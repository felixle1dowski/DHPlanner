from abc import ABC, abstractmethod

class IClusteringSecondStageFeasibleSolutionCreator(ABC):
    @abstractmethod
    def make_solution_feasible(self, cluster_dict: dict, cluster_center_dict: dict, info_layer):
        pass