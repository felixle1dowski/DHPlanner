from ..dhc_creation_pipeline import DHCCreationPipeline
from ..util.logger import Logger


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
        preprocessing_result = self.preprocessing.start()
        Logger().info("Finished Preprocessing.")
        Logger().info("Starting Graph Creation.")
        self.graph_creator.set_preprocessing_result(preprocessing_result)
        graph_creation_result = self.graph_creator.start()
        Logger().info("Finished Graph Creation.")
        Logger().info("Starting MST Creation.")
        self.mst_creator.set_graph_creator_result(graph_creation_result)
        self.mst_creator.start()

