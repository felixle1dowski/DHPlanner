from .preprocessing_result import PreprocessingResult
from .logger import Logger
import networkx as nx

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

    def __construct_roads_graph(self):
        """Constructs the roads graph."""
        self.roads_graph = nx.Graph()
        roads_features = self.exploded_roads.getFeatures()
        for road in roads_features:
            idx = road.fieldNameIndex("id")
            lengthx = road.fieldNameIndex("length")
            polyline = road.geometry().asPolyline()
            Logger().debug( f"road with id: {road.attributes()[idx]} \n"
                            f"and length: {road.attributes()[lengthx]} \n"
                            f"has len(): {len(polyline)} \n"
                            f"presumed starting point: {polyline[0]} \n"
                            f"presumed ending point: {polyline[-1]}.")

    def __find_building_access_points(self):
        """Find the building access points. Adds them to graph representation layer."""

    def __add_access_points_to_graph(self):
        """Helper method to add access points to graph representation layer."""

    def __split_roads_with_point(self):
        """Splits road by a point."""