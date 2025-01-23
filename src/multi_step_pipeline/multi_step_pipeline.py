from ..dhc_creation_pipeline import DHCCreationPipeline
from ..util.logger import Logger
from ..util.logger import Config
from qgis.core import (QgsProject)
import time


class MultiStepPipeline(DHCCreationPipeline):

    preprocessing = None
    graph_creator = None
    mst_creator = None
    mst_visualizer = None
    clustering_first_stage = None
    clustering_second_stage = None
    feasible_solution_creator = None

    def __init__(self, preprocessor, clustering_first_stage, feasible_solution_creator, clustering_second_stage, graph_creator, mst_creator, mst_visualizer):
        self.preprocessing = preprocessor
        self.clustering_first_stage = clustering_first_stage
        self.feasible_solution_creator = feasible_solution_creator
        self.clustering_second_stage = clustering_second_stage
        self.graph_creator = graph_creator
        self.mst_creator = mst_creator
        self.mst_visualizer = mst_visualizer

    def start(self):
        Logger().info("Starting Preprocessing.")
        preprocessing_result = self.timed_wrapper(self.preprocessing.start)
        Logger().info("Finished Preprocessing.")
        Logger().info("Starting First Stage Clustering.")
        self.graph_creator.set_preprocessing_result(preprocessing_result)
        graph_creation_result = self.graph_creator.start()
        self.mst_creator.set_graph_creator_result(graph_creation_result)
        self.timed_wrapper(self.mst_creator.start)
        Logger().info("Finished MST Creation.")




        # self.clustering_first_stage.set_preprocessing_result(preprocessing_result.building_centroids)
        # clustering_first_stage_result = self.timed_wrapper(self.clustering_first_stage.start)
        # Logger().info("Finished First Stage Clustering.")
        # Logger().info("Starting Second Stage Clustering.")
        # # ToDo: This is dirty. Change this by creating a shared resources class that holds ressources like this.
        # buildings_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        # self.clustering_second_stage.set_first_stage_result(clustering_first_stage_result,
        #                                                     buildings_layer,
        #                                                     preprocessing_result.building_centroids,
        #                                                     self.feasible_solution_creator)
        # self.timed_wrapper(self.clustering_second_stage.start)
        # Logger().info("Finished Second Stage Clustering.")

        # self.graph_creator.set_preprocessing_result(preprocessing_result)
        # graph_creation_result = self.timed_wrapper(self.graph_creator.start)
        # Logger().info("Finished Graph Creation.")
        # Logger().info("Starting MST Creation.")
        # self.mst_creator.set_graph_creator_result(graph_creation_result)
        # self.timed_wrapper(self.mst_creator.start)
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