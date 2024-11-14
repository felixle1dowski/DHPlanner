from .config import Config
from .not_yet_implemented_exception import NotYetImplementedException
from .dhc_creation_pipeline import DHCCreationPipeline
from .preprocessing import Preprocessing
from .graph_creator import GraphCreator
from .mst_creator import MSTCreator
from .mst_visualizer import MSTVisualizer
from .multi_step_pipeline import MultiStepPipeline


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