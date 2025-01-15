from turtle import pd

import numpy as np


class ClusteringInstance:
    """HAS to implement read only functions and fields."""

    IS_CENTER_FIELD = "is_center"
    CLUSTER_ID_FIELD = "cluster_id"

    # ToDo: Change Constructor api to hand over dataframe instead of distance_matrix and members list.

    def __init__(self, distance_matrix: np.ndarray, max_capacity: float, demands: {str : float}, members: list):
        self.distance_matrix = distance_matrix
        self.max_capacity = max_capacity
        self.demands = demands
        self.members = members

    def __setattr__(self, key, value):
        raise AttributeError(f"ClusteringInstance.__setattr__({key}) attempted. Permitted after instantiation!")

    def get_distance(self, point1, point2):
        return self.distance_matrix[point1, point2]

    def get_sorted_distances_to_multiple_points(self, from_point: int, to_group_of_points: list[int]):
        unsorted_result = []
        for point in to_group_of_points:
            point_distance_tuple = (point, self.get_distance(from_point, point))
            unsorted_result.append(point_distance_tuple)
        sorted_result = sorted(unsorted_result, key=lambda x: x[1])
        return sorted_result

    def get_point_demand(self, point: str) -> float:
        return self.demands[point]

    def get_number_of_nodes(self):
        return len(self.demands)

    def translate_cluster_membership_table(self,
                                           cluster_membership_table: np.ndarray,
                                           cluster_centers,
                                           cluster_members) -> {str: {}}:
        result_dict = {}
        rows, cols = np.where(cluster_membership_table == 1)
        combinations = list(zip(rows, cols))
        for combination in combinations:
            member = cluster_members[combination[0]]
            center = cluster_centers[combination[1]]
            if member != center:
                result_dict[self.members[member]] = {
                    self.IS_CENTER_FIELD : False,
                    self.CLUSTER_ID_FIELD : self.members[center],
                }
            else:
                result_dict[self.members[member]] = {
                    self.IS_CENTER_FIELD : True,
                    self.CLUSTER_ID_FIELD : self.members[center],
                }
        return result_dict