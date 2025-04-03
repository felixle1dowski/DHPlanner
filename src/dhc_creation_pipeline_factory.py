from .multi_step_pipeline.clustering_second_stage import ClusteringSecondStage
from .multi_step_pipeline.graph_creator import GraphCreator
from .multi_step_pipeline.orchestrator_greenfield import OrchestratorGreenfield
from .multi_step_pipeline.orchestrator_adjacent import OrchestratorAdjacent
from .util.config import Config
from .util.not_yet_implemented_exception import NotYetImplementedException
from .multi_step_pipeline.clustering_first_stage import ClusteringFirstStage
from .multi_step_pipeline.clustering_second_stage import ClusteringSecondStage
from .multi_step_pipeline.preprocessing import Preprocessing
from .multi_step_pipeline.shortest_path_graph_creator import ShortestPathGraphCreator
from .multi_step_pipeline.mst_visualizer import MSTVisualizer
from .multi_step_pipeline.multi_step_pipeline import MultiStepPipeline
from .multi_step_pipeline.clustering_second_stage_feasible_solution_creator import ClusteringSecondStageFeasibleSolutionCreator
from .multi_step_pipeline.visualization import Visualization


class DHCCreationPipelineFactory:

    method = None

    def __init__(self):
        self.method = Config().get_method()
        self.installation_strategy = Config().get_installation_strategy()

    def create_pipeline(self):
        """Creates and returns a dhc creation pipeline."""
        if self.method == "one-step":
            raise NotYetImplementedException("one-step solution has not yet been implemented.")
        elif self.method == "multi-step":
            if self.installation_strategy == "street-following":
                return self.create_street_following_pipeline()
            elif self.installation_strategy == "greenfield":
                return self.create_greenfield_pipeline()
            elif self.installation_strategy == "adjacent":
                return self.create_adjacent_pipeline()
            else:
                raise NotYetImplementedException(f"{self.installation_strategy} is not yet implemented.")
        else:
            raise Exception("method is not valid.")

    def create_street_following_pipeline(self):
        preprocessing = Preprocessing()
        clustering_first_stage = ClusteringFirstStage(Config().get_distance_measuring_method())
        feasible_solution_creator = ClusteringSecondStageFeasibleSolutionCreator()
        clustering_second_stage = ClusteringSecondStage()
        graph_creator = GraphCreator()
        mst_creator = ShortestPathGraphCreator()
        mst_visualizer = MSTVisualizer()
        visualization = Visualization()
        return MultiStepPipeline(preprocessing,
                                 clustering_first_stage,
                                 feasible_solution_creator,
                                 clustering_second_stage,
                                 graph_creator,
                                 mst_creator,
                                 mst_visualizer,
                                 visualization)

    def create_greenfield_pipeline(self):
        preprocessing = Preprocessing()
        clustering_first_stage = ClusteringFirstStage(Config().get_distance_measuring_method())
        feasible_solution_creator = ClusteringSecondStageFeasibleSolutionCreator()
        clustering_second_stage = ClusteringSecondStage()
        graph_creator = GraphCreator()
        visualization = Visualization()
        return OrchestratorGreenfield(preprocessing,
                                 clustering_first_stage,
                                 feasible_solution_creator,
                                 clustering_second_stage,
                                 graph_creator,
                                 visualization)

    def create_adjacent_pipeline(self):
        preprocessing = Preprocessing()
        clustering_first_stage = ClusteringFirstStage(Config().get_distance_measuring_method())
        feasible_solution_creator = ClusteringSecondStageFeasibleSolutionCreator()
        clustering_second_stage = ClusteringSecondStage()
        graph_creator = GraphCreator()
        visualization = Visualization()
        return OrchestratorAdjacent(preprocessing,
                                      clustering_first_stage,
                                      feasible_solution_creator,
                                      clustering_second_stage,
                                      graph_creator,
                                      visualization)