from .brkga.brkga_api import BrkgaAPI
from ..util.dhp_utility import DhpUtility
from scipy.spatial.distance import cdist
from ..util.config import Config

class ClusteringSecondStageAdapter():

    # ToDo: put in Config
    ID_FIELD = "osm_id"
    DISTANCE_MATRIX_FIELD = "distance_matrix"
    MEMBER_LIST_FIELD = "members"
    BRKGA_SOLUTION_FIELD = "brkga_solution"
    DEMAND_FIELD_LAYER = "peak_demand"
    DEMAND_FIELD_DICT = "demands"

    def __init__(self, cluster_dict,
                 buildings_layer,
                 building_centroids,
                 eliminate_buildings: bool,
                 number_of_clusters: int):
        self.cluster_dict = cluster_dict
        self.distance_matrix = None
        self.buildings_layer = buildings_layer
        self.building_centroids = building_centroids
        self.eliminate_buildings = eliminate_buildings
        self.number_of_clusters = number_of_clusters

    def get_member_lists_from_cluster_dict(self, cluster_dict) -> list:
        member_lists = []
        for cluster, members in cluster_dict.items():
            member_lists.append(members)
        return member_lists

    def add_distance_matrix_field_to_cluster_dict(self, cluster_dict) -> dict:
        new_dict = {}
        for cluster, member_list in cluster_dict.items():
            new_dict[cluster] = {
                self.MEMBER_LIST_FIELD: member_list,
                self.DISTANCE_MATRIX_FIELD: self.transform_member_ids_to_distance_matrix(member_list)
            }
        return new_dict

    def add_demands_field_to_dict(self, cluster_dict) -> dict:
        new_dict = {}
        for cluster, inner_dict in cluster_dict.items():
            inner_dict[self.DEMAND_FIELD_DICT] = self.get_demands_of_members(inner_dict[self.MEMBER_LIST_FIELD],
                                                                             self.building_centroids)
        return new_dict

    def do_brkga(self, cluster_dict):
        # ToDo: Just add field to cluster dict that represents the brkga solutions.
        # ToDo: For now: Just do the brkga so we can get logs.
        # ToDo: Check if dict has all fields required!
        for cluster, inner_dict in cluster_dict.items():
            member_list = inner_dict[self.MEMBER_LIST_FIELD]
            distance_matrix = inner_dict[self.DISTANCE_MATRIX_FIELD]
            demands = inner_dict[self.DEMAND_FIELD_DICT]
            brkga_api = BrkgaAPI()
            brkga_result = brkga_api.do_brkga(eliminate_buildings=self.eliminate_buildings,
                               distance_matrix=distance_matrix,
                               max_capacity=Config().get_heat_capacity(),
                               demands=demands,
                               num_clusters=self.number_of_clusters,
                               members=member_list)
            inner_dict[self.BRKGA_SOLUTION_FIELD] = brkga_result
        return cluster_dict

    def transform_member_ids_to_distance_matrix(self, member_id_list):
        member_xys = self.fill_member_xys(member_id_list)
        distance_matrix = cdist(member_xys, member_xys, 'euclidean')
        return member_id_list, distance_matrix

    def fill_member_xys(self, member_id_list):
        member_xys = []
        for member in member_id_list:
            feature = DhpUtility.get_feature_by_id_field(self.buildings_layer, self.ID_FIELD, member)
            feature_geom = feature.geometry()
            xy_tuple = (feature_geom.asPoint().x(), feature_geom.asPoint().y())
            member_xys.append(xy_tuple)
        return member_xys

    def get_demands_of_members(self, member_id_list, info_layer):
        demands = []
        for member in member_id_list:
            demand = DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                   self.ID_FIELD,
                                                                   member,
                                                                   self.DEMAND_FIELD_LAYER)
            demands.append(demand)
        return demands

