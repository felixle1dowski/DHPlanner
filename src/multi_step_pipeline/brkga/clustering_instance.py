import numpy as np


class ClusteringInstance:
    """HAS to implement read only functions and fields."""
    def __init__(self, distance_matrix: np.ndarray, max_capacity: float, demands: {int : float}):
        self.distance_matrix = distance_matrix
        self.max_capacity = max_capacity
        self.demands = demands

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

    def get_point_demand(self, point: int) -> float:
        return self.demands[point]
