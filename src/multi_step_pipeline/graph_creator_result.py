from dataclasses import dataclass
from qgis.core import QgsVectorLayer
import networkx as nx

@dataclass
class GraphCreatorResult:
    street_graph : nx.Graph
    building_centroids : QgsVectorLayer
    exploded_roads : QgsVectorLayer
    access_point_lines : QgsVectorLayer
