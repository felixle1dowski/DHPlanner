import os
import random

import numpy as np
from brkga_mp_ipr.enums import Sense

from ...util.not_yet_implemented_exception import NotYetImplementedException
from ...util.logger import Logger
from ...util.config import Config
from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from .fitness_function import FitnessFunction
from .brkga import Brkga
from .pipe_diameter_catalogue import PipeDiameterCatalogue
from .pipe_prices import PipePrices
from .mass_flow_calculation import MassFlowCalculation

class BrkgaAPI:

    EXCLUDED_KEY = -1
    MEMBER_LIST_KEY = "member_list"
    NUM_GENERATIONS = 2 # this is low. See: Praseyeto (2015).
    SEED_DEFAULT = 1
    # ToDo: Set in Config!

    CLUSTER_CENTER_KEY = "cluster_center"
    ID_FIELD_NAME = "osm_id"
    PIVOT_STRING_SINGLE = "pivot_members_end"

    SCRIPT_DIR = os.path.dirname(__file__)
    CATALOGUE_FOLDER_PATH = os.path.join(SCRIPT_DIR, "./pipe_diameter_catalogues")

    PRICES_JSON_PATH = os.path.join(SCRIPT_DIR, "./pipe_prices/SDR_11_price.json")

    def __init__(self):
        self.seed_to_use = 0

    # ToDo: Validate members and distance matrix. They need to have the same dimensions!
    def do_brkga(self,
                 graph,
                 max_capacity: float,
                 demands: {int: float},
                 yearly_demands: {int: float},
                 num_clusters: int,
                 members: list,
                 warm_start: dict,
                 total_distance: float,
                 total_member_list: list,
                 id_to_node_translation_dict: dict,
                 pivot_element="none"):

        result = self.do_brkga_(graph,
                                                       max_capacity,
                                                       demands,
                                                       yearly_demands,
                                                       num_clusters,
                                                       members,
                                                       warm_start,
                                                       total_distance,
                                                       total_member_list,
                                                       id_to_node_translation_dict,
                                                       pivot_element)
        return result

    def do_brkga_(self,
                  graph,
                  max_capacity: float,
                  demands: {int: float},
                  yearly_demands: {int: float},
                  num_clusters: int,
                  members: list,
                  warm_start: dict,
                  total_distance: float,
                  total_member_list: list,
                  id_to_node_translation_dict: dict,
                  pivot_element="none"):
        if pivot_element not in ["none", "single", "double"]:
            raise ValueError(f"pivot_element must be 'none', 'single', or 'double'. Is: {pivot_element}")
        if pivot_element == "single":
            total_member_list.append("pivot_members_end")
        elif pivot_element == "double":
            total_member_list.append("pivot_cluster_centers_end")
            total_member_list.append("pivot_members_end")
        instance = ClusteringInstance(graph, max_capacity, demands, yearly_demands, members, id_to_node_translation_dict, pivot_element)
        # ToDo: Fitness Function should probably be passed via dependency injection!

        catalogue_interpreter = PipeDiameterCatalogue()
        catalogues = catalogue_interpreter.open_catalogues(self.CATALOGUE_FOLDER_PATH)
        catalogue_df = catalogue_interpreter.create_dataframe(catalogues)
        # Logger().debug(f"catalogue df was created: {catalogue_df}")

        pipe_prices = PipePrices.open_prices_json(self.PRICES_JSON_PATH)

        decoder = ClusteringDecoder(instance, num_clusters, FitnessFunction(instance,
                                                                            id_to_node_translation_dict,
                                                                            catalogue_df,
                                                                            pipe_prices), pivot_element)
        initial_solution = self.encode_warm_start(warm_start, total_member_list, pivot_element)
        self.seed_to_use = self.SEED_DEFAULT
        if Config().get_use_random_seed():
            self.seed_to_use = random.randint(1,1_000_000_000)
        brkga = Brkga(instance=instance,
                      seed=self.seed_to_use,
                      num_generations=self.NUM_GENERATIONS,
                      sense=Sense.MINIMIZE,
                      decoder=decoder,
                      initial_solution=initial_solution)
        result = brkga.do_brkga()
        return result

    def encode_warm_start(self, warm_start, total_member_list : list, pivot_element="none"):
        cluster_ids = []
        members = []
        for cluster_id, inner_dict in warm_start.items():
            if cluster_id != self.EXCLUDED_KEY:
                cluster_center = inner_dict[self.CLUSTER_CENTER_KEY]
                cluster_ids.append(cluster_center)
                for member in inner_dict[self.MEMBER_LIST_KEY]:
                    if member != cluster_center:
                        members.append(member)
        excluded_members = warm_start[self.EXCLUDED_KEY][self.MEMBER_LIST_KEY]
        if pivot_element == "single":
            id_solution = cluster_ids + members + [self.PIVOT_STRING_SINGLE] + excluded_members
        else:
            id_solution = cluster_ids + members + excluded_members
        if len(id_solution) != len(total_member_list):
            raise Exception(f"Mismatched length of parameter total_member_list ({len(total_member_list)}) "
                            f"and local variable id_solution ({len(id_solution)})")
        keys = sorted([random.random() for _ in range(len(id_solution))])
        initial_chromosome = [0] * len(id_solution)
        for i in range(len(id_solution)):
            member_index = total_member_list.index(id_solution[i])
            initial_chromosome[member_index] = keys[i]
        # Logger().debug(f"Initial Chromosome created: {initial_chromosome}")
        return initial_chromosome