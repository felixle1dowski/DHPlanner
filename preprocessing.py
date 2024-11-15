from PyQt5.QtCore import QVariant
from .config import Config
from qgis.core import (QgsProject, QgsSpatialIndex, QgsFeatureRequest, QgsVectorLayer,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsMessageLog, Qgis, QgsField, QgsFeature)
from qgis import processing
from .logger import Logger


class Preprocessing:
    DESIRED_CRS = QgsCoordinateReferenceSystem('EPSG:4839')

    selection_layer = None
    roads_layer_path = None
    roads_layer = None
    buildings_layer_path = None
    buildings_layer = None
    selected_roads_exploded = None
    buildings_centroids = None
    preprocessing_result = None

    def __init__(self):
        pass

    """Central method for preprocessing. Will start - and finish - the preprocessing pipeline."""

    def start(self):
        self.selection_layer = None
        # ToDo: Add back in, when we use files again instead of layers.
        # self.roads_layer_path = Config().get_roads_path()
        # self.buildings_layer_path = Config().get_buildings_path()
        self.__verify_layer(Config().get_selection_layer_name(), True)
        self.selection_layer = QgsProject.instance().mapLayersByName(Config().get_selection_layer_name())[0]
        self.__verify_layer(Config().get_roads_layer_name())
        self.roads_layer = QgsProject.instance().mapLayersByName(Config().get_roads_layer_name())[0]
        self.__verify_layer(Config().get_buildings_layer_name())
        self.buildings_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]

        # ToDo: Is selection_layer necessary in the parameters?
        self.__select_features(self.roads_layer, self.selection_layer)
        self.__select_features(self.buildings_layer, self.selection_layer)

        # ToDo: This is not good practice. I should not do this in place.
        # ToDo: I want to change this, so that I only work with temporary layers from the preprocessing stage onward.
        self.__verify_layer(Config().get_roads_layer_name(), True)
        self.__explode_road_lines()
        self.__measure_lengths_of_roads()
        self.__assign_ids_to(self.selected_roads_exploded)
        Logger().info("Roads have been preprocessed successfully.")
        self.__find_centroids_of_buildings()
        self.__assign_ids_to(self.buildings_centroids)
        Logger().info("Buildings have been preprocessed successfully.")

    # ToDo: needs to be tested.
    def __verify_layer(self, layer_name, verify_crs=False):
        """
        Verifies the layer for further processing.

        :param layer_name: name of the layer inside the project.
        :param verify_crs: whether or not to verify the crs.
                don't verify it right away, when you
                want to reduce the size of the layer
                in a later preprocessing step. eg. explode the roads.
        """
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        if layer is None:
            raise Exception(f"No layer with name {layer_name} found.")
        if verify_crs and layer.crs() != self.DESIRED_CRS:
            Logger().warning(f"Layer {layer_name} has the wrong CRS."
                             "It is: {layer.crs()} The right"
                             "CRS is necessary in order to calculate pipe"
                             "lengths in meters."
                             f"Changing CRS to {self.DESIRED_CRS}")
            self.__convert_to_crs(layer, self.DESIRED_CRS)
        Logger().info(f"Layer {layer_name} has been verified successfully.")

    def __convert_to_crs(self, layer, crs):
        source_crs = layer.crs()
        transform = QgsCoordinateTransform(source_crs, crs, QgsProject.instance())
        layer.startEditing()
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                geom.transform(transform)
            layer.changeGeometry(feature.id(), geom)
        layer.setCrs(crs)
        layer.commitChanges()
        Logger().info("Selection CRS has been changed successfully.")

    def __select_features(self, target_layer, selection_layer):
        """Selects the features of the target_layer within the selection_layer. Uses Intersection."""
        if not target_layer.isEditable():
            target_layer.startEditing()
        # remove previous selection
        target_layer.removeSelection()
        # this is supposed to speed up the next processes.
        index = QgsSpatialIndex(target_layer.getFeatures())
        if selection_layer.featureCount() != 1:
            raise ValueError(f"The selection layer has to have exactly one feature."
                             f" It currently has {selection_layer.featureCount()} features.")
        polygon_feature = next(selection_layer.getFeatures())
        polygon_geom = polygon_feature.geometry()
        request = QgsFeatureRequest().setFilterRect(polygon_geom.boundingBox())
        intersecting_ids = [f.id() for f in target_layer.getFeatures(request) if polygon_geom.intersects(f.geometry())]
        if intersecting_ids:
            target_layer.selectByIds(intersecting_ids)
        target_layer.commitChanges()
        Logger().info(f"features of layer {target_layer.name()} have been selected successfully.")
        # iface.mapCanvas().refresh()

    # ToDo: can we generalize this? Not only for roads, but for lines in general?
    def __explode_road_lines(self):
        """Explodes the road lines. Two purposes:
        1) Make MultiLine Layer to Line Layer.
        2) Reduce complexity of vectors."""
        if not self.roads_layer.isValid():
            raise Exception(f"Target layer {self.roads_layer.name()} is invalid.")
        selected_features = self.roads_layer.selectedFeatures()
        if not selected_features:
            raise Exception(f"No features selected in {self.roads_layer.name()}.")
        # We're creating a copy of the roads layer with only the selected roads
        # By doing so, we can then explode it to obtain only Lines.
        selected_roads = QgsVectorLayer(f'MultiLineString?crs={self.DESIRED_CRS}',
                                        'selected_roads',
                                        'memory')
        selected_roads_data_provider = selected_roads.dataProvider()
        # We're copying the fields from the target layer to the selected layer.
        selected_roads_data_provider.addAttributes(self.roads_layer.fields())
        selected_roads.updateFields()
        selected_roads_data_provider.addFeatures(selected_features)
        params = {
            'INPUT': selected_roads,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        result = processing.run("native:explodelines", params)
        self.selected_roads_exploded = result['OUTPUT']
        QgsProject.instance().addMapLayer(self.selected_roads_exploded)
        Logger().info("Selected MultiLineStrings exploded successfully.")

    # ToDo: Generalize this for lengths in general.
    def __measure_lengths_of_roads(self):
        """Creates dedicated length field for each feature."""
        self.selected_roads_exploded.startEditing()
        self.selected_roads_exploded.dataProvider().addAttributes([QgsField("length", QVariant.Double)])
        self.selected_roads_exploded.updateFields()
        for feature in self.selected_roads_exploded.getFeatures():
            geom = feature.geometry()
            length = geom.length()
            feature.setAttribute("length", length)
            self.selected_roads_exploded.updateFeature(feature)
        self.selected_roads_exploded.commitChanges()
        Logger().info("Length of selected roads measured successfully.")

    def __assign_ids_to(self, layer):
        """Assigns unique IDs."""
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("id", QVariant.Int)])
        layer.updateFields()
        for feature in layer.getFeatures():
            feature.setAttribute("id", feature.id())
            layer.updateFeature(feature)

    def __find_centroids_of_buildings(self):
        # Create new temporary layer. ToDo: Do this earlier!
        selected_features = self.buildings_layer.selectedFeatures()
        self.buildings_centroids = QgsVectorLayer(f'Point?crs={self.DESIRED_CRS}',
                                            'selected_building_centroids',
                                            'memory')
        building_centroids_data_provider = self.buildings_centroids.dataProvider()

        new_features = []
        for feature in selected_features:
            geom = feature.geometry()
            centroid_geom = geom.centroid()
            centroid_feature = QgsFeature()
            centroid_feature.setGeometry(centroid_geom)
            centroid_feature.setAttributes([feature.id()])
            new_features.append(centroid_feature)

        building_centroids_data_provider.addFeatures(new_features)
        self.buildings_centroids.updateExtents()
        QgsProject.instance().addMapLayer(self.buildings_centroids)
