from .preprocessing_result import PreprocessingResult
from .logger import Logger
from .config import Config
import networkx as nx
import matplotlib.pyplot as plt
from qgis.core import QgsGeometry, QgsPointXY, QgsFeature

class GraphCreator:

    ready_to_start = False
    exploded_roads = None
    building_centroids = None
    roads_graph = None
    graph_representation = None

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
        Logger().info("Constructing roads graph.")
        self.__construct_roads_graph()
        self.__find_building_access_points()

    def __construct_roads_graph(self):
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
            if Config().get_log_level() == "debug":
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

    def __find_building_access_points(self):
        """Find the building access points. Adds them to graph representation layer."""
        provider = self.building_centroids.dataProvider()
        max_id = max([feature['id'] for feature in self.building_centroids.getFeatures() if isinstance(feature['id'], (int, float))], default=0)

        for building_point in self.building_centroids.getFeatures():
            building_geom = building_point.geometry()

            # find nearest road
            nearest_distance = float('inf')
            nearest_point = None

            for road in self.exploded_roads.getFeatures():
                road_geom = road.geometry()
                nearest = road_geom.closestSegmentWithContext(building_geom)
                dist = building_geom.distance(QgsGeometry.fromPointXY(nearest[0]))

                if nearest_distance is None or dist < nearest_distance:
                    nearest_distance = dist
                    nearest_point = nearest[0]

            nearest_x = nearest_point.x()
            nearest_y = nearest_point.y()
            # add access points to the building centroids
            if nearest_x is not None and nearest_y is not None:
                max_id += 1
                access_point = QgsPointXY(nearest_x, nearest_y)
                access_point_feature = QgsFeature()
                access_point_feature.setAttribute('id', max_id)
                access_point_feature.setAttribute('Type', "Access Point")
                access_point_feature.setGeometry(access_point)
                provider.addFeature(access_point_feature)
        self.building_centroids.commitChanges()



    def __add_access_points_to_graph(self):
        """Helper method to add access points to graph representation layer."""

    def __split_roads_with_point(self):
        """Splits road by a point."""