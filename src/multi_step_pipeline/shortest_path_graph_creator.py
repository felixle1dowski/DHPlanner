import networkx as nx

from ..util import function_timer
from ..util.logger import Logger
from ..util.dhp_utility import DhpUtility
from ..util.function_timer import FunctionTimer
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsFeature, QgsProject


class ShortestPathGraphCreator:
    graph_creator_result = None
    relevant_nodes = None
    graph = None
    building_centroids = None
    line_layer = None
    access_point_lines = None
    LOG_PATH = False
    DESIRED_CRS = QgsCoordinateReferenceSystem('EPSG:4839')
    function_timer = FunctionTimer()

    def __init__(self):
        pass


    @function_timer.timed_function
    def set_required_fields(self, graph, line_layer, relevant_nodes):
        self.graph = graph
        self.line_layer = line_layer
        self.relevant_nodes = relevant_nodes

    @function_timer.timed_function
    def start(self):
        shortest_path_graph = self.construct_shortest_paths_graph(self.relevant_nodes)
        mst = self.create_mst(shortest_path_graph)
        self.visualize_mst(mst)
        return shortest_path_graph

    @function_timer.timed_function
    def construct_shortest_paths_graph(self, relevant_nodes):
        shortest_path_graph = nx.Graph()
        shortest_paths = {}
        for i in range(len(relevant_nodes)):
            for j in range(i + 1, len(relevant_nodes)):
                source = relevant_nodes[i]
                target = relevant_nodes[j]
                try:
                    path = nx.shortest_path(self.graph, source, target, weight='weight')
                    path_length = nx.shortest_path_length(self.graph, source, target, weight='weight')
                    shortest_paths[(source, target)] = {
                        'length': path_length,
                        'path' : path
                    }
                except nx.NetworkXNoPath:
                    shortest_paths[(source, target)] = None
        shortest_path_graph.add_nodes_from(relevant_nodes)
        for (source, target), path_info in shortest_paths.items():
            if path_info is not None:
                edges_in_path = [(path_info['path'][k], path_info['path'][k + 1]) for k in
                                 range(len(path_info['path']) - 1)]
                edge_ids = [self.graph.get_edge_data(u, v).get('id') for u, v in edges_in_path]
                shortest_path_graph.add_edge(source, target, weight=path_info['length'], edge_ids=edge_ids)
                if self.LOG_PATH:
                    self.log_path(source, target, edge_ids)
        return shortest_path_graph

    @function_timer.timed_function
    def log_path(self, source, target, edge_ids):
        Logger().debug(f'Path from {source} to {target}: {edge_ids}')

    @function_timer.timed_function
    def create_mst(self, shortest_path_graph):
        mst = nx.minimum_spanning_tree(shortest_path_graph, weight='weight')
        return mst

    @function_timer.timed_function
    def visualize_mst(self, mst):
        edge_ids = []
        for u, v, data in mst.edges(data=True):
            gotten_edge_ids = data.get('edge_ids')
            edge_ids.append(gotten_edge_ids)
        mst_layer = QgsVectorLayer(f'MultiLineString?crs={self.DESIRED_CRS}',
                       'mst',
                       'memory')
        edge_ids = [item for sublist in edge_ids for item in sublist] # flattening
        edge_ids = list(set(edge_ids)) # make every entry unique. No multiples.
        mst_layer.startEditing()
        provider = mst_layer.dataProvider()
        provider.addAttributes(self.line_layer.fields())
        mst_layer.updateFields()
        source_features = {DhpUtility.get_value_from_field(self.line_layer,
                                                           f,
                                                           "osm_id")
                           : f for f in self.line_layer.getFeatures()}
        filtered_features = [source_features[feature_id] for feature_id in edge_ids if feature_id in source_features]
        for feature in filtered_features:
            new_feature = QgsFeature(mst_layer.fields())
            new_feature.setGeometry(feature.geometry())
            new_feature.setAttributes(feature.attributes())
            provider.addFeatures([new_feature])
        mst_layer.commitChanges()
        mst_layer.updateExtents()
        QgsProject.instance().addMapLayer(mst_layer)

    # ToDo: For testing
    @function_timer.timed_function
    def visualize_subgraph_mst(self, fully_connected_graph, nodes_to_connect):
        subgraph = fully_connected_graph.subgraph(nodes_to_connect)
        self.create_mst(subgraph)
        # self.visualize_mst(subgraph)