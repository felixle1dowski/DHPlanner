from .dhc_creation_pipeline import DHCCreationPipeline
from .preprocessing import Preprocessing
from .graph_creator import GraphCreator
from .mst_creator import MSTCreator
from .mst_visualizer import MSTVisualizer
from .logger import Logger


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
        # Logger().info("Preprocessing started.")
        # preprocessing_result = preprocessing.get_result()
        # Logger().info("Preprocessing finished.")
        # Logger().info("Graph creation started.")
        # graph_creator_result = graph_creator.get_result(preprocessing_result)
        # Logger().info("Graph creation finished.")
        # Logger().info("MST creation started.")
        # mst_creator_result = mst_creator.get_result(graph_creator_result)
        # Logger().info("MST creation finished.")
        # Logger().info("MST visualization started.")
        # mst_visualizer.visualize(mst_creator_result)
        # Logger().info("MST visualization finished.")
        Logger().info("Starting Preprocessing.")
        self.preprocessing.start()