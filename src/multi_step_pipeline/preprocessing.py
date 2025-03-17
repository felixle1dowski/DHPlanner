from PyQt5.QtCore import QVariant

from ..util.dhp_utility import DhpUtility
from ..util.config import Config
from qgis.core import (QgsProject, QgsSpatialIndex, QgsFeatureRequest, QgsVectorLayer,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsField, QgsFeature, QgsProcessingFeatureSourceDefinition, QgsWkbTypes)
from qgis import processing
from ..util.logger import Logger
from .preprocessing_result import PreprocessingResult


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
    heating_demand_layer = None

    # ToDo: Put this in config.
    HEAT_DEMAND_COL_NAME = "waermebeda"
    HEAT_DEMAND_N_BUILDINGS_COL_NAME = "anzahl_ein"
    INDIVIDUAL_HEAT_DEMAND_COL_NAME = "individual_heat_demand"
    JANUARY_CONSUMPTION_COL_NAME = "jan_demand"
    PEAK_DEMAND_COL_NAME = "peak_demand"
    BUILDINGS_ID_FIELD_NAME = "osm_id"
    COUNT_HOURS_IN_PEAK_MONTH = 31 * 24 # for January
    PEAK_MONTH_HEATING_DEMAND_PCT = 0.16 # for January - Jebamalai et al. (2019)
    MONTHS_IN_YEAR = 12

    RESTRICT_ROAD_TYPES = False

    def __init__(self):
        pass

    """Central method for preprocessing. Will start - and finish - the preprocessing pipeline."""
    def start(self) -> PreprocessingResult:
        self.selection_layer = None
        # ToDo: Add back in, when we use files again instead of layers.
        # self.roads_layer_path = Config().get_roads_path()
        # self.buildings_layer_path = Config().get_buildings_path()
        self.verify_layer(Config().get_selection_layer_name(), True)
        self.selection_layer = QgsProject.instance().mapLayersByName(Config().get_selection_layer_name())[0]
        self.verify_layer(Config().get_roads_layer_name())
        self.roads_layer = QgsProject.instance().mapLayersByName(Config().get_roads_layer_name())[0]
        self.verify_layer(Config().get_buildings_layer_name())
        self.buildings_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        self.verify_layer(Config().get_heat_demands_layer_name())
        self.heating_demand_layer = QgsProject.instance().mapLayersByName(Config().get_heat_demands_layer_name())[0]

        # ToDo: Is selection_layer necessary in the parameters?
        self.select_features(self.roads_layer, self.selection_layer)
        self.select_features(self.buildings_layer, self.selection_layer)
        self.select_features(self.heating_demand_layer, self.selection_layer)

        # ToDo: This is not good practice. I should not do this in place.
        # ToDo: I want to change this, so that I only work with temporary layers from the preprocessing stage onward.
        self.verify_layer(Config().get_roads_layer_name(), True)
        self.explode_road_lines()
        self.measure_lengths_of_roads()
        DhpUtility.assign_unique_ids_custom_name(self.selected_roads_exploded, "osm_id")
        Logger().info("Roads have been preprocessed successfully.")
        self.find_centroids_of_buildings()
        DhpUtility.assign_unique_ids(self.buildings_centroids, "id")
        self.add_building_type_attribute()
        Logger().info("Buildings have been preprocessed successfully.")
        self.add_heat_demands_to_building_centroids()
        Logger().info("Building centroids have successfully been adjusted to display heat demands of buildings.")
        self.delete_centroids_without_heat_demand()
        self.add_peak_demands_to_building_centroids()
        Logger().info("Peak demands have been calculated successfully and added to the buildings centroids.")
        result = PreprocessingResult(self.buildings_centroids, self.selected_roads_exploded)
        return result


    # ToDo: needs to be tested.
    def verify_layer(self, layer_name, verify_crs=False):
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
            self.convert_to_crs(layer, self.DESIRED_CRS)
        Logger().info(f"Layer {layer_name} has been verified successfully.")

    def convert_to_crs(self, layer, crs):
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

    def select_features(self, target_layer, selection_layer):
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
    def explode_road_lines(self):
        """Explodes the road lines. Purposes:
        1) Make MultiLine Layer to Line Layer.
        2) Optionally filter out undesired road types.
        3) Reduce complexity of vectors."""
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

        # If we want to restrict the road types that are to be used in order
        # to later lay the pipe network, we filter non-desired ones out now.
        if self.RESTRICT_ROAD_TYPES:
            restricted_types = Config().get_excluded_road_fclasses()
            for feature in selected_features:
                if feature['fclass'] not in restricted_types:
                    selected_roads_data_provider.addFeature(feature)
        else:
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
    def measure_lengths_of_roads(self):
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

    def assign_ids_to(self, layer):
        """Assigns unique IDs."""
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField("id", QVariant.Int)])
        layer.updateFields()
        for feature in layer.getFeatures():
            feature.setAttribute("id", feature.id())
            layer.updateFeature(feature)

    def find_centroids_of_buildings(self):
        params = {
            'INPUT': QgsProcessingFeatureSourceDefinition(
                self.buildings_layer.source(),
                selectedFeaturesOnly=True
            ),
            'OUTPUT': 'memory:'
        }
        result = processing.run("native:pointonsurface", params)
        self.buildings_centroids = result['OUTPUT']
        building_centroids_data_provider = self.buildings_centroids.dataProvider()
        building_centroids_data_provider.addAttributes([QgsField("Type", QVariant.String)])
        self.buildings_centroids.updateFields()
        QgsProject.instance().addMapLayer(self.buildings_centroids)

    def add_building_type_attribute(self):
        layer = self.buildings_centroids
        layer.startEditing()
        for feature in layer.getFeatures():
            feature.setAttribute("Type", "building")
            layer.updateFeature(feature)

    def add_heat_demands_to_building_centroids(self):
        building_centroids = self.buildings_centroids
        building_centroids.startEditing()
        DhpUtility.create_new_field(building_centroids, self.INDIVIDUAL_HEAT_DEMAND_COL_NAME, QVariant.String)
        insulation_factor = float(1 - (Config().get_insulation_factor() / 100))
        heat_demands = self.heating_demand_layer
        selected_heat_demands_list = list(self.heating_demand_layer.selectedFeatures())
        if not selected_heat_demands_list:
            raise Exception(f"No features selected in {self.heating_demand_layer.name()}.")
        centroids_area_dict = self.infer_building_areas_in_heat_demand_layer(selected_heat_demands_list,
                                                                                building_centroids)
        heat_spatial_index = QgsSpatialIndex(heat_demands.getFeatures())
        for centroid_feature, area_share in centroids_area_dict.items():
            point_geom = centroid_feature.geometry()
            heat_demand_ids = heat_spatial_index.intersects(point_geom.boundingBox())
            heat_demand_feature_iterator = heat_demands.getFeatures(heat_demand_ids)
            multiple_check = False
            for heat_demand_feature in heat_demand_feature_iterator:
                if heat_demand_feature.geometry().intersects(point_geom) and not multiple_check:
                    multiple_check = True
                    heat_demand_combined = heat_demand_feature[f"{self.HEAT_DEMAND_COL_NAME}"]
                    heat_demand_individual = str((float(heat_demand_combined) * area_share * insulation_factor))
                    Logger().debug(f"centroid {DhpUtility.get_value_from_field(building_centroids, centroid_feature, self.BUILDINGS_ID_FIELD_NAME)} "
                                   f"has an area share of {area_share}. The summed heating demand is {DhpUtility.get_value_from_field(heat_demands, heat_demand_feature, self.HEAT_DEMAND_COL_NAME)} "
                                   f"and thus an individual heat demand of {heat_demand_individual}")
                    DhpUtility.assign_value_to_field(building_centroids, self.INDIVIDUAL_HEAT_DEMAND_COL_NAME,
                                                     centroid_feature, heat_demand_individual)
                    building_centroids.updateFeature(centroid_feature)
                elif heat_demand_feature.geometry().contains(point_geom) and multiple_check:
                    building_centroid_id = centroid_feature.id()
                    raise Exception(
                        f"Multiple heat demand geometries for building centroid with id {building_centroid_id} found.")
        building_centroids.commitChanges()

    def infer_building_areas_in_heat_demand_layer(self, selected_heat_demands_list, building_centroids):
        buildings_spatial_index = QgsSpatialIndex(self.buildings_layer.getFeatures())
        result_dict = {}
        for heat_demand in selected_heat_demands_list:
            sum_of_area = 0
            id_area_dict = {}
            heat_demand_geometry = heat_demand.geometry()
            if heat_demand_geometry.isGeosValid() and heat_demand_geometry.type() == QgsWkbTypes.PolygonGeometry:
                intersecting_buildings = buildings_spatial_index.intersects(heat_demand_geometry.boundingBox())
                for building in DhpUtility.convert_iterator_to_list(
                        self.buildings_layer.getFeatures(intersecting_buildings)):
                    if building.geometry().intersects(heat_demand_geometry):
                        area = building.geometry().area()
                        sum_of_area += area
                        id_area_dict[DhpUtility.get_value_from_field(self.buildings_layer, building,
                                                                     self.BUILDINGS_ID_FIELD_NAME)] = area
                        Logger().debug(f"heat demand id: {heat_demand.id()} "
                                       f"Building area for building "
                                       f"{DhpUtility.get_value_from_field(self.buildings_layer, building, self.BUILDINGS_ID_FIELD_NAME)}: {area}")
            else:
                raise Exception(f"A selected heat demand is of the wrong type. Needed: "
                                f"Polygons. Gotten: {heat_demand_geometry.type()}, id of feature: {heat_demand.id()}")
            for building_id, area in id_area_dict.items():
                part_of_area_sum = area / sum_of_area
                corresponding_centroid = DhpUtility.get_feature_by_id_field(building_centroids,
                                                                            self.BUILDINGS_ID_FIELD_NAME,
                                                                            building_id)
                if corresponding_centroid is not None:
                    result_dict[corresponding_centroid] = part_of_area_sum
        logging_dict = {}
        for centroid, area in result_dict.items():
            logging_dict[DhpUtility.get_value_from_field(self.buildings_centroids, centroid, self.BUILDINGS_ID_FIELD_NAME)] = area
        Logger().debug(logging_dict)
        return result_dict

    def add_peak_demands_to_building_centroids(self):
        """
            From: Rosa, et al. (2012)
        """
        building_centroids = self.buildings_centroids
        DhpUtility.create_new_field(building_centroids, self.PEAK_DEMAND_COL_NAME, QVariant.String)
        DhpUtility.create_new_field(building_centroids, self.JANUARY_CONSUMPTION_COL_NAME, QVariant.String)
        building_centroids.startEditing()
        centroid_features = building_centroids.getFeatures()

        for centroid_feature in centroid_features:
            heat_demand = centroid_feature[f"{self.INDIVIDUAL_HEAT_DEMAND_COL_NAME}"]

            # unit: Kwh/month
            peak_month_demand = float(heat_demand) * self.PEAK_MONTH_HEATING_DEMAND_PCT
            DhpUtility.assign_value_to_field(building_centroids, self.JANUARY_CONSUMPTION_COL_NAME, centroid_feature, peak_month_demand)

            building_type = DhpUtility.get_value_from_field(building_centroids, centroid_feature, "type")

            # unit: Kwh/hour
            load_factor = Config().get_load_factor(building_type)

            peak_demand = self.q_peak_calculation(peak_month_demand, self.COUNT_HOURS_IN_PEAK_MONTH, load_factor)
            DhpUtility.assign_value_to_field(building_centroids, self.PEAK_DEMAND_COL_NAME, centroid_feature, peak_demand)



    @staticmethod
    def q_peak_calculation(epeakm, t, lf):
        result = epeakm / (t * lf)
        return result

    def delete_centroids_without_heat_demand(self):
        building_centroids = self.buildings_centroids
        centroid_provider = building_centroids.dataProvider()
        heat_demand_idx = building_centroids.fields().indexFromName(self.HEAT_DEMAND_COL_NAME)
        ids_to_delete = []
        str_ids_to_delete = []
        for feature in building_centroids.getFeatures():
            if feature.attributes()[heat_demand_idx] is None:
                ids_to_delete.append(feature.id())
                # ToDo: Delete all the osm_id accesses and replace it by a centrally located wallet or similar.
                str_ids_to_delete.append(DhpUtility.get_value_from_field(building_centroids, feature, "osm_id"))
        centroid_provider.deleteFeatures(ids_to_delete)
        building_centroids.commitChanges()
        Logger().debug(f"Deleted features with ids {', '.join(str_ids_to_delete)}, due to not having a corresponding"
                       f"heat demand.")

