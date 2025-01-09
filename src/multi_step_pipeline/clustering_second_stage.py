import math
from collections import defaultdict

import numpy as np
from qgis.core import QgsVectorLayer
from sklearn.cluster import BisectingKMeans
from ..util.logger import Logger
from ..util.config import Config

from src.util.dhp_utility import DhpUtility


class ClusteringSecondStage:

    buildings_layer : QgsVectorLayer = None
    # ToDo: Validate that it has all the required fields!
    building_centroids : QgsVectorLayer = None
    # ToDo: Validate that it has all the required fields!
    first_stage_cluster_dict : defaultdict = None
    ready_to_start = False

    PEAK_DEMAND_FIELD_NAME = "peak_demand"
    # ToDo: Put in config.
    UNIQUE_ID_FIELD_NAME_CENTROIDS = "osm_id"

    def __init__(self, first_stage_cluster_dict, buildings_layer):
        self.first_stage_cluster_dict = first_stage_cluster_dict
        self.buildings_layer = buildings_layer
        self.ready_to_start = True

    def start(self):
        if self.ready_to_start:
            for cluster_id, cluster_members in self.first_stage_cluster_dict.items():
                temporary_solution = self.generate_temporary_clustering_solution(cluster_id, cluster_members)
            pass

    def generate_temporary_clustering_solution(self, cluster_id, cluster_members):
        member_features_iterator = DhpUtility.get_features_from_id_field(self.building_centroids,
                                                                self.UNIQUE_ID_FIELD_NAME_CENTROIDS,
                                                                cluster_members)
        member_features_list = DhpUtility.convert_iterator_to_list(member_features_iterator)
        xys = self.collect_centroid_xys(member_features_list)
        weights = self.collect_centroid_weights(member_features_list)
        number_of_clusters = self.calculate_number_of_necessary_clusters(weights)
        self.do_kmeans_clustering(xys, weights, number_of_clusters)
        self.make_temporary_solution_feasible()
        return ""
        pass

    def calculate_number_of_necessary_clusters(self, weight_list):
        # ToDo: assert weight_list is list of floats.
        sum_of_demands = sum(weight_list)
        heat_capacity = Config().get_heat_capacity()
        necessary_clusters = sum_of_demands / heat_capacity
        decimal_places = necessary_clusters - int(necessary_clusters)
        result = -1
        if decimal_places * 100 > Config().get_minimum_heat_capacity_exhaustion():
            result = math.ceil(necessary_clusters)
        else:
            result = math.floor(necessary_clusters)
        return result

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

    def get_number_of_clusters(self):
        number_of_clusters = len(self.first_stage_cluster_dict)
        return number_of_clusters

    def collect_centroid_xys(self, building_centroid_features):
        """param building_centroid_features is a list of Qgis features."""
        centroid_xys = []
        for feature in building_centroid_features:
            feature_geom = feature.geometry()
            point = feature_geom.asPoint()
            centroid_xys.append([point.x(), point.y()])
        return centroid_xys

    def collect_centroid_weights(self, building_centroid_features):
        """param building_centroid_features is a list of Qgis features."""
        centroid_weights = []
        for feature in building_centroid_features:
            weight = DhpUtility.get_value_from_field(self.building_centroids, feature, self.PEAK_DEMAND_FIELD_NAME)
            centroid_weights.append(weight)
        return centroid_weights

    def make_temporary_solution_feasible(self):
        pass

    def generate_capacitated_centered_clustering_solution(self, temporary_clustering_solution):
        pass