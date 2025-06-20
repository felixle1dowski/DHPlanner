import random

from ..dhc_creation_pipeline import DHCCreationPipeline
from ..util.logger import Logger
from ..util.logger import Config
import time
import networkx as nx
from qgis.core import QgsProject


class MultiStepPipeline(DHCCreationPipeline):
    preprocessing = None
    graph_creator = None
    shortest_path_creator = None
    mst_visualizer = None
    clustering_first_stage = None
    clustering_second_stage = None
    feasible_solution_creator = None
    visualization = None

    def __init__(self, preprocessor, clustering_first_stage, feasible_solution_creator, clustering_second_stage,
                 graph_creator, shortest_path_creator, mst_visualizer, visualization):
        self.preprocessing = preprocessor
        self.clustering_first_stage = clustering_first_stage
        self.feasible_solution_creator = feasible_solution_creator
        self.clustering_second_stage = clustering_second_stage
        self.graph_creator = graph_creator
        self.shortest_path_creator = shortest_path_creator
        self.mst_visualizer = mst_visualizer
        self.visualization = visualization

    def start(self):
        # Logger().info("Starting Preprocessing.")
        preprocessing_result = self.timed_wrapper(self.preprocessing.start)
        # Logger().info("Finished Preprocessing.")
        graph, building_to_point_dict, line_layer = self.graph_creator.start(
            strategy=Config().get_installation_strategy(),
            exploded_roads=preprocessing_result.exploded_roads,
            building_centroids=preprocessing_result.building_centroids)
        self.shortest_path_creator.set_required_fields(graph, line_layer, list(building_to_point_dict.values()),
                                                       preprocessing_result.exploded_roads)
        shortest_paths = self.shortest_path_creator.start()

        if Config().get_distance_measuring_method() == "custom":
            # ToDo: Put this into function!
            adjacency_matrix = self.shortest_path_creator.get_adjacency_matrix_with_custom_weights(shortest_paths)
            # Logger().debug(f"'adjacency matrix is {adjacency_matrix}")
            nodes = list(shortest_paths.nodes())
            # translate nodes
            translated_nodes = []
            reverse_translation = dict(zip(building_to_point_dict.values(), building_to_point_dict.keys()))
            for node in nodes:
                translated_nodes.append(reverse_translation[node])
            self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids,
                                                            adjacency_matrix,
                                                            translated_nodes)
        else:
            self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids)
        clustering_first_stage_results = self.clustering_first_stage.start()
        self.clustering_second_stage.set_required_fields(shortest_path_graph=shortest_paths,
                                                         first_stage_cluster_dict=clustering_first_stage_results,
                                                         # ToDo: This is only in because of sloppy visualization. Remove!!
                                                         buildings_layer=QgsProject.instance().mapLayersByName(
                                                             Config().get_buildings_layer_name())[0],
                                                         building_centroids_layer=preprocessing_result.building_centroids,
                                                         feasible_solution_creator=self.feasible_solution_creator,
                                                         graph_translation_dict=building_to_point_dict)
        clustering_second_stage_results = self.clustering_second_stage.start()
        self.visualization.set_required_fields(preprocessing_result.exploded_roads, clustering_second_stage_results,
                                               preprocessing_result.building_centroids)
        self.visualization.start()

    def timed_wrapper(self, function_call, *args, **kwargs):
        function_name = self.get_fully_qualified_name(function_call)
        start_time = time.time()
        result = function_call(*args, **kwargs)
        end_time = time.time()
        Logger().info(f"Function {function_name} took {end_time - start_time} seconds.")
        return result

    @staticmethod
    def get_fully_qualified_name(function_call):
        """Returns the fully qualified name of a function."""
        if hasattr(function_call, "__self__") and function_call.__self__:
            # Method of a class instance
            class_name = function_call.__self__.__class__.__name__
            return f"{class_name}.{function_call.__name__}"
        elif hasattr(function_call, "__module__"):
            # Function from a module
            return f"{function_call.__module__}.{function_call.__name__}"
        else:
            # Standalone function
            return function_call.__name__
