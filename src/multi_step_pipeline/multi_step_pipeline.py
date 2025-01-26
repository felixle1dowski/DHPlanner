import random

from ..dhc_creation_pipeline import DHCCreationPipeline
from ..util.logger import Logger
from ..util.logger import Config
import time
import networkx as nx


class MultiStepPipeline(DHCCreationPipeline):
    preprocessing = None
    graph_creator = None
    shortest_path_creator = None
    mst_visualizer = None
    clustering_first_stage = None
    clustering_second_stage = None
    feasible_solution_creator = None

    def __init__(self, preprocessor, clustering_first_stage, feasible_solution_creator, clustering_second_stage,
                 graph_creator, shortest_path_creator, mst_visualizer):
        self.preprocessing = preprocessor
        self.clustering_first_stage = clustering_first_stage
        self.feasible_solution_creator = feasible_solution_creator
        self.clustering_second_stage = clustering_second_stage
        self.graph_creator = graph_creator
        self.shortest_path_creator = shortest_path_creator
        self.mst_visualizer = mst_visualizer

    def start(self):
        Logger().info("Starting Preprocessing.")
        preprocessing_result = self.timed_wrapper(self.preprocessing.start)
        Logger().info("Finished Preprocessing.")
        graph, building_to_point_dict, line_layer = self.graph_creator.start(
            strategy=Config().get_installation_strategy(),
            exploded_roads=preprocessing_result.exploded_roads,
            building_centroids=preprocessing_result.building_centroids)
        self.shortest_path_creator.set_required_fields(graph, line_layer, list(building_to_point_dict.values()))
        shortest_paths = self.shortest_path_creator.start()

        if Config().get_distance_measuring_method() == "custom":
            # ToDo: Put this into function!
            adjacency_matrix = nx.adjacency_matrix(shortest_paths).todense()
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
        self.clustering_first_stage.start()

        # random_items = dict(random.sample(building_to_point_dict.items(), 5)).values()
        # ToDo: testing...
        # self.mst_creator.visualize_subgraph_mst(shortest_paths, random_items)
        # Logger().info("Finished MST Creation.")

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
