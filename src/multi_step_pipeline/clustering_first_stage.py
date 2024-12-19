from collections import defaultdict
from typing import Dict, List
from sklearn.cluster import DBSCAN
from qgis.core import QgsVectorLayer
from ..util.logger import Logger
import numpy as np


class ClusteringFirstStage:
    building_centroids : QgsVectorLayer = None
    ready_to_start : bool = False
    plot_buildings : bool = False
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
            clusters = self.do_clustering(prepared_data)
            self.print_results(clusters)
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
        return clusters

    def plot_clusters(self):
        if self.plot_buildings:
            pass
        pass

    def print_results(self, clusters):
        for cluster_id, cluster_ids in clusters.items():
            if cluster_id != 1:
                Logger().debug(f"Cluster {cluster_id}: {cluster_ids}")
            else:
                Logger().debug(f"Noise: {cluster_ids}")