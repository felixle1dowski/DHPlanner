import math
from collections import defaultdict

from brkga_mp_ipr.types import BaseChromosome
from .clustering_instance import ClusteringInstance
from .fitness_function import FitnessFunction
from ...util.not_yet_implemented_exception import NotYetImplementedException
from ...util.logger import Logger
from .minded_heating_sources.minded_heating_sources import MindedHeatingSources


class ClusteringDecoder:
    MEMBERS_TO_FLAG_INDEX = "-1"
    PIVOT_SINGLE_NAME = "pivot_members_end"
    CONSTRAINT_BROKEN_PENALTY = 1_000_000_000
    PIVOT_PREFIX = "pivot"

    def __init__(self, instance: ClusteringInstance, num_clusters: int, fitness_function: FitnessFunction,
                 pivot_element="none"):
        if pivot_element not in ["none", "single", "double", "multiple"]:
            raise ValueError(f"pivot_element must be 'none' or 'single' or 'double' or 'multiple' but is {pivot_element}")
        self.pivot_element = pivot_element
        self.instance = instance
        self.num_clusters = num_clusters
        self.fitness_function = fitness_function
        self.number_of_heating_sources_to_consider = 1

    def decode(self, chromosome: BaseChromosome, rewrite: bool) -> float:
        arranged_ids = self.decode_shared_part(chromosome)
        if self.pivot_element in ("none", "single", "double"):
            fitness = self.decode_default(arranged_ids)
        elif self.pivot_element == "multiple":
            fitness = self.decode_multiple_heat_sources(arranged_ids)
        else:
            raise Exception("invalid pivot_element")
        return fitness

    def decode_default(self, arranged_ids):
        cluster_capacities = self.init_cluster_capacities_default(arranged_ids)
        if cluster_capacities is -1:
            return self.CONSTRAINT_BROKEN_PENALTY
        cluster_dict = self.create_cluster_membership_dict(arranged_ids, cluster_capacities)
        fitness = self.evaluate_solution(cluster_dict)
        return fitness

    def decode_multiple_heat_sources(self, arranged_ids):
        groups_per_heating_source = self.divide_ids_into_groups_per_heating_source(arranged_ids)
        needed_heating_sources = self.calculate_needed_heating_sources_first_guess(groups_per_heating_source)
        merged_list = self.merge_heating_sources_data_types(groups_per_heating_source, needed_heating_sources)
        concrete_groups = self.divide_members_into_groups(merged_list)
        return 1

    def divide_members_into_groups(self, merged_list):
        for entry in merged_list:
            members = entry["members"]
            cluster_centers = members[0:entry["needed_heating_sources"]]
            cluster_members = members[entry["needed_heating_sources"]:]
            capacities = self.init_cluster_capacities_multiple(cluster_centers, merged_list["heating_source"])
            potential_member_assigned = False
            for cluster_member in cluster_members:
                distances = self.instance.get_sorted_distances_to_multiple_points(cluster_member, cluster_centers)


    def merge_heating_sources_data_types(self, groups_per_heating_source, needed_heating_sources):
        merged_list = []
        index = 0
        for (heating_source, members) in groups_per_heating_source:
            dict_entry = {
                "heating_source": heating_source,
                "needed_heating_sources": needed_heating_sources[index],
                "members": members
            }
            index += 1
            merged_list.append(dict_entry)
        return merged_list

    def divide_ids_into_groups_per_heating_source(self, arranged_ids):
        number_of_pivots = self.instance.get_number_of_pivots()
        members_per_heating_source = {}
        start_element_index = 0
        for heating_source_index in range(number_of_pivots):
            for element_index in range(len(arranged_ids) - start_element_index):
                group_members = []
                if not arranged_ids[element_index].startswith(self.PIVOT_PREFIX):
                    group_members.append(arranged_ids[element_index])
                else:
                    start_element_index = element_index
                    members_per_heating_source[self.instance.minded_heating_sources.get_heating_source_by_index(heating_source_index)] = group_members
                    break
        Logger().debug(f"ids were grouped by heating source: {members_per_heating_source}")
        return members_per_heating_source

    def calculate_needed_heating_sources_first_guess(self, groups_per_heating_source):
        needed_heating_sources = []
        for (heating_source, members) in groups_per_heating_source:
            cumulated_demands = sum([self.instance.get_point_demands(member) for member in members])
            # always rounding up, because small heating sources are also possible.
            amount_of_heating_sources_needed = math.ceil(cumulated_demands / heating_source.capacity_kw)
            needed_heating_sources.append(amount_of_heating_sources_needed)
        return needed_heating_sources


    def decode_single_use(self, chromosome: BaseChromosome):
        cluster_dict = self.decode_chromosome(chromosome)
        fitness = self.evaluate_solution(cluster_dict)
        return fitness, cluster_dict

    def decode_end_result(self, chromosome: BaseChromosome):
        cluster_dict = self.decode_chromosome(chromosome)
        if cluster_dict == self.CONSTRAINT_BROKEN_PENALTY:
            return self.CONSTRAINT_BROKEN_PENALTY
        end_result = self.fitness_function.compute_fitness_for_all_result(cluster_dict)
        return end_result

    def decode_chromosome(self, chromosome: BaseChromosome):
        arranged_ids = self.decode_shared_part(chromosome)
        # ToDo: What does this mean in the case of multiple heating sources?
        cluster_capacities = self.init_cluster_capacities_default(arranged_ids)
        if cluster_capacities is -1:
            return self.CONSTRAINT_BROKEN_PENALTY
        cluster_dict = self.create_cluster_membership_dict(arranged_ids, cluster_capacities)
        return cluster_dict

    def decode_shared_part(self, chromosome: BaseChromosome):
        permutation = sorted(
            (key, index) for index, key in enumerate(chromosome)
        )
        all_indices = [index for key, index in permutation]
        arranged_ids = self.instance.get_decoded_list_of_ids(all_indices)
        return arranged_ids

    def init_cluster_capacities_default(self, permutation: list) -> {str: float}:
        return_dict = {}
        cluster_centers = permutation[:self.num_clusters]
        if self.pivot_element == "single":
            if self.PIVOT_SINGLE_NAME in cluster_centers:
                return -1
        for cluster_center in cluster_centers:
            return_dict[cluster_center] = float(self.instance.max_capacity) - float(self.instance.get_point_demand(cluster_center))
        return return_dict

    def init_cluster_capacities_multiple(self, cluster_centers, heating_source):
        capacities_dict = {}
        for cluster_center in cluster_centers:
            capacities_dict[cluster_center] = heating_source.capacity_kw
        return capacities_dict

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
        result_dict = defaultdict(list, {center: [] for center in cluster_centers})
        for potential_member in potential_members:
            result_dict = self.create_cluster_membership_dict_inner_function(result_dict, cluster_capacities,
                                                                             potential_member, cluster_centers)
        return result_dict

    def create_cluster_membership_dict_single_pivot(self, permutation: list, cluster_capacities: {int: float}) -> {
        str: list}:
        cluster_centers = permutation[:self.num_clusters]
        potential_members = permutation[self.num_clusters:]
        result_dict = defaultdict(list, {center: [] for center in cluster_centers})
        break_index = self.num_clusters
        for potential_member in potential_members:
            if potential_member == self.PIVOT_SINGLE_NAME:
                break
            result_dict = self.create_cluster_membership_dict_inner_function(result_dict, cluster_capacities,
                                                                             potential_member, cluster_centers)
            break_index += 1
        members_to_exclude = permutation[break_index:]
        # Logger().debug(f"break index: {break_index}, members_to_exclude: {members_to_exclude}")
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
                # Logger().debug(f"cluster capacity of {cluster_center} was: {cluster_capacities[cluster_center]}")
                cluster_capacities[cluster_center] -= self.instance.get_point_demand(potential_member)
                # Logger().debug(f"cluster capacity of {cluster_center} is: {cluster_capacities[cluster_center]}")
                potential_member_assigned = True
                break
        if not potential_member_assigned:
            # Logger().debug(f"{potential_member} had to be sorted out!")
            cluster_dict[self.MEMBERS_TO_FLAG_INDEX].append(potential_member)
        return cluster_dict

    def potential_member_fits_into_cluster(self, cluster_capacities: {int: float},
                                           cluster_center: str,
                                           potential_member: str):
        remaining_capacity = float(cluster_capacities[cluster_center])
        potential_remaining_capacity = remaining_capacity - self.instance.get_point_demand(potential_member)
        # Logger().debug(f'calculating remaining capacity for {potential_member}: {remaining_capacity} - {self.instance.get_point_demand(potential_member)} = {potential_remaining_capacity}'
        #               f'enough capacity? {potential_remaining_capacity >= 0}')
        return potential_remaining_capacity >= 0

    def evaluate_solution(self, cluster_dict) -> float:
        fitness = self.fitness_function.compute_fitness_for_all(cluster_dict)
        return fitness



