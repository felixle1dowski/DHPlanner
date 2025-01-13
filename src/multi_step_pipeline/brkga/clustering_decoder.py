import numpy as np
from brkga_mp_ipr.types import BaseChromosome
from .clustering_chromosome import ClusteringChromosome
from .clustering_instance import ClusteringInstance

class ClusteringDecoder():
    """First Version of the Decoder of the BRKGA method. Note that thus far, this only works with examples, in which
    the clusters have proper size and DO NOT violate the user-set minimum used capacity of the heating source!"""

    CONSTRAINT_BROKEN_PENALTY = 10_000_000.0

    def __init__(self, instance: ClusteringInstance, num_clusters: int):
        self.instance = instance
        self.num_clusters = num_clusters

    def decode(self, chromosome: BaseChromosome, rewrite: bool) -> float:
        permutation = sorted(
            (key, index) for index, key in enumerate(chromosome)
        )
        cluster_capacities = self.init_cluster_capacities(permutation)
        clusters = self.create_cluster_membership_table(permutation, cluster_capacities)
        fitness = self.evaluate_solution(clusters, cluster_capacities)
        return fitness

    def create_cluster_membership_table(self, permutation: list, cluster_capacities: {int:float}) \
            -> (int, int, np.ndarray):
        """Returns cluster members (rows), cluster centers (columns) and a membership table.
        Membership table will display 1 if cluster point is member of cluster, 0 otherwise."""
        cluster_members = permutation[self.num_clusters:]
        cluster_centers = permutation[:self.num_clusters]
        cluster_membership_table_init = np.zeros(shape=(len(cluster_members), len(cluster_centers)), dtype=int)
        cluster_membership_table = np.ndarray(cluster_membership_table_init, dtype=int)
        for cluster_member in cluster_members:
            distances_to_centers = self.instance.get_sorted_distances_to_multiple_points(cluster_member, cluster_centers)
            for cluster_center, distance in distances_to_centers:
                if self.cluster_member_fits_into_cluster(cluster_capacities, cluster_center, cluster_member):
                    cluster_membership_table[cluster_member][cluster_center] = 1
                    cluster_capacities[cluster_center] -= self.instance.get_point_demand(cluster_member)
                    break
        return cluster_members, cluster_centers, cluster_membership_table

    def init_cluster_capacities(self, permutation: list) -> {int: float}:
        return_dict = {}
        cluster_centers = permutation[:self.num_clusters]
        for cluster_center in cluster_centers:
            return_dict[cluster_center] = self.instance.max_capacity

    def cluster_member_fits_into_cluster(self,
                                         remaining_capacities : {int: float},
                                         cluster : int,
                                         potential_member : int) -> bool:
        remaining_capacity = remaining_capacities.get(cluster)
        potential_remaining_capacity = remaining_capacity - self.instance.get_point_demand(potential_member)
        return potential_remaining_capacity >= 0

    def evaluate_solution(self, clusters: np.ndarray, cluster_capacities: {int: float}) -> float:
        constraint_part = self.evaluate_constraints(clusters, cluster_capacities)
        distances_part = self.evaluate_distances(clusters)
        return constraint_part + distances_part

    def evaluate_constraints(self, clusters, cluster_capacities: {int: float}) -> float:
        capacity_constraint_part = self.evaluate_capacity_constraint(cluster_capacities)
        return capacity_constraint_part

    def evaluate_capacity_constraint(self, cluster_capacities: {int: float}) -> float:
        for cluster_center, capacity in cluster_capacities.items():
            if capacity < 0:
                return self.CONSTRAINT_BROKEN_PENALTY
        return 0.0

    def evaluate_distances(self, clusters: np.ndarray) -> float:
        rows, cols = np.where(clusters == 1)
        combinations = list(zip(rows, cols))
        distance_sum = 0
        for entry in combinations:
            distance_sum += self.instance.get_distance(entry[0], entry[1])
        return distance_sum

