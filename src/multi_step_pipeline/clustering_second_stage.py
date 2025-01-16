import math
from collections import defaultdict

import numpy as np
import subprocess
import sys
from qgis.core import QgsVectorLayer
from sklearn.cluster import BisectingKMeans

from .I_clustering_second_stage_feasible_solution_creator import IClusteringSecondStageFeasibleSolutionCreator

# ToDo: Put all of this into class that handles dependencies!!
required_version = (1,1)


from ..util.logger import Logger
from ..util.config import Config

from ..util.dhp_utility import DhpUtility


class ClusteringSecondStage:

    buildings_layer : QgsVectorLayer = None
    # ToDo: Validate that it has all the required fields!
    building_centroids : QgsVectorLayer = None
    # ToDo: Validate that it has all the required fields!
    first_stage_cluster_dict : defaultdict = None
    ready_to_start = False
    feasible_solution_creator : IClusteringSecondStageFeasibleSolutionCreator = None

    PEAK_DEMAND_FIELD_NAME = "peak_demand"
    # ToDo: Put in config.
    UNIQUE_ID_FIELD_NAME_CENTROIDS = "osm_id"

    def set_first_stage_result(self, first_stage_cluster_dict,
                               buildings_layer,
                               building_centroids_layer,
                               feasible_solution_creator: IClusteringSecondStageFeasibleSolutionCreator,):
        self.first_stage_cluster_dict = first_stage_cluster_dict
        self.buildings_layer = buildings_layer
        self.building_centroids = building_centroids_layer
        self.ready_to_start = True
        self.feasible_solution_creator = feasible_solution_creator

    def start(self):
        if self.ready_to_start:
            for cluster_id, cluster_members in self.first_stage_cluster_dict.items():
                temporary_solution, cluster_center_dict = self.generate_temporary_clustering_solution(cluster_id, cluster_members)
                feasible_solution = self.feasible_solution_creator.make_solution_feasible(temporary_solution,
                                                                 cluster_center_dict,
                                                                 self.building_centroids)
                Logger().debug(f"feasible solution has been created for cluster {cluster_id}\n"
                               f"solution: {feasible_solution}")


    def generate_temporary_clustering_solution(self, cluster_id, cluster_members):
        member_features_iterator = DhpUtility.get_features_by_id_field(self.building_centroids,
                                                                       self.UNIQUE_ID_FIELD_NAME_CENTROIDS,
                                                                       cluster_members)
        member_features_list = DhpUtility.convert_iterator_to_list(member_features_iterator)
        xys = self.collect_centroid_xys(member_features_list)
        weights = self.collect_centroid_weights(member_features_list)
        number_of_clusters = self.calculate_number_of_necessary_clusters(weights)
        kmeans_result = self.do_kmeans_clustering(xys, weights, number_of_clusters)
        cluster_center_dict = self.generate_cluster_center_dict(kmeans_result)
        member_features_list_ids = [id_value[self.UNIQUE_ID_FIELD_NAME_CENTROIDS] for id_value in member_features_list]
        cluster_dict = self.make_labels_into_cluster_dict(member_features_list_ids, kmeans_result.labels_)

        # ToDo: Change this after making the solution feasible.
        return cluster_dict, cluster_center_dict

    def calculate_number_of_necessary_clusters(self, weight_list):
        # ToDo: assert weight_list is list of floats.
        weight_list_as_floats = list(map(float, weight_list))
        sum_of_demands = sum(weight_list_as_floats)
        heat_capacity = float(Config().get_heat_capacity())
        necessary_clusters = sum_of_demands / heat_capacity
        decimal_places = necessary_clusters - int(necessary_clusters)
        necessary_clusters_whole = math.floor(necessary_clusters)
        if decimal_places * 100 > Config().get_minimum_heat_capacity_exhaustion():
            necessary_clusters_whole += 1
        return necessary_clusters_whole

    def do_kmeans_clustering(self, xys_list, weight_list, number_of_clusters):
        """do k-means clustering for a single building group. param building_centroid_features is a list of Qgis Features."""
        X = np.array(xys_list)
        weights = np.array(weight_list)
        bisect_means = BisectingKMeans(n_clusters=number_of_clusters,
                                       random_state=0,
                                       init='k-means++',
                                       algorithm='elkan',
                                       bisecting_strategy='largest_cluster')
        result = bisect_means.fit(X, weights)
        Logger().debug(result.labels_)
        Logger().debug(result.cluster_centers_)
        return result

    def get_number_of_clusters(self):
        number_of_clusters = len(self.first_stage_cluster_dict)
        return number_of_clusters

    def collect_centroid_xys(self, chosen_building_centroid_features):
        """param building_centroid_features is a list of Qgis features."""
        centroid_xys = []
        for feature in chosen_building_centroid_features:
            feature_geom = feature.geometry()
            point = feature_geom.asPoint()
            centroid_xys.append([point.x(), point.y()])
        return centroid_xys

    def collect_centroid_weights(self, chosen_building_centroid_features):
        """param building_centroid_features is a list of Qgis features."""
        centroid_weights = []
        for feature in chosen_building_centroid_features:
            weight = DhpUtility.get_value_from_field(self.building_centroids, feature, self.PEAK_DEMAND_FIELD_NAME)
            centroid_weights.append(weight)
        return centroid_weights

    def make_labels_into_cluster_dict(self, member_list, labels):
        cluster_dict = {}
        if len(member_list) != len(labels):
            raise Exception("member list and labels must have same lenght")
        for unique_label in set(labels):
            cluster_dict[unique_label] = []
        for i in range(len(member_list)):
            cluster_dict[labels[i]].append(member_list[i])
        Logger().debug(f"Cluster dict has been created.\n {cluster_dict}")
        return cluster_dict

    def generate_cluster_center_dict(self, temporary_solution):
        cluster_center_dict = {}
        cluster_center_xys = temporary_solution.cluster_centers_
        list_of_xy_tuples = list(map(tuple, cluster_center_xys))
        for i in range(len(list_of_xy_tuples)):
            cluster_center_dict[i] = list_of_xy_tuples[i]
        Logger().debug(f"Cluster center dict has been created.\n {cluster_center_dict}")
        return cluster_center_dict