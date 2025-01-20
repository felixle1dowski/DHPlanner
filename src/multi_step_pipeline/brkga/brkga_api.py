import random

import numpy as np
from brkga_mp_ipr.enums import Sense

from . import warm_start
from ...util.not_yet_implemented_exception import NotYetImplementedException
from ...util.logger import Logger
from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from .brkga import Brkga

class BrkgaAPI:

    NUM_GENERATIONS = 100 # this is low. See: Praseyeto (2015).
    SEED = 1
    # ToDo: Set in Config!

    MEMBER_LIST_KEY = "member_list"
    CLUSTER_CENTER_KEY = "cluster_center"

    def __init__(self):
        pass

    # ToDo: Validate members and distance matrix. They need to have the same dimensions!
    def do_brkga(self, eliminate_buildings: bool,
                 distance_matrix: np.ndarray,
                 max_capacity: float,
                 demands: {int: float},
                 num_clusters: int,
                 members: list,
                 warm_start: dict,
                 total_distance: float,
                 total_member_list: list):
        if len(members) != len(distance_matrix):
            raise Exception("members list and distance matrix must be same length")
        if eliminate_buildings:
            self.do_brkga_with_elimination()
        else:
            best_fitness, best_chromosome = self.do_brkga_without_elimination(distance_matrix,
                                              max_capacity,
                                              demands,
                                              num_clusters,
                                              members,
                                              warm_start,
                                              total_distance,
                                              total_member_list)
            return best_fitness, best_chromosome
        return {}

    def do_brkga_with_elimination(self):
        raise NotYetImplementedException("Brkga with elimination not yet implemented")

    def do_brkga_without_elimination(self,
                 distance_matrix: np.ndarray,
                 max_capacity: float,
                 demands: {int: float},
                 num_clusters: int,
                 members: list,
                 warm_start: dict,
                 total_distance: float,
                 total_member_list: list):
        instance = ClusteringInstance(distance_matrix, max_capacity, demands, members)
        decoder = ClusteringDecoder(instance, num_clusters)
        initial_solution = self.encode_warm_start(warm_start, total_member_list)
        brkga = Brkga(instance=instance,
                      seed=self.SEED,
                      num_generations=self.NUM_GENERATIONS,
                      sense=Sense.MINIMIZE,
                      decoder=decoder,
                      initial_solution=initial_solution)
        best_fitness, best_chromosome = brkga.do_brkga()
        return best_fitness, best_chromosome

    def encode_warm_start(self, warm_start, total_member_list : list):
        random.seed(self.SEED)
        cluster_ids = []
        members = []
        for cluster_id, inner_dict in warm_start.items():
            cluster_center = inner_dict[self.CLUSTER_CENTER_KEY]
            cluster_ids.append(cluster_center)
            for member in inner_dict[self.MEMBER_LIST_KEY]:
                if member != cluster_center:
                    members.append(member)
        id_solution = cluster_ids + members
        if len(id_solution) != len(total_member_list):
            raise Exception(f"Mismatched length of parameter total_member_list ({len(total_member_list)}) "
                            f"and local variable id_solution ({len(id_solution)})")
        keys = sorted([random.random() for _ in range(len(id_solution))])
        initial_chromosome = [0] * len(id_solution)
        for i in range(len(id_solution)):
            member_index = total_member_list.index(id_solution[i])
            initial_chromosome[member_index] = keys[i]
        Logger().debug(f"Initial Chromosome created: {initial_chromosome}")
        return initial_chromosome