from qgis.core import (QgsColorBrewerColorRamp, QgsRuleBasedRenderer,
                       QgsVectorLayer, QgsProject, QgsFeature,
                       QgsCategorizedSymbolRenderer, QgsSymbol, QgsRendererCategory, QgsFillSymbol,
                       QgsLineSymbol, QgsStyle)
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
    ROAD_ID_FIELD = "osm_id"
    CLUSTER_CENTER_FIELD = "cluster_center"

    ready_to_start = False
    exploded_roads_layer = None
    cluster_dict = None


    def start(self):
        if self.ready_to_start:
            cluster_center_colors_dict = self.generate_color_per_cluster_center()
            building_categories = self.create_categories(cluster_center_colors_dict, QgsFillSymbol)
            pipe_categories = self.create_categories(cluster_center_colors_dict, QgsLineSymbol)
            self.create_member_layer(building_categories)
            self.create_network_layer(pipe_categories)

    def set_required_fields(self, exploded_roads, cluster_dict):
        self.exploded_roads_layer = exploded_roads
        self.cluster_dict = cluster_dict
        self.ready_to_start = True

    def create_member_layer(self, cluster_center_fill_categories):
        building_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        building_fields = building_layer.fields()
        building_crs = building_layer.crs().authid()

        # Create the member layer
        member_layer = QgsVectorLayer(f'Polygon?crs={building_crs}', 'cluster_members', 'memory')
        member_layer_provider = member_layer.dataProvider()
        member_layer_provider.addAttributes(building_fields)
        member_layer.updateFields()
        member_layer.startEditing()

        # Get all members from the cluster dictionary
        complete_member_list = []
        for entry in self.cluster_dict['clusters']:
            members = entry['members']
            complete_member_list += members

        # Get features from the building layer
        building_features = DhpUtility.get_features_by_id_field(building_layer, self.BUILDING_ID_FIELD,
                                                                complete_member_list)
        for feature in building_features:
            building_geometry = feature.geometry()
            if not building_geometry.isGeosValid():
                print(f"Invalid geometry for feature ID: {feature.id()}")
                continue  # Skip invalid geometries

            building_attributes = feature.attributes()
            member_feature = QgsFeature()
            member_feature.setGeometry(building_geometry)
            member_feature.setFields(building_fields)
            member_feature.setAttributes(building_attributes)
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
        all_cluster_centers = [inner_dict['cluster_center'] for inner_dict in self.cluster_dict['clusters']]
        for cluster_center in all_cluster_centers:
            cluster_members_of_cluster_center = DhpUtility.flatten_list(
                [inner_dict['members'] for inner_dict in self.cluster_dict['clusters'] if
                 inner_dict['cluster_center'] == cluster_center]
            )
            for member in cluster_members_of_cluster_center:
                feature = DhpUtility.get_feature_by_id_field(member_layer, self.BUILDING_ID_FIELD, member)
                DhpUtility.assign_value_to_field(member_layer, self.CLUSTER_CENTER_FIELD, feature, cluster_center)

        # Apply styling
        self.render_and_repaint(member_layer, self.CLUSTER_CENTER_FIELD, cluster_center_fill_categories)
        # Commit changes and refresh the layer
        member_layer.commitChanges()
        member_layer.updateExtents()  # Update the layer's extent
        if iface:
            iface.layerTreeView().refreshLayerSymbology(member_layer.id())

    # def create_unique_cluster_colors_renderer(self, labels, geometry_type, cluster_field):
    #     unique_labels = set(labels)
    #     categories = []
    #     for cluster_id in unique_labels:
    #         cluster_id = str(cluster_id)
    #         symbol = QgsSymbol.defaultSymbol(geometry_type)
    #         colors = QColor.fromRgb(random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
    #         symbol.setColor(colors)
    #         category = QgsRendererCategory(cluster_id, symbol, cluster_id)
    #         categories.append(category)
    #     renderer = QgsCategorizedSymbolRenderer(cluster_field, categories)
    #     return renderer

    def create_network_layer(self, cluster_center_line_categories):
        roads_per_cluster_center = {cluster['cluster_center']: cluster['pipe_result'] for cluster in self.cluster_dict['clusters'] if cluster['cluster_center'] != "-1"}
        roads_crs = self.exploded_roads_layer.crs().authid()
        roads_fields = self.exploded_roads_layer.fields()
        network_layer = QgsVectorLayer(f'MultiLineString?crs={roads_crs}', 'pipe_network', 'memory')
        network_layer_provider = network_layer.dataProvider()
        network_layer_provider.addAttributes(roads_fields)
        network_layer.updateFields()
        network_layer.startEditing()

        pipes_to_be_added = {}
        for cluster_center, pipe_results in roads_per_cluster_center.items():
            if pipe_results:
                for pipe_result in pipe_results:
                    road_ids = pipe_result['id']
                    for road_id in road_ids:
                        road_feature = DhpUtility.get_feature_by_id_field(self.exploded_roads_layer,
                                                                          self.ROAD_ID_FIELD,
                                                                          road_id)
                        new_pipe_feature = QgsFeature()
                        new_pipe_feature.setGeometry(road_feature.geometry())
                        new_pipe_feature.setAttributes(road_feature.attributes())
                        pipes_to_be_added[road_id] = new_pipe_feature
        Logger().debug(pipes_to_be_added)
        all_pipe_features_to_be_added = [road_feature for road_id, road_feature in pipes_to_be_added.items()]
        network_layer_provider.addFeatures(all_pipe_features_to_be_added)

        DhpUtility.create_new_field(network_layer, self.CLUSTER_CENTER_FIELD, QVariant.String)
        for cluster_center, pipe_results in roads_per_cluster_center.items():
            if pipe_results:
                for pipe_result in pipe_results:
                    road_ids = pipe_result['id']
                    for road_id in road_ids:
                        pipe_feature = DhpUtility.get_feature_by_id_field(network_layer, self.ROAD_ID_FIELD, road_id)
                        DhpUtility.assign_value_to_field(network_layer, self.CLUSTER_CENTER_FIELD,
                                                         pipe_feature, cluster_center)
        self.render_and_repaint(network_layer, self.CLUSTER_CENTER_FIELD, cluster_center_line_categories)

        network_layer.commitChanges()
        network_layer.updateExtents()
        QgsProject.instance().addMapLayer(network_layer)

    def render_and_repaint(self, layer, field_to_categorize_by, categories):
        renderer = QgsCategorizedSymbolRenderer(field_to_categorize_by, categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()

    def generate_color_per_cluster_center(self):
        cluster_centers = [inner_dict['cluster_center'] for inner_dict in self.cluster_dict['clusters']]
        cluster_center_colors_dict = Visualization.generate_colors(cluster_centers)
        return cluster_center_colors_dict

    def create_categories(self, center_with_corresponding_color, symbol_type):
        categories = []
        if isinstance(symbol_type, QgsFillSymbol):
            categories = self.create_categories_fill(center_with_corresponding_color)
        elif isinstance(symbol_type, QgsLineSymbol):
            categories = self.create_categories_line(center_with_corresponding_color)
        Logger().debug(f"generated categories: {categories}")
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
            Logger().debug(f"Color for center {center}: {color}")

        Logger().debug(f"Generated colors for cluster centers: {center_colors}")
        return center_colors
