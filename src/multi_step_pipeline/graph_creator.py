import math
from operator import truediv

from ..util.logger import Logger
from ..util.dhp_utility import DhpUtility
from ..util.config import Config
from .graph_construction_exception import GraphConstructionException
from .node_information import NodeInformation
from .graph_creator_result import GraphCreatorResult
import networkx as nx
from PyQt5.QtCore import QVariant
import matplotlib.pyplot as plt
from qgis.core import (QgsProject, QgsExpression,
                       QgsFeatureRequest, QgsField,
                       QgsPointXY, QgsLineString,
                       QgsFeature, QgsGeometry,
                       QgsVectorLayer, QgsPoint)
from qgis import processing
from dataclasses import dataclass


class GraphCreator:
    class GraphNode:
        has_ap: bool
        building_id: str
        coordinates: QgsPointXY

        def __init__(self, has_ap, building_id, coordinates):
            self.has_ap = has_ap
            self.building_id = building_id
            self.coordinates = coordinates

    class GraphEdge:
        node_1 = None
        node_2 = None
        weight = None
        id = None

        def __init__(self, node_1, node_2, weight, id):
            self.node_1 = node_1
            self.node_2 = node_2
            self.weight = weight
            self.id = id

    DEBUG = True

    ready_to_start = False
    exploded_roads = None
    building_centroids = None
    roads_graph = None
    graph_representation = None
    DISTANCE_OF_POINTS = 5.0
    """Interval of Points that are to be regarded in the calculation of access points."""
    DRAW_GRAPH = True
    """Indiciates whether there's a plot of a graph to be generated for debugging purposes."""
    PERP_LINE_LENGTH = 20.0
    """Determines the length of the perpendicular lines that are used to split road lines."""
    HUB_FIELD_NAME = "HubName"
    ACCESS_POINT_ID_FIELD_NAME = "ap_id"
    ID_FIELD_NAME_BUILDINGS = "id"
    AP_ID_FIELD_NAME = "idx"

    def __init__(self):
        pass

    def set_preprocessing_result(self, preprocessing_result):
        self.exploded_roads = preprocessing_result.exploded_roads
        self.building_centroids = preprocessing_result.building_centroids
        self.ready_to_start = True

    def start(self) -> GraphCreatorResult:
        """
        Main Method of the Graph Creator. Executes the Graph Creation Pipeline.
        Only invokable after Preprocessing Result is set.

        :return: Finished Roads Graph.
        :rtype: GraphCreatorResult
        """
        if not self.ready_to_start:
            raise Exception("Preprocessing result is not set.")
        roads_as_points = DhpUtility.convert_line_to_points(layer=self.exploded_roads,
                                                            distance_of_points=self.DISTANCE_OF_POINTS,
                                                            debug=self.DEBUG)
        # Making sure that all necessary information are available in the roads_as_points layer.
        DhpUtility.add_field_and_copy_values(roads_as_points, "road_id", "osm_id")
        access_points_lines = self.find_building_access_points(roads_as_points)
        only_access_points = self.remove_unused_points(access_points_lines,
                                                       self.HUB_FIELD_NAME,
                                                       roads_as_points,
                                                       "idx")
        self.add_access_points_ids_to_buildings(access_points_lines, self.ACCESS_POINT_ID_FIELD_NAME, self.HUB_FIELD_NAME)
        Logger().info("Constructing roads graph.")
        self.add_access_points_to_roads_layer(only_access_points)
        DhpUtility.create_new_field(self.exploded_roads, "has_ap", QVariant.String)
        self.add_ap_lines_to_roads(only_access_points)
        nodes, edges = self.collect_roads_graph_nodes_and_edges()
        self.construct_nx_graph(nodes, edges)

        result = GraphCreatorResult(self.roads_graph, self.building_centroids, self.exploded_roads, access_points_lines)
        return result

    # ToDo: Check with Set for duplicates. Should speed this up!
    def collect_roads_graph_nodes_and_edges(self):
        """Constructs the roads graph only from roads.
        Note: If the node is a building, the key in the nodes dictionary is its ID.
        Its the coordinates of the node otherwise.
        """
        roads = self.exploded_roads.getFeatures()
        has_ap_idx = self.exploded_roads.fields().indexFromName('has_ap')
        connected_to_building_idx = self.exploded_roads.fields().indexFromName('connected_to_building')

        road_nodes = []
        nodes = {}
        edges = []
        # We iterate over every road in our selected roads to add them to our graph
        for road in roads:
            road_line = road.geometry().asPolyline()
            start_point = road_line[0]
            end_point = road_line[1]
            start_point_already_added = self.check_if_node_already_added(start_point, road_nodes)
            # we only want to add the starting point of a road, if it's not already present in the graph
            if start_point_already_added is None:
                road_nodes.append(start_point)
                new_start_node = GraphCreator.GraphNode(False, None, start_point)
                nodes[start_point] = new_start_node
                Logger().debug(f'added road_node starting point of road with id {road.id()}')
            else:
                start_point = start_point_already_added
                Logger().debug(f'starting point of road_node with id {road.id()} was already added')

            end_point_already_added = self.check_if_node_already_added(end_point, road_nodes)
            # same thing for the end point of a road. Only add it, if it's not already present in the graph
            if end_point_already_added is None:
                building_id = None
                if road.attributes()[has_ap_idx] == "True":
                    building_id = road.attributes()[connected_to_building_idx]
                    new_end_node = GraphCreator.GraphNode(True, building_id, end_point)
                    nodes[building_id] = new_end_node
                else:
                    new_end_node = GraphCreator.GraphNode(False, building_id, end_point)
                    nodes[building_id] = new_end_node
                road_nodes.append(end_point)
                Logger().debug(f'added road node ending point of road with id {road.id()}. Is connecting graph to building'
                               f' with id {building_id}')
            else:
                end_point = end_point_already_added
                Logger().debug(f'ending point of road_node with id {road.id()} was already added')

            weight_idx = road.fieldNameIndex('length')
            weight = road.attributes()[weight_idx]
            osm_id_idx = road.fieldNameIndex('osm_id')
            id_ = road.attributes()[osm_id_idx]
            edges.append(GraphCreator.GraphEdge(start_point, end_point, weight, id_))
        return (nodes, edges)

    def check_if_node_already_added(self, node, node_list: list):
        for existing_node in node_list:
            if node.x() == existing_node.x() and node.y() == existing_node.y():
                return existing_node
        return None

    def construct_nx_graph(self, nodes, edges):
        roads_graph = nx.Graph()
        for node_point, node_information in nodes.items():
            node_info = {
                'has_ap': node_information.has_ap,
                'building_id': node_information.building_id,
                'coordinates': node_information.coordinates
            }
            roads_graph.add_node(node_point, **node_info)
        for edge in edges:
            roads_graph.add_edge(edge.node_1, edge.node_2, weight=edge.weight, id=edge.id)
        self.roads_graph = roads_graph
        if self.DRAW_GRAPH:
            self.plot_graph(roads_graph)

    def plot_graph(self, roads_graph: nx.Graph):
        plt.figure(figsize=(50, 50))
        plt.rcParams["font.family"] = "DejaVu Sans"
        pos = nx.spring_layout(roads_graph)
        nx.draw(roads_graph, pos, with_labels=True)
        edge_labels = {edge: f'{weight:.2f}' for edge, weight in nx.get_edge_attributes(roads_graph, 'weight').items()}
        nx.draw_networkx_edge_labels(roads_graph, pos, edge_labels=edge_labels)
        # ToDo: Put the path in config!
        plt.savefig(Config().get_debug_folder_path()+'graph.png')

    def find_building_access_points(self, lines_as_points_layer: QgsVectorLayer):
        """

        :param lines_as_points_layer: A point layer that was generated from a lines layer.
        :type lines_as_points_layer:  QgsVectorLayer
        :return: a new layer with
        :rtype: QgsVectorLayer
        """
        # make road lines into points first, so we can find the shortest distance.
        roads_as_points = lines_as_points_layer

        result = processing.run("qgis:distancetonearesthublinetohub", {
            'INPUT': self.building_centroids,
            'HUBS': roads_as_points,
            'FIELD': 'idx',
            'UNIT': 0,
            'OUTPUT': "memory:"
        })
        output_layer = result['OUTPUT']
        output_layer.setName('Lines to Access Points')
        if self.DEBUG:
            QgsProject.instance().addMapLayer(output_layer)
        return output_layer

    def remove_unused_points(self, line_layer: QgsVectorLayer,
                             field_name_id_referral: str,
                             point_layer: QgsVectorLayer,
                             id_column_title: str):
        """
        Removes all points from a lines layer that is not specified as a point to keep.

        :param line_layer: the line layer featuring which points to keep.
        :type line_layer: QgsVectorLayer
        :param field_name_id_referral: the field name id on the line layer referring to the points.
        :type field_name_id_referral: str
        :param point_layer: the point layer featuring points to keep and points to remove.
        :type point_layer: QgsVectorLayer
        :param id_column_title: the id column title.
        :type id_column_title: str
        :return: the edited point layer.
        :rtype: QgsVectorLayer
        """
        ids_of_points_to_keep = []
        for line in line_layer.getFeatures():
            hub_idx = line.fieldNameIndex(field_name_id_referral)
            hub = line.attributes()[hub_idx]
            ids_of_points_to_keep.append(hub)
        expression = QgsExpression(f'"{id_column_title}" NOT IN ({", ".join([f"{p}" for p in ids_of_points_to_keep])})')
        request = QgsFeatureRequest(expression)
        requested_features = point_layer.getFeatures(request)
        point_feature_ids = [feature.id() for feature in requested_features]
        point_layer.startEditing()
        result = point_layer.dataProvider().deleteFeatures(point_feature_ids)
        if result:
            Logger().debug("unused points removed successfully.")
        else:
            raise GraphConstructionException("Removal of unused points failed.")
        point_layer.commitChanges()
        return point_layer

    def add_access_points_ids_to_buildings(self, access_lines_layer: QgsVectorLayer,
                                           access_points_id_field_name: str,
                                           hub_field_name: str):
        """

        :param access_lines_layer:
        :type access_lines_layer:
        :param access_points_id_field_name:
        :type access_points_id_field_name:
        :param hub_field_name:
        :type hub_field_name:
        """
        DhpUtility.create_new_field(self.building_centroids,
                                    access_points_id_field_name,
                                    QVariant.Int)
        for line in access_lines_layer.getFeatures():
            building_id = DhpUtility.get_value_from_field(access_lines_layer,
                                                          line,
                                                          self.ID_FIELD_NAME_BUILDINGS)
            hub_id = DhpUtility.get_value_from_field(access_lines_layer,
                                            line,
                                            self.HUB_FIELD_NAME)
            DhpUtility.assign_value_to_field(self.building_centroids,
                                             access_points_id_field_name,
                                             DhpUtility.get_feature_by_id_field(self.building_centroids,
                                                                                "id",
                                                                                int(building_id)),
                                            int(hub_id))

    def add_access_points_to_roads_layer(self, access_points):
        roads = self.exploded_roads
        roads_provider = roads.dataProvider()
        access_points_features = access_points.getFeatures()
        # ToDo: Put those into another function! I don't need to create the fields here!

        road_split_points = {}
        # we need to obtain the right roads further down the line
        # we want to obtain the roads that have an access point on them.
        road_id_idx = access_points.fields().indexFromName('road_id')
        roads.startEditing()
        # first we add all the roads that are to be split and the
        # access points we want to split them by.
        for access_point in access_points_features:
            road_id = access_point.attributes()[road_id_idx]
            Logger().debug(f"road to split added: {road_id}.")
            if road_id not in road_split_points:
                road_split_points[road_id] = []
            road_split_points[road_id].append(access_point)
            Logger().debug(f"road with id {road_id} to be split at access point {access_point.id()}.")
        for road_id, p in road_split_points.items():
            p_dict = {}
            reconnection_list = []
            road = DhpUtility.get_feature_by_id_field(roads, 'osm_id', road_id)
            road_line = road.geometry().asPolyline()
            road_start = road_line[0]
            road_end = road_line[-1]
            # if the road is to be split at multiple points, we need to obtain
            # the distance of each access point from the starting point of the road
            for point in p:
                point_x = point.geometry().asPoint().x()
                point_y = point.geometry().asPoint().y()
                dx = abs(point_x - road_start.x())
                dy = abs(point_y - road_start.y())
                distance = dx + dy
                p_dict[point.id()] = distance
            # now we can order the points that we have to split the road by
            # thus we can connect each point by a line starting from the starting point
            # of the road.
            if len(p_dict) > 0:
                dict(sorted(p_dict.items()))
            reconnection_list.append((road_start, None))
            for p_id in p_dict.keys():
                point = access_points.getFeature(p_id)
                pxy = QgsPointXY(point.geometry().asPoint().x(), point.geometry().asPoint().y())
                reconnection_list.append((pxy, point))
            reconnection_list.append((road_end, None))
            source_attributes = road.attributes()
            length_of_reconnection_list = len(reconnection_list)
            iteration = 0
            for i in range(len(reconnection_list) - 1):
                is_last_iteration = (iteration == (length_of_reconnection_list - 2))
                first_element = reconnection_list[i]
                second_element = reconnection_list[i + 1]
                end_element = reconnection_list[-1]
                pxy_1 = first_element[0]
                pxy_2 = second_element[0]
                pxy_end = end_element[0]

                # if the road is very short there is a chance that the access point is on the end
                # point of the road. We don't have to split the road then and can break immediately.
                condition = iteration == 0 and (pxy_1 == pxy_2 or pxy_2 == pxy_end) and length_of_reconnection_list <= 3
                if condition:
                    line_geometry = QgsGeometry.fromPolylineXY([pxy_1, pxy_end])
                    feature = QgsFeature()
                    feature.setGeometry(line_geometry)
                    feature.setAttributes(source_attributes)
                    new_road_id = DhpUtility.assign_unique_id_custom_id_field(roads, feature, "osm_id")
                    DhpUtility.assign_value_to_field(roads, "length", feature, line_geometry.length())
                    DhpUtility.assign_value_to_field(access_points, "road_id", second_element[1], new_road_id)
                    roads_provider.addFeature(feature)
                    break
                # otherwise we end up here:
                line_geometry = QgsGeometry.fromPolylineXY([pxy_1, pxy_2])
                feature = QgsFeature()
                feature.setGeometry(line_geometry)
                feature.setAttributes(source_attributes)
                new_road_id = DhpUtility.assign_unique_id_custom_id_field(roads, feature, "osm_id")
                DhpUtility.assign_value_to_field(roads, "length", feature, line_geometry.length())
                if not is_last_iteration:
                    # we also need to update the value in the access points.
                    DhpUtility.assign_value_to_field(access_points, "road_id", second_element[1], new_road_id)
                roads_provider.addFeature(feature)
                iteration += 1
            DhpUtility.delete_features_custom_id(roads, "osm_id", road_id)
        roads.commitChanges()

    def add_ap_lines_to_roads(self, ap_layer):
        roads_provider = self.exploded_roads.dataProvider()
        DhpUtility.add_field(self.exploded_roads,
                             "connected_to_building",
                             self.building_centroids.fields().field('osm_id').type())
        road_fields = self.exploded_roads.fields()
        for centroid in self.building_centroids.getFeatures():
            ap_id = DhpUtility.get_value_from_field(self.building_centroids,
                                                    centroid,
                                                    self.ACCESS_POINT_ID_FIELD_NAME)
            ap_xy = DhpUtility.get_xy_by_id_field(ap_layer,
                                                  self.AP_ID_FIELD_NAME,
                                                  int(ap_id))
            ap_xy_point = QgsPointXY(ap_xy[0], ap_xy[1])
            centroid_xy = DhpUtility.get_xy_by_id_field(self.building_centroids,
                                                        "id",
                                                        centroid.id())
            centroid_xy_point = QgsPointXY(centroid_xy[0], centroid_xy[1])
            road_line = QgsGeometry.fromPolylineXY([ap_xy_point, centroid_xy_point])
            feature = QgsFeature()
            feature.setGeometry(road_line)
            feature.setFields(road_fields)
            DhpUtility.assign_unique_id_custom_id_field(self.exploded_roads,
                                                        feature,
                                                        "osm_id")
            DhpUtility.assign_value_to_field(self.exploded_roads,
                                             "length",
                                             feature,
                                             0)
            DhpUtility.assign_value_to_field(self.exploded_roads,
                                             "has_ap",
                                             feature,
                                             "True")
            DhpUtility.assign_value_to_field(self.exploded_roads,
                                             "connected_to_building",
                                             feature,
                                             DhpUtility.get_value_from_field(self.building_centroids,
                                                                             centroid,
                                                                             "osm_id"))
            roads_provider.addFeature(feature)
