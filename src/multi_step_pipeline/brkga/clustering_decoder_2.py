from collections import defaultdict

from brkga_mp_ipr.types import BaseChromosome
from .clustering_instance import ClusteringInstance
from .fitness_function import FitnessFunction


class ClusteringDecoder2:

    MEMBERS_TO_FLAG_INDEX = "-1"

    def __init__(self, instance: ClusteringInstance, num_clusters: int, fitness_function: FitnessFunction):
        self.instance = instance
        self.num_clusters = num_clusters
        self.fitness_function = fitness_function

    def decode(self, chromosome: BaseChromosome) -> float:
        permutation = sorted(
            (key, index) for index, key in enumerate(chromosome)
        )
        all_indices = [index for key, index in permutation]
        arranged_ids = self.instance.get_decoded_list_of_ids(all_indices)
        cluster_capacities = self.init_cluster_capacities(arranged_ids)
        cluster_dict = self.create_cluster_membership_dict(arranged_ids, cluster_capacities)
        fitness = self.evaluate_solution(cluster_dict)
        return fitness

    def init_cluster_capacities(self, permutation: list) -> {str: float}:
        return_dict = {}
        cluster_centers = permutation[:self.num_clusters]
        for cluster_center in cluster_centers:
            return_dict[cluster_center] = float(self.instance.max_capacity)
        return return_dict

    def create_cluster_membership_dict(self, permutation: list, cluster_capacities: {int:float}) -> {str: list[str]}:
        cluster_centers = permutation[:self.num_clusters]
        potential_members = permutation[self.num_clusters:]
        result_dict = defaultdict(list)
        for potential_member in potential_members:
            distances_to_center = self.instance.get_sorted_distances_to_multiple_points(potential_member, cluster_centers)
            for cluster_center, distance in distances_to_center:
                if self.potential_member_fits_into_cluster(cluster_capacities, cluster_center, potential_member):
                    result_dict[cluster_center].append(potential_member)
                    cluster_capacities[cluster_center] -= self.instance.get_point_demand(potential_member)
                    break
            result_dict[self.MEMBERS_TO_FLAG_INDEX].append(potential_member)
        return result_dict

    def potential_member_fits_into_cluster(self, cluster_capacities : {int:float},
                                           cluster_center : str,
                                           potential_member: str):
        remaining_capacity = float(cluster_capacities[cluster_center])
        potential_remaining_capacity = remaining_capacity - self.instance.get_point_demand(potential_member)
        return potential_remaining_capacity >= 0

    def evaluate_solution(self, cluster_dict) -> float:
        fitness = self.fitness_function.compute_fitness_for_all(cluster_dict)
        return fitness
