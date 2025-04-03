from qgis.core import (QgsVectorLayer, QgsCoordinateReferenceSystem, QgsPointXY,
                       QgsFeature, QgsGeometry, QgsProject)
from PyQt5.QtCore import QVariant
import networkx as nx

from ..util.dhp_utility import DhpUtility


class GraphCreatorGreenfield():
    # TODO: NEEDS TO INHERIT FROM GRAPHCREATOR! A LOT OF REDUNDANT INFORMATION HERE!
    class GraphNode:
        def __init__(self, has_ap, building_id, coordinates):
            self.has_ap = has_ap
            self.building_id = building_id
            self.coordinates = coordinates

    class GraphEdge:
        def __init__(self, node_1, node_2, weight, id):
            self.node_1 = node_1
            self.node_2 = node_2
            self.weight = weight
            self.id = id

    DESIRED_CRS = QgsCoordinateReferenceSystem('EPSG:4839')
    ID_FIELD_NAME = "osm_id"
    BUILDING_CENTROID_ID_FIELD = "osm_id"
    LENGTH_FIELD_NAME = "length"
    CONNECTED_TO_BUILDING_FIELD_NAME = "connected_to_building"
    CONNECTED_FROM_BUILDING_FIELD_NAME = "connected_from_building"
    BUILDING_ID_FIELD_NAME = "osm_id"

    def __init__(self, building_centroids):
        self.building_centroids = building_centroids

    def start(self):
        layer = self.create_new_layer()
        self.create_weighted_lines_between_buildings(layer)
        nodes, edges, building_point_translation = self.collect_nodes_and_edges(layer)
        graph = self.construct_nx_graph(nodes, edges)
        # for debugging:
        QgsProject.instance().addMapLayer(layer)
        return graph, building_point_translation, layer

    def create_new_layer(self):
        line_layer = QgsVectorLayer(f'MultiLineString?crs={self.DESIRED_CRS}',
                                    'building_connections',
                                    'memory')
        DhpUtility.create_new_field(line_layer, self.ID_FIELD_NAME, QVariant.String)
        DhpUtility.create_new_field(line_layer, self.LENGTH_FIELD_NAME, QVariant.Double)
        DhpUtility.create_new_field(line_layer, self.CONNECTED_FROM_BUILDING_FIELD_NAME, QVariant.String)
        DhpUtility.create_new_field(line_layer, self.CONNECTED_TO_BUILDING_FIELD_NAME, QVariant.String)
        return line_layer

    def create_weighted_lines_between_buildings(self, layer):
        centroid_features = self.building_centroids.getFeatures()
        feature_list = DhpUtility.convert_iterator_to_list(centroid_features)
        for i in range(len(feature_list)):
            for j in range(i + 1, len(feature_list)):
                feature = self.create_line_between_buildings(feature_list[i], feature_list[j], layer)
                id_ = DhpUtility.assign_unique_id_custom_id_field(layer,
                                                                  feature,
                                                                  self.ID_FIELD_NAME)
                layer.dataProvider().addFeatures([feature])

    def collect_nodes_and_edges(self, line_layer):
        lines = line_layer.getFeatures()
        beginning_node_idx = line_layer.fields().indexFromName(self.CONNECTED_FROM_BUILDING_FIELD_NAME)
        ending_node_idx = line_layer.fields().indexFromName(self.CONNECTED_TO_BUILDING_FIELD_NAME)
        edges = []
        nodes = {}
        nodes_list = []
        building_point_translation = {}
        for line in lines:
            beginning_node_xy = self.check_node(line, beginning_node_idx, nodes_list, building_point_translation, nodes,
                                                DhpUtility.get_value_from_field(line_layer,
                                                                                line,
                                                                                self.CONNECTED_FROM_BUILDING_FIELD_NAME))
            ending_node_xy = self.check_node(line, ending_node_idx, nodes_list, building_point_translation, nodes,
                                             DhpUtility.get_value_from_field(line_layer,
                                                                             line,
                                                                             self.CONNECTED_TO_BUILDING_FIELD_NAME))
            edge = GraphCreatorGreenfield.GraphEdge(beginning_node_xy, ending_node_xy,
                                                    DhpUtility.get_value_from_field(line_layer,
                                                                                    line,
                                                                                    self.LENGTH_FIELD_NAME),
                                                    DhpUtility.get_value_from_field(line_layer,
                                                                                    line,
                                                                                    self.ID_FIELD_NAME))
            edges.append(edge)
        return nodes, edges, building_point_translation

    def check_node(self, line, node_field_idx, nodes_list, building_point_translation_dict, node_dict, building_id):
        node_id = line[node_field_idx]
        node_feature = DhpUtility.get_feature_by_id_field(self.building_centroids,
                                                          self.BUILDING_CENTROID_ID_FIELD,
                                                          node_id)
        node_xy = node_feature.geometry().asPoint()
        if self.check_if_node_already_added(node_xy, nodes_list) is None:
            nodes_list.append(node_xy)
            building_point_translation_dict[node_id] = node_xy
            node_dict[node_xy] = GraphCreatorGreenfield.GraphNode(True,
                                                                  DhpUtility.get_value_from_field(
                                                                      self.building_centroids,
                                                                      node_feature,
                                                                      self.BUILDING_ID_FIELD_NAME),
                                                                      node_xy)
        return node_xy

    def check_if_node_already_added(self, node, node_list: list):
        for existing_node in node_list:
            if node.x() == existing_node.x() and node.y() == existing_node.y():
                return existing_node
        return None

    def construct_nx_graph(self, nodes, edges):
        graph = nx.Graph()
        for node_point, node_information in nodes.items():
            node_info = {
                'has_ap': node_information.has_ap,
                'building_id': node_information.building_id,
                'coordinates': node_information.coordinates
            }
            graph.add_node(node_point, **node_info)
        for edge in edges:
            graph.add_edge(edge.node_1, edge.node_2, weight=edge.weight, edge_ids=edge.id)
        return graph



    def create_line_between_buildings(self, building_centroid_1, building_centroid_2, layer: QgsVectorLayer):
        b1_xy = QgsPointXY(building_centroid_1.geometry().asPoint().x(), building_centroid_1.geometry().asPoint().y())
        b2_xy = QgsPointXY(building_centroid_2.geometry().asPoint().x(), building_centroid_2.geometry().asPoint().y())
        layer_fields = layer.fields()
        line_feature = QgsFeature(layer_fields)
        line_geometry = QgsGeometry.fromPolylineXY([b1_xy, b2_xy])
        line_feature.setGeometry(line_geometry)
        DhpUtility.assign_value_to_field(layer, self.LENGTH_FIELD_NAME, line_feature, line_geometry.length())
        DhpUtility.assign_value_to_field(layer,
                                         self.CONNECTED_TO_BUILDING_FIELD_NAME,
                                         line_feature,
                                         DhpUtility.get_value_from_field(layer,
                                                                         building_centroid_2,
                                                                         self.BUILDING_ID_FIELD_NAME))
        DhpUtility.assign_value_to_field(layer,
                                         self.CONNECTED_FROM_BUILDING_FIELD_NAME,
                                         line_feature,
                                         DhpUtility.get_value_from_field(layer,
                                                                         building_centroid_1,
                                                                         self.BUILDING_ID_FIELD_NAME))
        return line_feature
