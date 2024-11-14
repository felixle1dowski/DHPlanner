from PyQt5.QtCore import QVariant
from qgis._core import QgsField

from .config import Config
from qgis.core import (QgsProject, QgsSpatialIndex, QgsFeatureRequest, QgsVectorLayer,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsMessageLog, Qgis)
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

    def __init__(self):
        pass

    def start(self):
        self.selection_layer = None
        # ToDo: Add back in, when we use files again instead of layers.
        # self.roads_layer_path = Config().get_roads_path()
        # self.buildings_layer_path = Config().get_buildings_path()
        self.__verify_layer(Config().get_selection_layer_name())
        self.selection_layer = QgsProject.instance().mapLayersByName(Config().get_selection_layer_name())[0]
        self.__verify_layer(Config().get_roads_layer_name())
        self.roads_layer = QgsProject.instance().mapLayersByName(Config().get_roads_layer_name())[0]
        self.__verify_layer(Config().get_buildings_layer_name())
        self.buildings_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]

        # ToDo: Is selection_layer necessary in the parameters?
        self.__select_features(self.roads_layer, self.selection_layer)
        self.__select_features(self.buildings_layer, self.selection_layer)

        self.__explode_road_lines()
        self.__measure_length()

    # needs to be tested.
    def __verify_layer(self, layer_name):
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        if layer is None:
            raise Exception(f"No layer with name {layer_name} found.")
        if layer.crs() != self.DESIRED_CRS:
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
        if not self.roads_layer.isValid():
            raise Exception(f"Target layer {self.roads_layer.name()} is invalid.")
        selected_features = self.roads_layer.selectedFeatures()
        if not selected_features:
            raise Exception(f"No features selected in {self.roads_layer.name()}.")
        # We're creating a copy of the roads layer with only the selected roads
        # By doing so, we can then explode it to obtain only Lines.
        selected_roads = QgsVectorLayer(f'MultiLineString?crs={self.DESIRED_CRS}', 'selected_roads', 'memory')
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

    def __measure_length(self):
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