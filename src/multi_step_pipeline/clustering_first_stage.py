from collections import defaultdict
from typing import Dict, List
import time
from sklearn.cluster import DBSCAN
from qgis.core import (QgsVectorLayer, QgsField, QgsProject,
                       QgsSymbol, QgsRendererCategory,
                       QgsCategorizedSymbolRenderer, QgsFeature,
                       QgsFeatureRequest)
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from ..util.logger import Logger
from ..util.config import Config
from ..util.dhp_utility import DhpUtility
import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt


class ClusteringFirstStage:
    building_centroids : QgsVectorLayer = None
    buildings_layer : QgsVectorLayer = None
    selected_buildings_expression : str = None
    ready_to_start : bool = False
    plot_buildings : bool = False
    """Used for further debugging. If True, an image gets generated in the debug folder."""
    clusters : Dict[int, List[int]] = {}
    """Dictionary for clustered buildings. Get specified by building IDs."""
    CLUSTER_FIELD_NAME = "clusterId"
    SHARED_ID_FIELD_NAME = 'osm_id'
    CLUSTER_RESULTS_ID_COL_NAME = 'id'
    CLUSTER_RESULTS_CLUSTER_COL_NAME = 'cluster'
    CLUSTER_RESULTS_CLUSTER_COL_N = 0
    EPS = 0.01
    MIN_SAMPLES = 2

    def __init__(self):
        pass

    def set_preprocessing_result(self, building_centroids_layer):
        self.building_centroids = building_centroids_layer
        self.buildings_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        self.ready_to_start = True

    def start(self):
        if self.ready_to_start:
            self.selected_buildings_expression = self.prepare_filter_expression()
            # prepared_data = self.prepare_data_for_clustering()
            # clusters, features, labels = self.do_clustering(prepared_data)
            # self.print_results(clusters)
            distances_list, amount_of_features, osm_ids = self.calculate_distances_between_points()
            distance_matrix = self.construct_distance_matrix(distances_list, amount_of_features)
            distance_df = self.construct_distance_matrix_df(distance_matrix, osm_ids)
            clustering_results = self.do_clustering_with_custom_metric(distance_df)
            output_layer = self.prepare_output_layer_for_visualization(clustering_results)
            renderer = self.create_unique_cluster_colors_renderer(clustering_results[self.CLUSTER_RESULTS_CLUSTER_COL_NAME].values,
                                                       output_layer.geometryType(),
                                                       self.CLUSTER_FIELD_NAME)
            self.visualize_clustering_results_by_repainting(output_layer, renderer)
            results = self.prepare_return(clustering_results)
            # self.plot_clusters(clusters, features, labels)
            # self.assign_clusters_to_building_centroids(clusters)
            # self.visualize_building_cluster_membership(labels)
        else:
            raise Exception("Not ready to start")

    def prepare_data_for_clustering(self):
        prepared_data = []
        selected_centroids = self.building_centroids.getFeatures()
        for centroid in selected_centroids:
            xy = centroid.geometry().asPoint()
            x = xy.x()
            y = xy.y()
            prepared_data.append({
                "id" : centroid.id(),
                "x" : x,
                "y" : y
            })
            Logger().debug(f"centroid added in preparation for clustering: "
                         f"id: {centroid.id()}, x: {x}, y: {y}")
        return prepared_data

    def calculate_distances_between_points(self):
        """Calculates nearest points for all elements present in filtered buildings layer."""
        # we need two iterators.
        features = self.buildings_layer.getFeatures(self.selected_buildings_expression)
        features_list = DhpUtility.convert_iterator_to_list(features)
        features_list_length = len(features_list)
        distances_between_buildings = []
        osm_ids = []
        for i in range(features_list_length):
            feature_i = features_list[i]
            feature_i_osm_id = DhpUtility.get_value_from_field(self.buildings_layer, feature_i, "osm_id")
            osm_ids.append(feature_i_osm_id)
            for j in range(i + 1, features_list_length):
                feature_j = features_list[j]
                geometry_i = feature_i.geometry()
                geometry_j = feature_j.geometry()
                distance = geometry_i.distance(geometry_j)
                feature_i_osm_id = DhpUtility.get_value_from_field(self.buildings_layer, feature_i, "osm_id")
                feature_j_osm_id = DhpUtility.get_value_from_field(self.buildings_layer, feature_j, "osm_id")
                distance_entry = {
                    "feature_i_osm_id": feature_i_osm_id,
                    "feature_j_osm_id": feature_j_osm_id,
                    "distance" : distance
                }
                distances_between_buildings.append(distance_entry)
                self.log_distances_between_geometries(feature_i, feature_j, distance, self.buildings_layer,
                                                      "osm_id")
        return distances_between_buildings, features_list_length, osm_ids

    def construct_distance_matrix(self, distances_between_geometries, amount_of_features):
        condensed_distances = [i["distance"] for i in distances_between_geometries]
        condensed_labels = [i["feature_i_osm_id"] for i in distances_between_geometries]
        distance_matrix = np.zeros((amount_of_features, amount_of_features))
        labels = []
        k = 0
        for i in range(amount_of_features):
            for j in range(i + 1, amount_of_features):
                distance_matrix[i, j] = condensed_distances[k]
                labels.append(condensed_labels[k])
                k += 1
        distance_matrix = distance_matrix + distance_matrix.T
        if not np.allclose(distance_matrix, distance_matrix.T):
            raise Exception("Distance matrix is not symmetric. Error in distance matrix calculation.")
        return distance_matrix

    def construct_distance_matrix_df(self, distance_matrix, label_names):
        distance_df = pd.DataFrame(distance_matrix, index=label_names, columns=label_names)
        Logger().debug(distance_df)
        return distance_df

    def do_clustering_with_custom_metric(self, distance_df):
        db = DBSCAN(eps=self.EPS, min_samples=self.MIN_SAMPLES, metric="precomputed")
        clusters = db.fit_predict(distance_df.values)
        labels = distance_df.index
        columns = [self.CLUSTER_RESULTS_CLUSTER_COL_NAME]
        cluster_results = pd.DataFrame(clusters, index=labels, columns=columns)
        Logger().debug(cluster_results)
        return cluster_results

    def prepare_output_layer_for_visualization(self, cluster_results):
        """Prepares output layer for visualization and further calculation.
                - creates output layer
                - adds cluster id field to output layer
                - transfers correct values into cluster id field
        """
        output_layer = QgsVectorLayer("Polygon?crs=" + self.buildings_layer.crs().authid(), "Clustered Buildings", "memory")
        output_layer_data = output_layer.dataProvider()
        output_layer_data.addAttributes(self.buildings_layer.fields())
        output_layer.updateFields()
        DhpUtility.create_new_field(output_layer, self.CLUSTER_FIELD_NAME, QVariant.String)
        output_layer.updateFields()
        selected_buildings_features = self.buildings_layer.getFeatures(self.selected_buildings_expression)
        for building in selected_buildings_features:
            new_feature = QgsFeature()
            new_feature.setGeometry(building.geometry())
            new_feature.setAttributes(building.attributes())
            output_layer_data.addFeature(new_feature)

        for index, row in cluster_results.iterrows():
            value = str(row.iloc[self.CLUSTER_RESULTS_CLUSTER_COL_N])
            DhpUtility.assign_value_to_field_by_id(output_layer, self.SHARED_ID_FIELD_NAME, index, self.CLUSTER_FIELD_NAME, value)

        QgsProject.instance().addMapLayer(output_layer)
        return output_layer

    def visualize_clustering_results_by_repainting(self, output_layer, renderer):
        output_layer.setRenderer(renderer)
        output_layer.triggerRepaint()

    @staticmethod
    def log_distances_between_geometries(feature1, feature2, distance, layer, id_field_name):
        """To be used if a layer uses a custom id."""
        # we only do this when the log level is adequately low.
        if Config().get_log_level == "debug":
            id_field_name_idx = layer.fields().indexFromName(id_field_name)
            feature1_id = str(feature1[id_field_name_idx])
            feature2_id = str(feature2[id_field_name_idx])
            Logger().debug(f"distance between Feature: {feature1_id} and Feature: {feature2_id}: {distance}")


    def do_clustering(self, data):
        ids = [point['id'] for point in data]
        features = np.array([[point['x'], point['y']] for point in data])

        dbscan = DBSCAN(eps=self.EPS, min_samples=self.MIN_SAMPLES)
        labels = dbscan.fit_predict(features)

        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters[label].append(ids[idx])
        return clusters, features, labels

    def plot_clusters(self, clusters, features, labels):
        if not self.plot_buildings:
            return
        unique_labels = set(labels)
        colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))

        plt.figure(figsize=(8,6))
        for label, color in zip(unique_labels, colors):
            if label == -1:
                color = "k"
                label_name = "noise"
            else:
                label_name = f"Cluster {label}"
            cluster_points = features[labels == label]
            plt.scatter(cluster_points[:, 0], cluster_points[:, 1], c=color, label=label_name)

        plt.title("Clustering first stage")
        plt.xlabel("x coordinate")
        plt.ylabel("y coordinate")
        plt.legend()
        plt.grid(True)
        file_path = f"{Config().get_debug_folder_path()}clusters{time.asctime()}.png"
        plt.savefig(file_path)

    def print_results(self, clusters):
        for cluster_id, cluster_ids in clusters.items():
            if cluster_id != 1:
                Logger().debug(f"Cluster {cluster_id}: {cluster_ids}")
            else:
                Logger().debug(f"Noise: {cluster_ids}")

    def assign_clusters_to_building_centroids(self, clusters):
        DhpUtility.create_new_field(self.building_centroids, self.CLUSTER_FIELD_NAME, QVariant.String)
        for cluster_id, cluster_ids in clusters.items():
            features = self.building_centroids.getFeatures(cluster_ids)
            for feature in features:
                DhpUtility.assign_value_to_field(self.building_centroids,
                                                 self.CLUSTER_FIELD_NAME,
                                                 feature,
                                                 str(cluster_id))

    def visualize_building_cluster_membership(self, labels):
        buildings_layer = self.buildings_layer
        cluster_field = self.CLUSTER_FIELD_NAME
        output_layer = QgsVectorLayer("Polygon?crs=" + buildings_layer.crs().authid(), "Clustered Buildings", "memory")
        output_layer_data = output_layer.dataProvider()
        selected_centroids = self.building_centroids.getFeatures()
        selected_buildings_features = self.buildings_layer.getFeatures(self.selected_buildings_expression)

        DhpUtility.create_new_field(buildings_layer, cluster_field, QVariant.String)
        DhpUtility.transfer_values_by_matching_id(buildings_layer,
                                                  selected_centroids, selected_buildings_features,
                                                  cluster_field, self.SHARED_ID_FIELD_NAME)
        # we also need to rewind this iterator.
        selected_buildings_features = self.buildings_layer.getFeatures(self.selected_buildings_expression)

        # preparing the new layer to have the same fields as the original building layer
        output_layer_data.addAttributes(buildings_layer.fields())
        output_layer.updateFields()

        for building in selected_buildings_features:
            new_feature = QgsFeature()
            new_feature.setGeometry(building.geometry())
            new_feature.setAttributes(building.attributes())
            output_layer_data.addFeature(new_feature)
        color_renderer = self.create_unique_cluster_colors_renderer(labels,
                                                                    output_layer.geometryType(),
                                                                    cluster_field)
        output_layer.setRenderer(color_renderer)
        output_layer.triggerRepaint()
        QgsProject.instance().addMapLayer(output_layer)

    def create_unique_cluster_colors_renderer(self, labels, geometry_type, cluster_field):
        unique_labels = set(labels)
        categories = []
        for cluster_id in unique_labels:
            cluster_id = str(cluster_id)
            symbol = QgsSymbol.defaultSymbol(geometry_type)
            colors = QColor.fromRgb(random.randrange(0,256), random.randrange(0,256), random.randrange(0,256))
            symbol.setColor(colors)
            category = QgsRendererCategory(cluster_id, symbol, cluster_id)
            categories.append(category)
        renderer = QgsCategorizedSymbolRenderer(cluster_field, categories)
        return renderer

    def prepare_filter_expression(self):
        """Used to only select buildings that have been processed and selected via preprocessing.
            These are available via the building_centroids."""
        # ToDo: This should probably be part of the preprocessing stage.
        osm_ids = [str(feature[self.SHARED_ID_FIELD_NAME]) for feature in self.building_centroids.getFeatures()]
        osm_list = ",".join(f"'{osm_id}'" for osm_id in osm_ids)
        expression = f"{self.SHARED_ID_FIELD_NAME} IN ({osm_list})"
        return expression

    def prepare_return(self, cluster_df):
        return_dict = defaultdict(list)
        for building_id, cluster_id in cluster_df.itertuples():
            return_dict[cluster_id].append(building_id)
        Logger().debug(return_dict)
        return return_dict