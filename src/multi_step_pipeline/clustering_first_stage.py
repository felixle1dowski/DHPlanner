from collections import defaultdict
from typing import Dict, List
from sklearn.cluster import DBSCAN
from qgis.core import QgsVectorLayer
from ..util.logger import Logger
from ..util.config import Config
import numpy as np
import matplotlib.pyplot as plt


class ClusteringFirstStage:
    building_centroids : QgsVectorLayer = None
    ready_to_start : bool = False
    plot_buildings : bool = True
    """Used for further debugging. If True, an image gets generated in the debug folder."""
    clusters : Dict[int, List[int]] = {}
    """Dictionary for clustered buildings. Get specified by building IDs."""

    def __init__(self):
        pass

    def set_preprocessing_result(self, building_centroids):
        self.building_centroids = building_centroids
        self.ready_to_start = True

    def start(self):
        if self.ready_to_start:
            prepared_data = self.prepare_data_for_clustering()
            clusters, features, labels = self.do_clustering(prepared_data)
            self.print_results(clusters)
            self.plot_clusters(clusters, features, labels)
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
        file_path = f"{Config().get_debug_folder_path()}clusters.png"
        plt.savefig(file_path)


    def print_results(self, clusters):
        for cluster_id, cluster_ids in clusters.items():
            if cluster_id != 1:
                Logger().debug(f"Cluster {cluster_id}: {cluster_ids}")
            else:
                Logger().debug(f"Noise: {cluster_ids}")