from qgis.core import (QgsColorBrewerColorRamp, QgsRuleBasedRenderer,
                       QgsVectorLayer, QgsProject, QgsFeature,
                       QgsCategorizedSymbolRenderer, QgsSymbol, QgsRendererCategory)
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
    CLUSTER_CENTER_FIELD = "cluster_center"

    def visualize_network(self, cluster_dict):
        pass

    def create_member_layer(self, cluster_dict):
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
        for entry in cluster_dict['clusters']:
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
        all_cluster_centers = [inner_dict['cluster_center'] for inner_dict in cluster_dict['clusters']]
        for cluster_center in all_cluster_centers:
            cluster_members_of_cluster_center = DhpUtility.flatten_list(
                [inner_dict['members'] for inner_dict in cluster_dict['clusters'] if
                 inner_dict['cluster_center'] == cluster_center]
            )
            for member in cluster_members_of_cluster_center:
                feature = DhpUtility.get_feature_by_id_field(member_layer, self.BUILDING_ID_FIELD, member)
                DhpUtility.assign_value_to_field(member_layer, self.CLUSTER_CENTER_FIELD, feature, cluster_center)

        # Apply styling
        # colors = Visualization.generate_colors(all_cluster_centers)
        renderer = self.create_unique_cluster_colors_renderer(all_cluster_centers, member_layer.geometryType(), self.CLUSTER_CENTER_FIELD)
        member_layer.setRenderer(renderer)
        member_layer.triggerRepaint()
        # Commit changes and refresh the layer
        member_layer.commitChanges()
        member_layer.updateExtents()  # Update the layer's extent
        if iface:
            iface.layerTreeView().refreshLayerSymbology(member_layer.id())

    def create_unique_cluster_colors_renderer(self, labels, geometry_type, cluster_field):
        unique_labels = set(labels)
        categories = []
        for cluster_id in unique_labels:
            cluster_id = str(cluster_id)
            symbol = QgsSymbol.defaultSymbol(geometry_type)
            colors = QColor.fromRgb(random.randrange(0, 256), random.randrange(0, 256), random.randrange(0, 256))
            symbol.setColor(colors)
            category = QgsRendererCategory(cluster_id, symbol, cluster_id)
            categories.append(category)
        renderer = QgsCategorizedSymbolRenderer(cluster_field, categories)
        return renderer


    @staticmethod
    def generate_colors(categories, ramp_name='Spectral'):
        num_colors = len(categories)
        ramp = QgsColorBrewerColorRamp(ramp_name, num_colors)
        ramp.updateColors()
        center_colors = {}
        for i, center in enumerate(categories):
            color = ramp.color(i % num_colors).name()
            center_colors[center] = color
        return center_colors
