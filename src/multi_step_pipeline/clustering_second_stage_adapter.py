from .brkga.brkga_api import BrkgaAPI
from ..util.dhp_utility import DhpUtility
from scipy.spatial.distance import cdist
from ..util.config import Config

class ClusteringSecondStageAdapter():

    # ToDo: put in Config
    ID_FIELD = "osm_id"
    DISTANCE_MATRIX_KEY = "distance_matrix"
    MEMBER_LIST_KEY = "total_member_list"
    BRKGA_SOLUTION_KEY = "brkga_solution"
    DEMAND_FIELD_KEY = "demands"
    TOTAL_DISTANCE_KEY = "total_sum_of_distances"
    FEASIBLE_SOLUTION_KEY = "clusters"
    DEMAND_FIELD_LAYER = "peak_demand"
    YEARLY_DEMAND_FIELD_LAYER = "individual_heat_demand"

    def do_brkga(self, graph, cluster_dict, info_layer, number_of_clusters : int, id_to_node_translation_dict, pivot_element: str):
        # ToDo: Just add field to cluster dict that represents the brkga solutions.
        # ToDo: For now: Just do the brkga so we can get logs.
        # ToDo: Check if dict has all fields required!
        brkga_api = BrkgaAPI()
        members = cluster_dict[self.MEMBER_LIST_KEY]
        demands = self.get_demands_of_members_as_dict(members, info_layer)
        yearly_demands = self.get_yearly_demands_of_members_as_dict(members, info_layer)
        feasible_solution = cluster_dict[self.FEASIBLE_SOLUTION_KEY]
        total_distance = cluster_dict[self.TOTAL_DISTANCE_KEY]
        result = brkga_api.do_brkga(
                                     graph=graph,
                                     max_capacity=Config().get_heat_capacity(),
                                     demands=demands,
                                     yearly_demands=yearly_demands,
                                     num_clusters=number_of_clusters,
                                     members=members,
                                     warm_start=feasible_solution,
                                     total_distance=total_distance,
                                     total_member_list=members,
                                    id_to_node_translation_dict=id_to_node_translation_dict,
                                    pivot_element=pivot_element)
        return result


    def get_demands_of_members_as_dict(self, members, info_layer):
        # ToDo: I use something like this multiple times. Put this in DHPUtility or calculate it ONCE!
        demand_dict = {}
        for member in members:
            demand_dict[member] = DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                                  self.ID_FIELD,
                                                                                  member,
                                                                                  self.DEMAND_FIELD_LAYER)
        return demand_dict

    def get_yearly_demands_of_members_as_dict(self, members, info_layer):
        yearly_demand_dict = {}
        for member in members:
            yearly_demand_dict[member] = DhpUtility.get_value_from_feature_by_id_field(info_layer,
                                                                                       self.ID_FIELD,
                                                                                       member,
                                                                                       self.YEARLY_DEMAND_FIELD_LAYER)
        return yearly_demand_dict