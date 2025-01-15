import numpy as np
from brkga_mp_ipr.enums import Sense

from ...util.not_yet_implemented_exception import NotYetImplementedException
from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from .brkga import Brkga

class BrkgaAPI:

    NUM_GENERATIONS = 100 # this is low. See: Praseyeto (2015).
    # ToDo: Set in Config!

    def __init__(self):
        pass

    # ToDo: Validate members and distance matrix. They need to have the same dimensions!
    def do_brkga(self, eliminate_buildings: bool,
                 distance_matrix: np.ndarray,
                 max_capacity: float,
                 demands: {int: float},
                 num_clusters: int,
                 members: list):
        if len(members) != len(distance_matrix):
            raise Exception("members list and distance matrix must be same length")
        if eliminate_buildings:
            self.do_brkga_with_elimination()
        else:
            self.do_brkga_without_elimination(distance_matrix,
                                              max_capacity,
                                              demands,
                                              num_clusters,
                                              members)
        return {}

    def do_brkga_with_elimination(self):
        raise NotYetImplementedException("Brkga with elimination not yet implemented")

    def do_brkga_without_elimination(self,
                 distance_matrix: np.ndarray,
                 max_capacity: float,
                 demands: {int: float},
                 num_clusters: int,
                 members: list):
        instance = ClusteringInstance(distance_matrix, max_capacity, demands, members)
        decoder = ClusteringDecoder(instance, num_clusters)
        brkga = Brkga(instance=instance,
                      seed=1,
                      num_generations=self.NUM_GENERATIONS,
                      sense=Sense.MINIMIZE,
                      decoder=decoder)
        brkga.do_brkga()