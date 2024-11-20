import math

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
        self.__construct_roads_graph()
        result = GraphCreatorResult(self.roads_graph, self.building_centroids, self.exploded_roads, access_points_lines)
        return result

    # ToDo: Check with Set for duplicates. Should speed this up!
    def __construct_roads_graph(self):
        """Constructs the roads graph only from roads."""
        self.roads_graph = nx.Graph()
        roads_graph = self.roads_graph
        roads = self.exploded_roads.getFeatures()
        has_ap_idx = self.exploded_roads.fields().indexFromName('has_ap')
        ap_id_idx = self.exploded_roads.fields().indexFromName('ap_id')

        road_nodes = []
        for road in roads:
            road_line = road.geometry().asPolyline()
            start_point = road_line[0]
            end_point = road_line[1]
            start_point_already_added = self.__check_if_node_already_added(start_point, road_nodes)
            is_ap = False
            if start_point_already_added is None:
                start_node_info = {
                    'has_ap': False,
                    'ap_id': None,
                    'coordinates': start_point
                }
                roads_graph.add_node(start_point, **start_node_info)
                road_nodes.append(start_point)
            else:
                start_point = start_point_already_added
            end_point_already_added = self.__check_if_node_already_added(end_point, road_nodes)
            if end_point_already_added is None:
                if road.attributes()[has_ap_idx] == "True":
                    ap_id = road.attributes()[ap_id_idx]
                    end_node_info = {
                        'has_ap': True,
                        'ap_id': ap_id,
                        'coordinates': end_point
                    }
                else:
                    end_node_info = {
                        'has_ap': False,
                        'ap_id': None,
                        'coordinates': end_point
                    }
                roads_graph.add_node(end_point, **end_node_info)
                road_nodes.append(end_point)
            else:
                end_point = end_point_already_added
            weight_idx = road.fieldNameIndex('length')
            weight = road.attributes()[weight_idx]
            id_idx = road.fieldNameIndex('id')
            id = road.attributes()[id_idx]
            roads_graph.add_edge(start_point, end_point, weight=weight, id=id)
            Logger().debug(nx.info(roads_graph))
        self.roads_graph = roads_graph
        if self.DRAW_GRAPH:
            self.__plot_graph(roads_graph)


    def __check_if_node_already_added(self, node, node_list: list):
        for existing_node in node_list:
            if node.x() == existing_node.x() and node.y() == existing_node.y():
                return existing_node
        return None

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
        road_id_idx = access_points.fields().indexFromName('road_id')
        roads.startEditing()
        for access_point in access_points_features:
            road_id = access_point.attributes()[road_id_idx]
            Logger().debug(f"Adding road with road id {road_id}")
            if road_id not in road_split_points:
                road_split_points[road_id] = []
            road_split_points[road_id].append(access_point)
            Logger().debug(f"Adding point with point id {access_point.id()}")
        for road_id, p in road_split_points.items():
            p_dict = {}
            reconnection_list = []
            road = roads.getFeature(road_id)
            road_line = road.geometry().asPolyline()
            road_start = road_line[0]
            road_end = road_line[-1]
            if len(p) > 1:
                for point in p:
                    point_x = point.geometry().asPoint().x()
                    point_y = point.geometry().asPoint().y()
                    dx = abs(point_x - road_start.x())
                    dy = abs(point_y - road_start.y())
                    distance = dx + dy
                    p_dict[point.id()] = distance
            if len(p_dict) > 0:
                dict(sorted(p_dict.items()))
            reconnection_list.append((road_start, None))
            if len(p) == 1:
                point = p[0]
                pxy = QgsPointXY(point.geometry().asPoint().x(), point.geometry().asPoint().y())
                reconnection_list.append((pxy, point))
            for p_id in p_dict.keys():
                point = access_points.getFeature(p_id)
                pxy = QgsPointXY(point.geometry().asPoint().x(), point.geometry().asPoint().y())
                reconnection_list.append((pxy, point))
            reconnection_list.append((road_end, None))
            source_attributes = road.attributes()
            roads_provider.deleteFeatures([road_id])
            length_of_reconnection_list = len(reconnection_list)
            iteration = 0
            for i in range(len(reconnection_list) - 1):
                is_last = (iteration == (length_of_reconnection_list - 2))
                first_element = reconnection_list[i]
                second_element = reconnection_list[i + 1]
                pxy_1 = first_element[0]
                pxy_2 = second_element[0]
                line_geometry = QgsGeometry.fromPolylineXY([pxy_1, pxy_2])
                feature = QgsFeature()
                feature.setGeometry(line_geometry)
                feature.setAttributes(source_attributes)
                DhpUtility.assign_unique_id(roads, feature, "id")
                DhpUtility.assign_value_to_field(roads, "length", feature, line_geometry.length())
                if not is_last:
                    DhpUtility.assign_value_to_field(roads, "has_ap", feature, "True")
                    ap_id = second_element[1].id()
                    DhpUtility.assign_value_to_field(roads, "ap_id", feature, ap_id)
                else:
                    DhpUtility.assign_value_to_field(roads, "has_ap", feature, "False")
                roads_provider.addFeature(feature)
                iteration += 1
        roads.commitChanges()

    def __split_roads_with_point(self):
        """Splits road by a point."""

    def __add_building_nodes_to_graph(self):
        """Add building nodes to the graph."""
