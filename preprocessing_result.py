from dataclasses import dataclass

from qgis.core import QgsVectorLayer

@dataclass
class PreprocessingResult:

    building_centroids: QgsVectorLayer
    exploded_roads: QgsVectorLayer