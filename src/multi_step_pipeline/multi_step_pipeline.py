from ..dhc_creation_pipeline import DHCCreationPipeline
from ..util.logger import Logger
import time


class MultiStepPipeline(DHCCreationPipeline):

    preprocessing = None
    graph_creator = None
    mst_creator = None
    mst_visualizer = None

    def __init__(self, preprocessor, graph_creator, mst_creator, mst_visualizer):
        self.preprocessing = preprocessor
        self.graph_creator = graph_creator
        self.mst_creator = mst_creator
        self.mst_visualizer = mst_visualizer

    def start(self):
        Logger().info("Starting Preprocessing.")
        preprocessing_result = self.timed_wrapper(self.preprocessing.start)
        Logger().info("Finished Preprocessing.")
        Logger().info("Starting Graph Creation.")
        self.graph_creator.set_preprocessing_result(preprocessing_result)
        graph_creation_result = self.timed_wrapper(self.graph_creator.start)
        Logger().info("Finished Graph Creation.")
        Logger().info("Starting MST Creation.")
        self.mst_creator.set_graph_creator_result(graph_creation_result)
        self.timed_wrapper(self.mst_creator.start)
        Logger().info("Finished MST Creation.")

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