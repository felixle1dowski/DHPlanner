from collections import defaultdict

from brkga_mp_ipr.types import BaseChromosome
from .clustering_instance import ClusteringInstance
from .fitness_function import FitnessFunction
from ...util.not_yet_implemented_exception import NotYetImplementedException


class ClusteringDecoder:
    MEMBERS_TO_FLAG_INDEX = "-1"
    PIVOT_SINGLE_NAME = "pivot_members_end"
    CONSTRAINT_BROKEN_PENALTY = -1000

    def __init__(self, instance: ClusteringInstance, num_clusters: int, fitness_function: FitnessFunction,
                 pivot_element="none"):
        if pivot_element not in ["none", "single", "double"]:
            raise ValueError(f"pivot_element must be 'none' or 'single' or 'double' but is {pivot_element}")
        self.pivot_element = pivot_element
        self.instance = instance
        self.num_clusters = num_clusters
        self.fitness_function = fitness_function

    def decode(self, chromosome: BaseChromosome, rewrite: bool) -> float:
        permutation = sorted(
            (key, index) for index, key in enumerate(chromosome)
        )
        all_indices = [index for key, index in permutation]
        arranged_ids = self.instance.get_decoded_list_of_ids(all_indices)
        cluster_capacities = self.init_cluster_capacities(arranged_ids)
        if cluster_capacities is -1:
            return self.CONSTRAINT_BROKEN_PENALTY
        cluster_dict = self.create_cluster_membership_dict(arranged_ids, cluster_capacities)
        fitness = self.evaluate_solution(cluster_dict)
        return fitness

    def decode_single_use(self, chromosome: BaseChromosome):
        permutation = sorted(
            (key, index) for index, key in enumerate(chromosome)
        )
        all_indices = [index for key, index in permutation]
        arranged_ids = self.instance.get_decoded_list_of_ids(all_indices)
        cluster_capacities = self.init_cluster_capacities(arranged_ids)
        cluster_dict = self.create_cluster_membership_dict(arranged_ids, cluster_capacities)
        fitness = self.evaluate_solution(cluster_dict)
        return fitness, cluster_dict

    def init_cluster_capacities(self, permutation: list) -> {str: float}:
        return_dict = {}
        cluster_centers = permutation[:self.num_clusters]
        if self.pivot_element == "single":
            if self.PIVOT_SINGLE_NAME in cluster_centers:
                return -1
        for cluster_center in cluster_centers:
            return_dict[cluster_center] = float(self.instance.max_capacity)
        return return_dict

    def create_cluster_membership_dict(self, permutation: list, cluster_capacities: {int: float}) -> {str: list[str]}:
        if self.pivot_element == "none":
            cluster_membership_dict = self.create_cluster_membership_dict_no_pivot(permutation, cluster_capacities)
            return cluster_membership_dict
        elif self.pivot_element == "single":
            cluster_membership_dict = self.create_cluster_membership_dict_single_pivot(permutation, cluster_capacities)
            return cluster_membership_dict
        else:
            raise NotYetImplementedException(f"Other pivot strategies such as chosen {self.pivot_element} are not implemented.")

    def create_cluster_membership_dict_no_pivot(self, permutation: list, cluster_capacities: {int: float}) -> {str: list[str]}:
        cluster_centers = permutation[:self.num_clusters]
        potential_members = permutation[self.num_clusters:]
        result_dict = defaultdict(list)
        for potential_member in potential_members:
            result_dict = self.create_cluster_membership_dict_inner_function(result_dict, cluster_capacities,
                                                                             potential_member, cluster_centers)
        return result_dict

    def create_cluster_membership_dict_single_pivot(self, permutation: list, cluster_capacities: {int: float}) -> {
        str: list}:
        cluster_centers = permutation[:self.num_clusters]
        potential_members = permutation[self.num_clusters:]
        result_dict = defaultdict(list)
        break_index = 0
        for potential_member in potential_members:
            if potential_member == self.PIVOT_SINGLE_NAME:
                break
            result_dict = self.create_cluster_membership_dict_inner_function(result_dict, cluster_capacities,
                                                                             potential_member, cluster_centers)
            break_index += 1
        members_to_exclude = permutation[break_index:]
        for member in members_to_exclude:
            result_dict[self.MEMBERS_TO_FLAG_INDEX].append(member)
        return result_dict

    def create_cluster_membership_dict_inner_function(self, cluster_dict, cluster_capacities, potential_member,
                                                      cluster_centers):
        distances_to_center = self.instance.get_sorted_distances_to_multiple_points(
            potential_member, cluster_centers)
        potential_member_assigned = False
        for cluster_center, distance in distances_to_center:
            if self.potential_member_fits_into_cluster(cluster_capacities, cluster_center, potential_member):
                cluster_dict[cluster_center].append(potential_member)
                cluster_capacities[cluster_center] -= self.instance.get_point_demand(potential_member)
                potential_member_assigned = True
                break
        if not potential_member_assigned:
            cluster_dict[self.MEMBERS_TO_FLAG_INDEX].append(potential_member)
        return cluster_dict

    def potential_member_fits_into_cluster(self, cluster_capacities: {int: float},
                                           cluster_center: str,
                                           potential_member: str):
        remaining_capacity = float(cluster_capacities[cluster_center])
        potential_remaining_capacity = remaining_capacity - self.instance.get_point_demand(potential_member)
        return potential_remaining_capacity >= 0

    def evaluate_solution(self, cluster_dict) -> float:
        fitness = self.fitness_function.compute_fitness_for_all(cluster_dict)
        return fitness
