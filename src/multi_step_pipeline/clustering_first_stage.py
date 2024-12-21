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
import random
import matplotlib.pyplot as plt


class ClusteringFirstStage:
    building_centroids : QgsVectorLayer = None
    buildings_layer : QgsVectorLayer = None
    ready_to_start : bool = False
    plot_buildings : bool = False
    """Used for further debugging. If True, an image gets generated in the debug folder."""
    clusters : Dict[int, List[int]] = {}
    """Dictionary for clustered buildings. Get specified by building IDs."""
    CLUSTER_FIELD_NAME = "clusterId"
    SHARED_ID_FIELD_NAME = 'osm_id'

    def __init__(self):
        pass

    def set_preprocessing_result(self, building_centroids_layer):
        self.building_centroids = building_centroids_layer
        self.buildings_layer = QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0]
        self.ready_to_start = True

    def start(self):
        if self.ready_to_start:
            prepared_data = self.prepare_data_for_clustering()
            clusters, features, labels = self.do_clustering(prepared_data)
            self.print_results(clusters)
            self.plot_clusters(clusters, features, labels)
            self.assign_clusters_to_building_centroids(clusters)
            self.visualize_building_cluster_membership(labels)
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

    def do_clustering(self, data):
        ids = [point['id'] for point in data]
        features = np.array([[point['x'], point['y']] for point in data])

        dbscan = DBSCAN(eps=30.0, min_samples=2)
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
        osm_ids = [str(feature[self.SHARED_ID_FIELD_NAME]) for feature in selected_centroids]
        osm_list = ",".join(f"'{osm_id}'" for osm_id in osm_ids)
        expression = f"{self.SHARED_ID_FIELD_NAME} IN ({osm_list})"
        request = QgsFeatureRequest().setFilterExpression(expression)
        Logger().debug(f"filter expression: {request.filterExpression()}")
        selected_buildings = buildings_layer.getFeatures(request)
        # we get the features again to "rewind" the iterator.
        selected_centroids = self.building_centroids.getFeatures()

        DhpUtility.create_new_field(buildings_layer, cluster_field, QVariant.String)
        DhpUtility.transfer_values_by_matching_id(buildings_layer,
                                                  selected_centroids, selected_buildings,
                                                  cluster_field, self.SHARED_ID_FIELD_NAME)
        # we also need to rewind this iterator.
        selected_buildings = buildings_layer.getFeatures(request)

        # preparing the new layer to have the same fields as the original building layer
        output_layer_data.addAttributes(buildings_layer.fields())
        output_layer.updateFields()

        for building in selected_buildings:
            new_feature = QgsFeature()
            new_feature.setGeometry(building.geometry())
            new_feature.setAttributes(building.attributes())
            output_layer_data.addFeature(new_feature)
        color_renderer = self.create_unique_cluster_colors_renderer(labels,
                                                                    output_layer.geometryType(),
                                                                    cluster_field)
        Logger().debug(f"color renderer: {color_renderer.categories()}")
        output_layer.setRenderer(color_renderer)
        Logger().debug(f"Renderer applied: {output_layer.renderer()}")
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
            Logger().debug(f"Cluster {cluster_id}, string: {str(cluster_id)}")
            category = QgsRendererCategory(cluster_id, symbol, cluster_id)
            categories.append(category)
        renderer = QgsCategorizedSymbolRenderer(cluster_field, categories)
        return renderer
