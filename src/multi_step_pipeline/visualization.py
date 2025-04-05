from qgis.core import (QgsColorBrewerColorRamp, QgsRuleBasedRenderer,
                       QgsVectorLayer, QgsProject, QgsFeature,
                       QgsCategorizedSymbolRenderer, QgsSymbol, QgsRendererCategory, QgsFillSymbol,
                       QgsLineSymbol, QgsStyle, QgsMultiLineString, QgsGeometry)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from ..util.config import Config
from ..util.logger import Logger
from ..util.dhp_utility import DhpUtility
from qgis.utils import iface
import random

class Visualization:

    COLOR_RAMP_NAME = 'Spectral'
    BUILDING_ID_FIELD = "osm_id"
    INFO_LAYER_ID_FIELD = "osm_id"
    ROAD_ID_FIELD = "osm_id"
    CLUSTER_CENTER_FIELD = "cluster_center"
    PIPE_TYPE_FIELD = "pipe_type"
    PIPE_OUTER_DIAMETER_FIELD = "pipe_diameter"
    ROAD_IDS_KEY_NAME = "id"
    ROAD_IDS_FIELD_NAME = "road_ids"

    PIPE_ID_FIELD_NAME = "pipe_id"

    PIPE_RENDER_MIN_THICKNESS = 0.3
    PIPE_RENDER_MAX_THICKNESS = 2.0

    ready_to_start = False
    pipe_layer = None
    cluster_list = None
    info_layer = None


    def start(self):
        if self.ready_to_start:
            cluster_center_colors_dict = self.generate_color_per_cluster_center(self.cluster_list)
            building_categories = self.create_categories(cluster_center_colors_dict, QgsFillSymbol)
            pipe_categories = self.create_categories(cluster_center_colors_dict, QgsLineSymbol)
            self.create_selection_result_layer(self.cluster_list)
            self.create_results_per_cluster_layer(self.cluster_list, building_categories)
            self.create_member_layer(building_categories, self.cluster_list)
            self.create_network_layer(pipe_categories, self.cluster_list)

    def set_required_fields(self, pipe_layer, cluster_list, info_layer):
        self.pipe_layer = pipe_layer
        self.cluster_list = cluster_list
        self.info_layer = info_layer
        self.ready_to_start = True

    def create_selection_result_layer(self, cluster_list):
        selection_layer = QgsProject.instance().mapLayersByName(Config().get_selection_layer_name())[0]
        if not selection_layer.isValid():
            # we should never get here, since the layers have been validated while
            # preprocessing. This is here just in case some process tempered with
            # the layer during the processing chain.
            raise Exception('Invalid selection layer')
        selection_crs = selection_layer.crs().authid()
        selection_result_layer = QgsVectorLayer(f'Polygon?crs={selection_crs}', 'selection_result', 'memory')
        feature = DhpUtility.convert_iterator_to_list(selection_layer.getFeatures())
        if len(feature) > 1:
            raise Exception('Multiple features in selection layer are not supported')
        selection_feature = feature[0]
        selection_geometry = selection_feature.geometry()
        selection_feature.setGeometry(selection_geometry)
        self.add_fields_and_attributes_selection_result(selection_result_layer, selection_feature, cluster_list)
        selection_result_layer.startEditing()
        selection_result_layer.dataProvider().addFeatures([selection_feature])
        selection_result_layer.commitChanges()
        selection_result_layer.updateExtents()
        QgsProject.instance().addMapLayer(selection_result_layer)

    def add_fields_and_attributes_selection_result(self, selection_result_layer, selection_feature, cluster_list):
        # assumes all sum fields are of type double (float).
        all_fields = []
        for key, value in cluster_list['total_sums'].items():
            all_fields.append((key, value))
        for field in all_fields:
            DhpUtility.create_new_field(selection_result_layer, field[0], QVariant.Double)
        selection_feature.setFields(selection_result_layer.fields())
        for field in all_fields:
            DhpUtility.assign_value_to_field(selection_result_layer, field[0], selection_feature, field[1])

    def create_results_per_cluster_layer(self, cluster_list, cluster_center_fill_categories):
        building_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        if not building_layer.isValid():
            raise Exception('Invalid building layer')
        building_crs = building_layer.crs().authid()
        cluster_result_layer = QgsVectorLayer(f'Polygon?crs={building_crs}', f'cluster_result', 'memory')
        cluster_members_and_sums = {}
        for entry in cluster_list['clusters']:
            for inner_dict in entry['clusters']:
                if inner_dict["cluster_center"] != "-1":
                    cluster_members_and_sums[inner_dict['cluster_center']] = {
                        "members": inner_dict['members'],
                        "supplied_power": inner_dict['supplied_power'],
                        "pipe_investment_cost": inner_dict['pipe_investment_cost'],
                        "trench_cost": inner_dict['trench_cost'],
                        "total_pipe_cost": inner_dict['total_pipe_cost'],
                        "total_cost": inner_dict['total_cost'],
                        "fitness": inner_dict['fitness'],
                    }
        self.add_fields_results_per_cluster_layer(cluster_result_layer, cluster_members_and_sums)
        features_to_add = []
        for cluster_center, inner_dict in cluster_members_and_sums.items():
            cluster_feature = QgsFeature()
            self.create_fused_geometry(building_layer, inner_dict["members"], cluster_feature)
            self.set_values_for_results_per_cluster_layer(cluster_result_layer,
                                                          cluster_center, inner_dict, cluster_feature)
            features_to_add.append(cluster_feature)
        cluster_result_layer.startEditing()
        cluster_result_layer.dataProvider().addFeatures(features_to_add )
        cluster_result_layer.commitChanges()
        cluster_result_layer.updateExtents()
        QgsProject.instance().addMapLayer(cluster_result_layer)
        self.render_and_repaint(cluster_result_layer, self.CLUSTER_CENTER_FIELD, cluster_center_fill_categories)

    def add_fields_results_per_cluster_layer(self, cluster_result_layer, cluster_members_and_sums):
        # assumes all sum fields are double (float)
        DhpUtility.create_new_field(cluster_result_layer, self.CLUSTER_CENTER_FIELD, QVariant.String)
        fields_to_add = []
        for cluster_center, inner_dict in cluster_members_and_sums.items():
            for key in inner_dict.keys():
                if key != "members":
                    fields_to_add.append(key)
        for field in fields_to_add:
            DhpUtility.create_new_field(cluster_result_layer, field, QVariant.Double)

    def set_values_for_results_per_cluster_layer(self, cluster_result_layer, cluster_center_id, dictionary_with_fields, feature):
        feature.setFields(cluster_result_layer.fields())
        DhpUtility.assign_value_to_field(cluster_result_layer, self.CLUSTER_CENTER_FIELD, feature, cluster_center_id)
        for key, value in dictionary_with_fields.items():
            if key != "members":
                DhpUtility.assign_value_to_field(cluster_result_layer, key, feature, value)

    def create_fused_geometry(self, building_layer, member_ids, feature):
        member_building_features = DhpUtility.get_features_by_id_field(building_layer, self.BUILDING_ID_FIELD, member_ids)
        geometries = [feature.geometry() for feature in member_building_features]
        if geometries:
            fused_geometry = QgsGeometry(geometries[0])
            if len(geometries) > 1:
                for geometry in geometries[1:]:
                    fused_geometry = fused_geometry.combine(geometry)
            feature.setGeometry(fused_geometry)

    def create_member_layer(self, cluster_center_fill_categories, cluster_list):
        building_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        if not building_layer.isValid():
            raise Exception('Invalid building layer')
        info_layer_fields = self.info_layer.fields()
        building_crs = building_layer.crs().authid()

        # Create the member layer
        member_layer = QgsVectorLayer(f'Polygon?crs={building_crs}', f'cluster_members', 'memory')
        member_layer_provider = member_layer.dataProvider()
        member_layer_provider.addAttributes(info_layer_fields)
        member_layer.updateFields()
        member_layer.startEditing()

        # Get all members from the cluster dictionary
        complete_member_list = []
        for entry in cluster_list['clusters']:
            for inner_dict in entry['clusters']:
                members = inner_dict['members']
                complete_member_list += members

        # for entry in cluster_dict['clusters']:
        #     members = entry['members']
        #     complete_member_list += members

        # Get features from the building layer
        building_features = DhpUtility.get_features_by_id_field(building_layer, self.BUILDING_ID_FIELD,
                                                                complete_member_list)
        for feature in building_features:
            building_geometry = feature.geometry()
            if not building_geometry.isGeosValid():
                print(f"Invalid geometry for feature ID: {feature.id()}")
                continue  # Skip invalid geometries
            corresponding_info_layer_feature = DhpUtility.get_feature_by_id_field(self.info_layer,
                                                                                  self.INFO_LAYER_ID_FIELD,
                                                                                  DhpUtility.get_value_from_field(building_layer,
                                                                                                                  feature,
                                                                                                                  self.BUILDING_ID_FIELD))
            info_layer_attributes = corresponding_info_layer_feature.attributes()
            member_feature = QgsFeature()
            member_feature.setGeometry(building_geometry)
            member_feature.setFields(info_layer_fields)
            member_feature.setAttributes(info_layer_attributes)
            result = member_layer_provider.addFeature(member_feature)
            if not result:
                Logger().error("Failed to add features to the layer.")
                Logger().error(f"Reason: {member_layer_provider.error().message()}")
            else:
                Logger().debug(f"Successfully added feature to the layer.")

        # Add the layer to the project
        QgsProject.instance().addMapLayer(member_layer)

        # Add cluster center field and assign values
        DhpUtility.create_new_field(member_layer, self.CLUSTER_CENTER_FIELD, QVariant.String)
        all_cluster_centers = []
        for entry in cluster_list['clusters']:
            for inner_dict in entry['clusters']:
                all_cluster_centers.append(inner_dict['cluster_center'])
        # all_cluster_centers = [inner_dict['cluster_center'] for inner_dict in cluster_dict['clusters']]
        for cluster_center in all_cluster_centers:
            for entry in cluster_list['clusters']:
                cluster_members_of_cluster_center = DhpUtility.flatten_list(
                    [inner_dict['members'] for inner_dict in entry['clusters'] if
                     inner_dict['cluster_center'] == cluster_center]
                )
                for member in cluster_members_of_cluster_center:
                    feature = DhpUtility.get_feature_by_id_field(member_layer, self.INFO_LAYER_ID_FIELD, member)
                    DhpUtility.assign_value_to_field(member_layer, self.CLUSTER_CENTER_FIELD, feature, cluster_center)
        # Apply styling
        self.render_and_repaint(member_layer, self.CLUSTER_CENTER_FIELD, cluster_center_fill_categories)
        # Commit changes and refresh the layer
        member_layer.commitChanges()
        member_layer.updateExtents()  # Update the layer's extent
        if iface:
            iface.layerTreeView().refreshLayerSymbology(member_layer.id())

    def create_network_layer(self, cluster_center_line_categories, cluster_list):
        roads_per_cluster_center = {}
        for entry in cluster_list['clusters']:
            for cluster in entry['clusters']:
                if cluster['cluster_center'] != "-1":
                    roads_per_cluster_center[cluster['cluster_center']] = cluster['pipe_result']
        # roads_per_cluster_center = {cluster['cluster_center']: cluster['pipe_result'] for cluster in cluster_dict['clusters'] if cluster['cluster_center'] != "-1"}
        roads_crs = self.pipe_layer.crs().authid()
        network_layer = QgsVectorLayer(f'MultiLineString?crs={roads_crs}', 'pipe_network', 'memory')
        network_layer_provider = network_layer.dataProvider()
        network_layer.startEditing()
        pipes_to_be_added = self.create_pipe_features(roads_per_cluster_center, network_layer)
        network_layer_provider.addFeatures(pipes_to_be_added)
        DhpUtility.create_new_field(network_layer, self.PIPE_ID_FIELD_NAME, QVariant.String)
        DhpUtility.assign_unique_ids_custom_name(network_layer, self.PIPE_ID_FIELD_NAME)

        # sadly double rendering doesn't work :(
        # pipe_result = DhpUtility.flatten_list(roads_per_cluster_center.values())
        # diameter_thicknesses = self.calculate_diameter_thickness(pipe_result)
        # self.render_line_thickness(network_layer, diameter_thicknesses)

        self.render_and_repaint(network_layer, self.CLUSTER_CENTER_FIELD, cluster_center_line_categories)
        network_layer.commitChanges()
        network_layer.updateExtents()
        QgsProject.instance().addMapLayer(network_layer)

    def render_line_thickness(self, network_layer, diameter_thicknesses):
        default_symbol = QgsLineSymbol.createSimple({'width': '1.0'})
        rule_renderer = QgsRuleBasedRenderer(default_symbol)
        root_rule = rule_renderer.rootRule()
        for diameter, thickness in diameter_thicknesses.items():
            symbol = QgsLineSymbol.createSimple({'width': thickness})
            rule = QgsRuleBasedRenderer.Rule(symbol, filterExp=f'"pipe_diameter" = {diameter}')
            root_rule.appendChild(rule)
        network_layer.setRenderer(rule_renderer)
        network_layer.triggerRepaint()

    def render_and_repaint(self, layer, field_to_categorize_by, categories):
        renderer = QgsCategorizedSymbolRenderer(field_to_categorize_by, categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def generate_color_per_cluster_center(self, cluster_list):
        cluster_centers = []
        for inner_list in cluster_list['clusters']:
            for cluster in inner_list['clusters']:
                cluster_centers.append(cluster['cluster_center'])
        cluster_center_colors_dict = Visualization.generate_colors(cluster_centers)
        return cluster_center_colors_dict

    def create_categories(self, center_with_corresponding_color, symbol_type):
        categories = []
        if symbol_type is QgsFillSymbol:
            categories = self.create_categories_fill(center_with_corresponding_color)
        elif symbol_type is QgsLineSymbol:
            categories = self.create_categories_line(center_with_corresponding_color)
        # Logger().debug(f"generated categories: {categories}")
        return categories

    def create_categories_fill(self, center_with_corresponding_color):
        categories = []
        # creating symbols
        for cluster_center, color in center_with_corresponding_color.items():
            symbol = QgsFillSymbol.createSimple({
                'color': color,
                'outline_color': 'black'
            })
            # creating categories
            category = QgsRendererCategory(cluster_center, symbol, str(cluster_center))
            categories.append(category)
        return categories

    def create_categories_line(self, center_with_corresponding_color):
        categories = []
        # creating symbols
        for cluster_center, color in center_with_corresponding_color.items():
            symbol = QgsLineSymbol.createSimple({
                'color': color,
                'outline_color': color
            })
            # creating categories
            category = QgsRendererCategory(cluster_center, symbol, str(cluster_center))
            categories.append(category)
        return categories

    @staticmethod
    def generate_colors(categories, ramp_name='Turbo'):
        style = QgsStyle.defaultStyle()
        ramp = style.colorRamp(ramp_name)

        # Check if the ramp was found
        if not ramp:
            Logger().error(f"Failed to find color ramp with name: {ramp_name}")
            return {center: '#000000' for center in categories}  # Default to black

        num_colors = len(categories)
        center_colors = {}

        for i, center in enumerate(categories):
            # Normalize i to a value between 0 and 1
            normalized_value = i / (num_colors - 1) if num_colors > 1 else 0.5
            color = ramp.color(normalized_value).name()
            center_colors[center] = color
            # Logger().debug(f"Color for center {center}: {color}")

        # Logger().debug(f"Generated colors for cluster centers: {center_colors}")
        return center_colors

    def add_pipe_fields(self, pipe_result, pipe_attributes, network_layer):
        for pipe in pipe_result:
            for title, value in pipe.items():
                if title not in pipe_attributes:
                    # not pretty: extra rules for this iteration:
                    if title not in ["id", "pipe_type"]:
                        pipe_attributes.append(title)
                        q_variant = QVariant(value).type()
                        DhpUtility.add_field(network_layer, title, q_variant)
        DhpUtility.add_field(network_layer, self.CLUSTER_CENTER_FIELD, QVariant.String)
        DhpUtility.add_field(network_layer, self.ROAD_ID_FIELD, QVariant.String)
        DhpUtility.add_field(network_layer, self.PIPE_TYPE_FIELD, QVariant.String)
        DhpUtility.add_field(network_layer, self.PIPE_OUTER_DIAMETER_FIELD, QVariant.Double)

    def add_pipe_field_values(self, pipe, network_layer, pipe_feature, cluster_center):
        for entry, value in pipe.items():
            if entry not in ["id", "pipe_type"]:
                DhpUtility.assign_value_to_field(network_layer, entry, pipe_feature, value)
            # sadly: some extra rules.
            elif entry == "id":
                road_ids = str(value)
                DhpUtility.assign_value_to_field(network_layer, self.ROAD_ID_FIELD, pipe_feature, road_ids)
            elif entry == "pipe_type":
                pipe_type = str(value['type'])
                DhpUtility.assign_value_to_field(network_layer, self.PIPE_TYPE_FIELD, pipe_feature, pipe_type)
                outer_diameter = float(value['outer_diameter'])
                DhpUtility.assign_value_to_field(network_layer, self.PIPE_OUTER_DIAMETER_FIELD, pipe_feature, outer_diameter)
            DhpUtility.assign_value_to_field(network_layer, self.CLUSTER_CENTER_FIELD, pipe_feature, cluster_center)

    def add_pipe_geometry(self, pipe, pipe_feature):
        road_ids = pipe[self.ROAD_IDS_KEY_NAME]
        pipe_multiline = QgsMultiLineString()
        if type(road_ids) == list:
            for road_id in road_ids:
                road_feature = DhpUtility.get_feature_by_id_field(self.pipe_layer, self.ROAD_ID_FIELD, road_id)
                road_geometry = road_feature.geometry().constGet().clone()
                pipe_multiline.addGeometry(road_geometry)
        elif type(road_ids) == str:
            road_feature = DhpUtility.get_feature_by_id_field(self.pipe_layer, self.ROAD_ID_FIELD, road_ids)
            road_geometry = road_feature.geometry().constGet().clone()
            pipe_multiline.addGeometry(road_geometry)
        pipe_feature.setGeometry(QgsGeometry(pipe_multiline))


    def create_pipe_features(self, pipes_per_cluster_center, network_layer):
        pipe_attributes = []
        pipe_features = []
        pipe_result = DhpUtility.flatten_list(pipes_per_cluster_center.values())
        # diameter_thicknesses = self.calculate_diameter_thickness(pipe_result)
        self.add_pipe_fields(pipe_result, pipe_attributes, network_layer)
        for cluster_center, pipes in pipes_per_cluster_center.items():
            for pipe in pipes:
                pipe_feature = QgsFeature()
                pipe_feature.setFields(network_layer.fields())
                self.add_pipe_field_values(pipe, network_layer, pipe_feature, cluster_center)
                self.add_pipe_geometry(pipe, pipe_feature)
                pipe_features.append(pipe_feature)
        return pipe_features

    def calculate_diameter_thickness(self, pipe_result):
        pipe_diameter = set([inner_dict["pipe_type"]["outer_diameter"] for inner_dict in pipe_result if "pipe_type" in inner_dict])
        min_diameter = min(pipe_diameter)
        max_diameter = max(pipe_diameter)
        diameter_thickness_dict = {}
        for diameter in pipe_diameter:
            diameter_thickness_dict[diameter] = self.normalize(diameter, min_diameter,
                                                               max_diameter,
                                                               self.PIPE_RENDER_MIN_THICKNESS,
                                                               self.PIPE_RENDER_MAX_THICKNESS)
        return diameter_thickness_dict

    def normalize(self, value, old_min, old_max, new_min, new_max):
        normalized_value = ((value - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
        return normalized_value



