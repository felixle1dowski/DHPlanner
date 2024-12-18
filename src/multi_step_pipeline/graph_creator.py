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
        has_ap : bool
        ap_id : int
        coordinates : QgsPointXY

        def __init__(self, has_ap, ap_id, coordinates):
            self.has_ap = has_ap
            self.ap_id = ap_id
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

    ready_to_start = False
    exploded_roads = None
    building_centroids = None
    roads_graph = None
    graph_representation = None
    DISTANCE_OF_POINTS = 5.0
    """Interval of Points that are to be regarded in the calculation of access points."""
    DRAW_GRAPH = False
    """Indiciates whether there's a plot of a graph to be generated for debugging purposes."""
    PERP_LINE_LENGTH = 20.0
    """Determines the length of the perpendicular lines that are used to split road lines."""

    def __init__(self):
        pass

    def set_preprocessing_result(self, preprocessing_result):
        self.exploded_roads = preprocessing_result.exploded_roads
        self.building_centroids = preprocessing_result.building_centroids
        self.ready_to_start = True

    def start(self):
        """Central method of GraphCreator class. Returns Complete graph and representation layer.
        (That means that all start and end points of roads are also present,
        even if they aren't needed in further processing.)"""
        if not self.ready_to_start:
            raise Exception("Preprocessing result is not set.")
        roads_as_points = self.__convert_line_to_points(self.exploded_roads)
        DhpUtility.add_field_and_copy_values(roads_as_points, "road_id", "id")
        DhpUtility.copy_values_between_fields(roads_as_points, "idx", "id")
        access_points_lines = self.__find_building_access_points(roads_as_points)
        only_access_points = self.__remove_unused_points(access_points_lines, roads_as_points, "idx")
        self.__add_access_points_ids_to_buildings(access_points_lines)
        Logger().info("Constructing roads graph.")
        self.__add_access_points_to_roads_layer(only_access_points)
        nodes, edges = self.__collect_roads_graph_nodes_and_edges()
        self.__construct_nx_graph(nodes, edges)

        result = GraphCreatorResult(self.roads_graph, self.building_centroids, self.exploded_roads, access_points_lines)
        return result

    # ToDo: Check with Set for duplicates. Should speed this up!
    def __collect_roads_graph_nodes_and_edges(self):
        """Constructs the roads graph only from roads."""
        roads = self.exploded_roads.getFeatures()
        has_ap_idx = self.exploded_roads.fields().indexFromName('has_ap')
        ap_id_idx = self.exploded_roads.fields().indexFromName('ap_id')

        road_nodes = []
        nodes = {}
        edges = []
        # We iterate over every road in our selected roads to add them to our graph
        for road in roads:
            road_line = road.geometry().asPolyline()
            start_point = road_line[0]
            end_point = road_line[1]
            start_point_already_added = self.__check_if_node_already_added(start_point, road_nodes)
            # we only want to add the starting point of a road, if it's not already present in the graph
            if start_point_already_added is None:
                road_nodes.append(start_point)
                new_start_node = GraphCreator.GraphNode(False, None, start_point)
                nodes[start_point] = new_start_node
                Logger().debug(f'added road_node starting point of road with id {road.id()}')
            else:
                start_point = start_point_already_added
                Logger().debug(f'starting point of road_node with id {road.id()} was already added')
            if start_point_already_added is not None and road.attributes()[has_ap_idx] == "True":
                start_point_to_upgrade = nodes[start_point]
                start_point_to_upgrade.has_ap = True
                start_point_to_upgrade.ap_id = road.attributes()[ap_id_idx]
                Logger().debug(f'an end-node was upgraded to have an ap. Ap with id '
                               f'{start_point_to_upgrade.ap_id} was added.')
        ###############################################################################

            end_point_already_added = self.__check_if_node_already_added(end_point, road_nodes)
            # same thing for the end point of a road. Only add it, if it's not already present in the graph
            if end_point_already_added is None:
                ap_id = None
                if road.attributes()[has_ap_idx] == "True":
                    new_end_node = GraphCreator.GraphNode(True, ap_id, end_point)
                else:
                    new_end_node = GraphCreator.GraphNode(False, ap_id, end_point)
                road_nodes.append(end_point)
                nodes[end_point] = new_end_node
                Logger().debug(f'ap with id {ap_id} was added to road with id {road.id()}')
            else:
                end_point = end_point_already_added
                Logger().debug(f'ending point of road_node with id {road.id()} was already added')
            # however, if we come from a different direction to a node and from this direction it "has" an ap
            # we need to upgrade the node to have an ap.
            if end_point_already_added is not None and road.attributes()[has_ap_idx] == "True":
                end_point_to_upgrade = nodes[end_point]
                end_point_to_upgrade.has_ap = True
                end_point_to_upgrade.ap_id = road.attributes()[ap_id_idx]
                Logger().debug(f'an end-node was upgraded to have an ap. Ap with id '
                               f'{end_point_to_upgrade.ap_id} was added.')
            ###############################################################################

            weight_idx = road.fieldNameIndex('length')
            weight = road.attributes()[weight_idx]
            id_idx = road.fieldNameIndex('id')
            id = road.attributes()[id_idx]
            edges.append(GraphCreator.GraphEdge(start_point, end_point, weight, id))
        return (nodes, edges)

    def __check_if_node_already_added(self, node, node_list: list):
        for existing_node in node_list:
            if node.x() == existing_node.x() and node.y() == existing_node.y():
                return existing_node
        return None

    def __construct_nx_graph(self, nodes, edges):
        roads_graph = nx.Graph()
        for node_point, node_information in nodes.items():
            node_info = {
                'has_ap': node_information.has_ap,
                'ap_id': node_information.ap_id,
                'coordinates': node_information.coordinates
            }
            roads_graph.add_node(node_point, **node_info)
        for edge in edges:
            roads_graph.add_edge(edge.node_1, edge.node_2, weight=edge.weight, id=edge.id)
        self.roads_graph = roads_graph
        if self.DRAW_GRAPH:
            self.__plot_graph(roads_graph)

    def __plot_graph(self, roads_graph: nx.Graph):
        plt.figure(figsize=(50,50))
        pos = nx.spring_layout(roads_graph)
        nx.draw(roads_graph, pos, with_labels=True)
        edge_labels = {edge: f'{weight:.2f}' for edge, weight in nx.get_edge_attributes(roads_graph, 'weight').items()}
        nx.draw_networkx_edge_labels(roads_graph, pos, edge_labels=edge_labels)
        # ToDo: Put the path in config!
        plt.savefig('/Users/felixlewandowski/Documents/ba/graph.png')

    def __find_building_access_points(self, lines_as_points_layer):
        """Find the building access points. Adds them to graph representation layer."""
        provider = self.building_centroids.dataProvider()
        max_id = max([feature['id'] for feature in self.building_centroids.getFeatures() if isinstance(feature['id'], (int, float))], default=0)

        # make road lines into points first, so we can find the shortest distance.
        roads_as_points = lines_as_points_layer

        result = processing.run("qgis:distancetonearesthublinetohub", {
            'INPUT': self.building_centroids,
            'HUBS': roads_as_points,
            'FIELD': 'idx',
            'UNIT': 0,
            'OUTPUT': "memory:"
        })
        # ToDo: For debugging purposes! The GUI representation is for debugging. Layer can be kept internally.
        output_layer = result['OUTPUT']
        output_layer.setName('Lines to Access Points')
        QgsProject.instance().addMapLayer(output_layer)
        return output_layer

    def __convert_line_to_points(self, layer):
        output_layer_path = "memory:"
        result = processing.run("native:pointsalonglines", {
            'INPUT': layer,
            'OUTPUT': output_layer_path,
            'DISTANCE': self.DISTANCE_OF_POINTS,
        })
        # ToDo: For debugging purposes!
        output_layer = result['OUTPUT']
        output_layer.setName('points_on_line')
        DhpUtility.assign_unique_ids(output_layer, "idx")
        QgsProject.instance().addMapLayer(output_layer)
        return output_layer

    def __remove_unused_points(self, line_layer, point_layer, id_column_title):
        """removes points by ids obtained by line layer. Only usable if a connection id is
        available."""
        ids_of_points_to_keep = []
        for line in line_layer.getFeatures():
            hub_idx = line.fieldNameIndex('HubName')
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

    def __add_access_points_ids_to_buildings(self, access_lines_layer):
        building_points = self.building_centroids.getFeatures()
        access_point_id_column_name = "ap_id"
        building_points_provider = self.building_centroids.dataProvider()
        self.building_centroids.startEditing()
        building_points_provider.addAttributes([QgsField(f"{access_point_id_column_name}",
                                                                       QVariant.Int)])
        self.building_centroids.updateFields()
        for line in access_lines_layer.getFeatures():
            building_id = line.id()
            hub_idx = line.fieldNameIndex('HubName')
            hub_id = line.attributes()[hub_idx]
            ap_id_idx = self.building_centroids.fields().indexFromName(access_point_id_column_name)
            (self.building_centroids
             .changeAttributeValue(building_id,
                                   ap_id_idx,
                                   hub_id))
        self.building_centroids.commitChanges()

    def __add_access_points_to_roads_layer(self, access_points):
        roads = self.exploded_roads
        roads_provider = roads.dataProvider()
        access_points_features = access_points.getFeatures()
        DhpUtility.create_new_field(roads, "has_ap", QVariant.String)
        DhpUtility.create_new_field(roads, "ap_id", QVariant.Int)
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
            road = roads.getFeature(road_id)
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
                    new_road_id = DhpUtility.assign_unique_id(roads, feature, "id")
                    DhpUtility.assign_value_to_field(roads, "length", feature, line_geometry.length())
                    DhpUtility.assign_value_to_field(access_points, "road_id", second_element[1], new_road_id)
                    DhpUtility.assign_value_to_field(roads, "has_ap", feature, "True")
                    ap_id = second_element[1].id()
                    DhpUtility.assign_value_to_field(roads, "ap_id", feature, ap_id)
                    roads_provider.addFeature(feature)
                    break

                line_geometry = QgsGeometry.fromPolylineXY([pxy_1, pxy_2])
                feature = QgsFeature()
                feature.setGeometry(line_geometry)
                feature.setAttributes(source_attributes)
                new_road_id = DhpUtility.assign_unique_id(roads, feature, "id")
                DhpUtility.assign_value_to_field(roads, "length", feature, line_geometry.length())
                if not is_last_iteration:
                    DhpUtility.assign_value_to_field(roads, "has_ap", feature, "True")
                    ap_id = second_element[1].id()
                    DhpUtility.assign_value_to_field(roads, "ap_id", feature, ap_id)
                    # we also need to update the value in the access points.
                    DhpUtility.assign_value_to_field(access_points, "road_id", second_element[1], new_road_id)

                else:
                    DhpUtility.assign_value_to_field(roads, "has_ap", feature, "False")
                roads_provider.addFeature(feature)
                iteration += 1
            roads_provider.deleteFeatures([road_id])
        roads.commitChanges()

    def __split_roads_with_point(self):
        """Splits road by a point."""

    def __add_building_nodes_to_graph(self):
        """Add building nodes to the graph."""
