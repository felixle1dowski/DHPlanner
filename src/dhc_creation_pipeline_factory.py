from .util.config import Config
from .util.not_yet_implemented_exception import NotYetImplementedException
from .multi_step_pipeline.preprocessing import Preprocessing
from .multi_step_pipeline.graph_creator import GraphCreator
from .multi_step_pipeline.mst_creator import MSTCreator
from .multi_step_pipeline.mst_visualizer import MSTVisualizer
from .multi_step_pipeline.multi_step_pipeline import MultiStepPipeline


class DHCCreationPipelineFactory:

    method = None

    def __init__(self):
        self.method = Config().get_method()

    def create_pipeline(self):
        """Creates and returns a dhc creation pipeline."""
        if self.method == "one-step":
            raise NotYetImplementedException("one-step solution has not yet been implemented.")
        elif self.method == "multi-step":
            preprocessing = Preprocessing()
            graph_creator = GraphCreator()
            mst_creator = MSTCreator()
            mst_visualizer = MSTVisualizer()
            return MultiStepPipeline(preprocessing, graph_creator, mst_creator, mst_visualizer)
        else:
            raise Exception("method is not valid.")