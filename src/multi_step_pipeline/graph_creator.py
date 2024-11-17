from ..util.logger import Logger
from ..util.dhp_utility import DhpUtility
import networkx as nx
from PyQt5.QtCore import QVariant
import matplotlib.pyplot as plt
from qgis.core import (QgsProject, QgsExpression,
                       QgsFeatureRequest, QgsField)
from qgis import processing

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
        DhpUtility.add_field_and_copy_values(roads_as_points, "road_ids", "id")
        DhpUtility.copy_values_between_fields(roads_as_points, "idx", "id")
        access_points_lines = self.__find_building_access_points(roads_as_points)
        only_access_points = self.__remove_unused_points(access_points_lines, roads_as_points, "idx")
        self.__add_access_points_ids_to_buildings(access_points_lines)
        Logger().info("Constructing roads graph.")
        self.__construct_roads_graph(only_access_points)


    def __construct_roads_graph(self, access_points):
        """Constructs the roads graph only from roads."""
        self.roads_graph = nx.Graph()
        roads_graph = self.roads_graph
        roads = self.exploded_roads.getFeatures()

        road_nodes = []
        for road in roads:
            road_line = road.geometry().asPolyline()
            start_point = road_line[0]
            end_point = road_line[1]
            start_point_already_added = self.__check_if_node_already_added(start_point, road_nodes)
            if start_point_already_added is None:
                roads_graph.add_node(start_point)
                road_nodes.append(start_point)
            else:
                start_point = start_point_already_added
            end_point_already_added = self.__check_if_node_already_added(end_point, road_nodes)
            if end_point_already_added is None:
                roads_graph.add_node(end_point)
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
        DhpUtility.assign_unique_id(output_layer, "idx")
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
        point_layer.commitChanges()
        return result

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

    def __add_access_points_to_graph(self):
        """Helper method to add access points to graph representation layer."""

    def __split_roads_with_point(self):
        """Splits road by a point."""