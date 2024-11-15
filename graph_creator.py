from preprocessing_result import PreprocessingResult


class GraphCreator:

    exploded_roads = None
    building_centroids = None
    graph_representation = None

    def __init__(self, preprocessing_result: PreprocessingResult):
        self.building_centroids = preprocessing_result.building_centroids
        self.exploded_roads = preprocessing_result.exploded_roads

    def start(self):
        """Central method of GraphCreator class. Returns Complete graph and representation layer.
        (That means that all start and end points of roads are also present,
        even if they aren't needed in further processing.)"""

    def __construct_roads_graph(self):
        """Constructs the roads graph."""

    def __find_building_access_points(self):
        """Find the building access points. Adds them to graph representation layer."""

    def __add_access_points_to_graph(self):
        """Helper method to add access points to graph representation layer."""

    def __split_roads_with_point(self):
        """Splits road by a point."""