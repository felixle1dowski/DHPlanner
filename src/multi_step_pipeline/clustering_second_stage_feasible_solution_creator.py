from I_clustering_second_stage_feasible_solution_creator import IClusteringSecondStageFeasibleSolutionCreator
from scipy.spatial.distance import cdist
from ..util.dhp_utility import DhpUtility
from ..util.logger import Logger
from ..util.config import Config

class ClusteringSecondStageFeasibleSolutionCreator(IClusteringSecondStageFeasibleSolutionCreator):

    # ToDo: Put in Config
    UNIQUE_ID_FIELD = "osm_id"

    MEMBER_LIST_KEY = "member_list"
    CURRENT_CAPACITY_KEY = "current_capacity"

    DEMAND_FIELD = "peak_demand"

    def __init__(self):
        pass

    def make_solution_feasible(self, cluster_dict: dict, cluster_center_dict: dict, info_layer):
        # ToDo: Check for validity (do dicts have the right fields?)
        # ToDo: I have to do the cluster_center_dict thingy!!
        distance_ranking_dict = self.create_distance_ranking_dict(cluster_dict, cluster_center_dict, info_layer)
        dict_with_capacity = self.add_capacity_field_to_cluster_dict(distance_ranking_dict, info_layer)
        feasible_solution = self.swap_cluster_membership_until_solution_feasible(dict_with_capacity,
                                                                                 cluster_center_dict,
                                                                                 info_layer)
        return feasible_solution

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
            distances_ranking.append((member, cdist(member_xy, cluster_center_xy)))
        sorted_by_distance = [id_ for id_ in sorted(distances_ranking,
                                                    key=lambda x: x[1],
                                                    reverse=True)]
        return sorted_by_distance

    def add_capacity_field_to_cluster_dict(self, cluster_dict, info_layer):
        dict_with_capacity = {}
        for (cluster_id, member_list) in cluster_dict.items():
            dict_with_capacity[cluster_id] = {
                self.MEMBER_LIST_KEY : member_list,
                self.CURRENT_CAPACITY_KEY : self.calculate_current_capacity(info_layer, member_list)
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
                    for cluster_center in cluster_centers_ranked:
                        if cluster_center_dict[cluster_id][self.CURRENT_CAPACITY_KEY] > DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                                                                                      self.UNIQUE_ID_FIELD,
                                                                                                                                      candidate,
                                                                                                                                      self.DEMAND_FIELD):
                            self.swap_cluster_membership(cluster_dict, candidate, cluster_id, cluster_center, info_layer)
                            break
                    if inner_dict[self.CURRENT_CAPACITY_KEY] >= 0:
                        break
        return cluster_dict

    def swap_cluster_membership(self, cluster_dict, member,
                                from_cluster, to_cluster, info_layer):
        member_demand = DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                      self.UNIQUE_ID_FIELD,
                                                                      member,
                                                                      self.DEMAND_FIELD)
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
            distance = cdist(cluster_xy, member_xy)
            ranking_list.append((cluster_id, distance))
        sorted_by_distance = [id_ for id_ in sorted(ranking_list,
                                                    key=lambda x: x[1],
                                                    reverse=False)]
        return sorted_by_distance