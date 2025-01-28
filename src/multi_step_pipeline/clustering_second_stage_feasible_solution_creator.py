from .I_clustering_second_stage_feasible_solution_creator import IClusteringSecondStageFeasibleSolutionCreator
from scipy.spatial.distance import euclidean
from ..util.dhp_utility import DhpUtility
from ..util.logger import Logger
from ..util.config import Config
from ..util.function_timer import FunctionTimer


class ClusteringSecondStageFeasibleSolutionCreator(IClusteringSecondStageFeasibleSolutionCreator):
    function_timer = FunctionTimer()

    # ToDo: Change all variable names containing member to member_id (if suitable)

    # ToDo: Put in Config
    UNIQUE_ID_FIELD = "osm_id"

    MEMBER_LIST_KEY = "member_list"
    NON_MEMBER_KEY = "non_member_list"
    # ToDo: This has to be put into a config anyway, but sometimes QGIS struggles mightily with underscores...
    CURRENT_CAPACITY_KEY = "current_capacity"
    TOTAL_SUM_OF_DISTANCES_KEY = "total_sum_of_distances"
    SUM_OF_DISTANCES_PER_CLUSTER_KEY = "sum_of_distances"
    CLUSTER_CENTER_BUILDING_KEY = "cluster_center"
    CLUSTERS_KEY = "clusters"

    DEMAND_FIELD = "peak_demand"

    def __init__(self):
        pass

    def make_solution_feasible(self, cluster_dict: dict, cluster_center_dict: dict, info_layer):
        # ToDo: Check for validity (do dicts have the right fields?)
        # ToDo: I have to do the cluster_center_dict thingy!!
        distance_ranking_dict = self.create_distance_ranking_dict(cluster_dict, cluster_center_dict, info_layer)
        dict_with_capacity = self.add_capacity_field_to_cluster_dict(distance_ranking_dict, info_layer)
        dict_with_non_member_list = self.add_non_member_list_to_cluster_dict(distance_ranking_dict)
        feasible_solution = self.swap_cluster_membership_until_solution_feasible(dict_with_capacity,
                                                                                 cluster_center_dict,
                                                                                 info_layer)
        solution_with_cluster_centers = self.add_cluster_center_to_cluster_dict(feasible_solution,
                                                                                cluster_center_dict,
                                                                                info_layer)
        solution_with_distances = self.add_sum_of_distances_field_per_cluster(solution_with_cluster_centers, info_layer)
        solution_with_total_distances = self.add_total_sum_of_distances_field(solution_with_distances)
        return solution_with_total_distances

    def create_distance_ranking_dict(self, cluster_dict, cluster_center_dict, info_layer):
        distance_ranking_dict = {}
        for (cluster_id, member_list) in cluster_dict.items():
            sorted_list = self.rank_member_list_by_distance_from_center(member_list,
                                                                        cluster_center_dict[cluster_id],
                                                                        info_layer)
            # ToDo: cluster_center_dict[cluster_id] has to be (x, y) tuple!
            distance_ranking_dict[cluster_id] = sorted_list
        Logger().debug(f"Distance Ranking in Cluster dict has been successful.\n{distance_ranking_dict}")
        return distance_ranking_dict

    def rank_member_list_by_distance_from_center(self, member_list, cluster_center_xy, info_layer):
        distances_ranking = []
        for member in member_list:
            member_feature = DhpUtility.get_feature_by_id_field(info_layer, self.UNIQUE_ID_FIELD, member)
            member_geometry = member_feature.geometry()
            member_xy = (member_geometry.asPoint().x(), member_geometry.asPoint().y())
            distances_ranking.append((member, euclidean(member_xy, cluster_center_xy)))
        sorted_by_distance = [id_ for id_, distance in sorted(distances_ranking,
                                                              key=lambda x: x[1],
                                                              reverse=True)]
        return sorted_by_distance

    def add_capacity_field_to_cluster_dict(self, cluster_dict, info_layer):
        dict_with_capacity = {}
        for (cluster_id, member_list) in cluster_dict.items():
            dict_with_capacity[cluster_id] = {
                self.MEMBER_LIST_KEY: member_list,
                self.CURRENT_CAPACITY_KEY: self.calculate_current_capacity(info_layer, member_list)
            }
        Logger().debug(f"capacity added to cluster_dict. Current dict:\n{dict_with_capacity}")
        return dict_with_capacity

    def calculate_current_capacity(self, info_layer, member_list):
        capacity = float(Config().get_heat_capacity())
        for member in member_list:
            demand = DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                   self.UNIQUE_ID_FIELD,
                                                                   member,
                                                                   self.DEMAND_FIELD)
            capacity -= float(demand)
        return capacity

    @function_timer.timed_function
    def swap_cluster_membership_until_solution_feasible(self, cluster_dict, cluster_center_dict, info_layer):
        # ToDo: Validate that dict has all the required fields!
        for (cluster_id, inner_dict) in cluster_dict.items():
            if inner_dict[self.CURRENT_CAPACITY_KEY] < 0:
                Logger().debug(f"Capacity of Cluster {cluster_id} is less than 0."
                               f"Trying to swap cluster memberships until capacity is >= 0.")
                for candidate in inner_dict[self.MEMBER_LIST_KEY]:
                    cluster_centers_ranked = (
                        self.create_distance_ranking_member_to_cluster_center(candidate,
                                                                              cluster_center_dict,
                                                                              info_layer))
                    for cluster_center_id, distance in cluster_centers_ranked:
                        if cluster_dict[cluster_center_id][self.CURRENT_CAPACITY_KEY] > float(
                                DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                              self.UNIQUE_ID_FIELD,
                                                                              candidate,
                                                                              self.DEMAND_FIELD)):
                            self.swap_cluster_membership(cluster_dict, candidate, cluster_id, cluster_center_id,
                                                         info_layer)
                            break
                    if inner_dict[self.CURRENT_CAPACITY_KEY] >= 0:
                        break
                    self.flag_as_non_member(cluster_dict, cluster_id, candidate)
        return cluster_dict

    def swap_cluster_membership(self, cluster_dict, member,
                                from_cluster, to_cluster, info_layer):
        member_demand = float(DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                            self.UNIQUE_ID_FIELD,
                                                                            member,
                                                                            self.DEMAND_FIELD))
        if member in cluster_dict[from_cluster][self.MEMBER_LIST_KEY]:
            cluster_dict[from_cluster][self.MEMBER_LIST_KEY].remove(member)
            cluster_dict[from_cluster][self.CURRENT_CAPACITY_KEY] += member_demand
        else:
            raise Exception(f"Candidate {member} is not in cluster {from_cluster}")

        cluster_dict[to_cluster][self.MEMBER_LIST_KEY].append(member)
        cluster_dict[to_cluster][self.CURRENT_CAPACITY_KEY] -= member_demand
        Logger().debug(f"Swapped {member} from cluster {from_cluster} to cluster {to_cluster}")

    def create_distance_ranking_member_to_cluster_center(self, member, cluster_center_dict, info_layer):
        ranking_list = []
        member_xy = DhpUtility.get_xy_by_id_field(info_layer,
                                                  self.UNIQUE_ID_FIELD,
                                                  member)
        for cluster_id, cluster_xy in cluster_center_dict.items():
            distance = euclidean(cluster_xy, member_xy)
            ranking_list.append((cluster_id, distance))
        sorted_by_distance = [id_ for id_ in sorted(ranking_list,
                                                    key=lambda x: x[1],
                                                    reverse=False)]
        return sorted_by_distance

    def add_cluster_center_to_cluster_dict(self, cluster_dict, cluster_center_dict, info_layer):
        # ToDo: Wouldn't it make more sense to do this BEFORE applying the swap_cluster_membership?
        for cluster_id, inner_dict in cluster_dict.items():
            closest_building_id = -1
            closest_distance = float('inf')
            cluster_center_xy = cluster_center_dict[cluster_id]
            for member in inner_dict[self.MEMBER_LIST_KEY]:
                member_xy = DhpUtility.get_xy_by_id_field(info_layer,
                                                          self.UNIQUE_ID_FIELD,
                                                          member)
                distance_to_cluster_center = euclidean(cluster_center_xy, member_xy)
                if distance_to_cluster_center < closest_distance:
                    closest_distance = distance_to_cluster_center
                    closest_building_id = member
            inner_dict[self.CLUSTER_CENTER_BUILDING_KEY] = closest_building_id
        Logger().debug(f"Cluster Centers added. Current dict: {cluster_dict}")
        return cluster_dict


    def add_sum_of_distances_field_per_cluster(self, cluster_dict, info_layer):
        total_distance = 0.0
        for cluster_id, inner_dict in cluster_dict.items():
            cluster_center_id = inner_dict[self.CLUSTER_CENTER_BUILDING_KEY]
            members = inner_dict[self.MEMBER_LIST_KEY]
            cluster_center_xy = DhpUtility.get_xy_by_id_field(info_layer,
                                                              self.UNIQUE_ID_FIELD,
                                                              cluster_center_id)
            for member in members:
                member_xy = DhpUtility.get_xy_by_id_field(info_layer,
                                                          self.UNIQUE_ID_FIELD,
                                                          member)
                total_distance += euclidean(cluster_center_xy, member_xy)
            inner_dict[self.SUM_OF_DISTANCES_PER_CLUSTER_KEY] = total_distance
        Logger().debug(f"Sum of distances per cluster added. Current Dictionary: {cluster_dict}")
        return cluster_dict

    def add_total_sum_of_distances_field(self, cluster_dict):
        total_sum_of_distances = 0.0
        for cluster_id, inner_dict in cluster_dict.items():
            total_sum_of_distances += inner_dict[self.SUM_OF_DISTANCES_PER_CLUSTER_KEY]
        new_cluster_dict = {
            self.TOTAL_SUM_OF_DISTANCES_KEY : total_sum_of_distances,
            self.CLUSTERS_KEY : cluster_dict
        }
        Logger().debug(f"Total sum of distances per cluster added. Current Dictionary: {new_cluster_dict}")
        return new_cluster_dict

    def flag_as_non_member(self, cluster_dict, cluster_id, candidate):
        cluster_dict[cluster_id][self.MEMBER_LIST_KEY].remove(candidate)
        cluster_dict[cluster_id][self.NON_MEMBER_KEY].append(candidate)
        Logger().debug(f"{candidate} was flagged as non-member. Current non-member list:"
                       f" {cluster_dict[cluster_id][self.NON_MEMBER_KEY]}")

    def add_non_member_list_to_cluster_dict(self, cluster_dict):
        for cluster_id, inner_dict in cluster_dict.items():
            inner_dict[self.NON_MEMBER_KEY] = []