from turtle import pd

import numpy as np
from networkx import nx


class ClusteringInstance:
    """HAS to implement read only functions and fields."""

    IS_CENTER_FIELD = "is_center"
    CLUSTER_ID_FIELD = "cluster_id"
    PIVOT_STRING_SINGLE = "pivot_members_end"

    # ToDo: Change Constructor api to hand over dataframe instead of distance_matrix and members list.

    def __init__(self, graph: nx.Graph, max_capacity: float, demands: {str: float}, members: list,
                 id_to_node_translation_dict: dict, pivot_element="none"):
        self.graph = graph
        self.max_capacity = max_capacity
        self.demands = demands
        self.members = members
        self.id_to_node_translation_dict = id_to_node_translation_dict
        self.pivot_element = pivot_element

    # ToDo: Delete?
    def get_distance(self, id1, id2):
        distance = self.graph[self.id_to_node_translation_dict[id1]][self.id_to_node_translation_dict[id2]]['weight']
        return distance

    def get_subgraph(self, members: list):
        node_list = [self.id_to_node_translation_dict[member] for member in members]
        subgraph = self.graph.subgraph(node_list)
        return subgraph

    def get_sorted_distances_to_multiple_points(self, from_point: str, to_group_of_points: list[str]):
        unsorted_result = []
        for point in to_group_of_points:
            point_distance_tuple = (point, self.get_distance(from_point, point))
            unsorted_result.append(point_distance_tuple)
        sorted_result = sorted(unsorted_result, key=lambda x: x[1])
        return sorted_result

    def get_point_demand(self, point: str) -> float:
        if not point.startswith("pivot"):
            return float(self.demands[point])

    def get_number_of_nodes(self):
        number_of_nodes = len(self.demands)
        if self.pivot_element == "single":
            number_of_nodes += 1
        elif self.pivot_element == "double":
            number_of_nodes += 2
        return number_of_nodes

    # def translate_cluster_membership_table(self,
    #                                        cluster_membership_table: np.ndarray,
    #                                        cluster_centers,
    #                                        cluster_members) -> {str: {}}:
    #     result_dict = {}
    #     rows, cols = np.where(cluster_membership_table == 1)
    #     combinations = list(zip(rows, cols))
    #     for combination in combinations:
    #         member = cluster_members[combination[0]]
    #         center = cluster_centers[combination[1]]
    #         if member != center:
    #             result_dict[self.members[member]] = {
    #                 self.IS_CENTER_FIELD: False,
    #                 self.CLUSTER_ID_FIELD: self.members[center],
    #             }
    #         else:
    #             result_dict[self.members[member]] = {
    #                 self.IS_CENTER_FIELD: True,
    #                 self.CLUSTER_ID_FIELD: self.members[center],
    #             }
    #     return result_dict

    def get_decoded_list_of_ids(self, indexes: list[int]) -> list[str]:
        return_list = []
        for index in indexes:
            return_list.append(self.members[index])
        return return_list

    def get_point_demands(self, id_subset):
        demands = sum([self.get_point_demand(cluster_member) for cluster_member in id_subset])
        return demands