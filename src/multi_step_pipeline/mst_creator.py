import networkx as nx
from ..util.logger import Logger
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsFeature, QgsProject

class MSTCreator:
    graph_creator_result = None
    street_graph = None
    building_centroids = None
    exploded_roads = None
    access_point_lines = None
    LOG_PATH = False
    DESIRED_CRS = QgsCoordinateReferenceSystem('EPSG:4839')

    def __init__(self):
        pass

    def set_graph_creator_result(self, graph_creator_result):
        self.graph_creator_result = graph_creator_result
        self.street_graph = graph_creator_result.street_graph
        self.building_centroids = graph_creator_result.building_centroids
        self.exploded_roads = graph_creator_result.exploded_roads
        self.access_point_lines = graph_creator_result.access_point_lines

    def start(self):
        ap_nodes = self.__find_ap_nodes()
        shortest_path_graph = self.__construct_shortest_paths_graph(ap_nodes)
        mst = self.__create_mst(shortest_path_graph)
        self.__visualize_mst(mst)

    def __find_ap_nodes(self):
        nodes = []
        nodes_from_graph = self.street_graph.nodes
        for node in nodes_from_graph:
            node_info = self.street_graph.nodes[node]
            if node_info['has_ap']:
                nodes.append(node)
        return nodes

    def __construct_shortest_paths_graph(self, ap_nodes):
        shortest_path_graph = nx.Graph()
        shortest_paths = {}
        for i in range(len(ap_nodes)):
            for j in range(i + 1, len(ap_nodes)):
                source = ap_nodes[i]
                target = ap_nodes[j]
                try:
                    path = nx.shortest_path(self.street_graph, source, target, weight='weight')
                    path_length = nx.shortest_path_length(self.street_graph, source, target, weight='weight')
                    shortest_paths[(source, target)] = {
                        'length': path_length,
                        'path' : path
                    }
                except nx.NetworkXNoPath:
                    shortest_paths[(source, target)] = None
        shortest_path_graph.add_nodes_from(ap_nodes)
        for (source, target), path_info in shortest_paths.items():
            if path_info is not None:
                edges_in_path = [(path_info['path'][k], path_info['path'][k + 1]) for k in
                                 range(len(path_info['path']) - 1)]
                edge_ids = [self.street_graph.get_edge_data(u, v).get('id') for u, v in edges_in_path]
                shortest_path_graph.add_edge(source, target, weight=path_info['length'], edge_ids=edge_ids)
                if self.LOG_PATH:
                    self.__log_path(source, target, edge_ids)
        return shortest_path_graph

    def __log_path(self, source, target, edge_ids):
        Logger().debug(f'Path from {source} to {target}: {edge_ids}')

    def __create_mst(self, shortest_path_graph):
        mst = nx.minimum_spanning_tree(shortest_path_graph, weight='weight')
        return mst

    def __visualize_mst(self, mst):
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
        provider.addAttributes(self.exploded_roads.fields())
        mst_layer.updateFields()
        source_features = {f.id(): f for f in self.exploded_roads.getFeatures()}
        filtered_features = [source_features[feature_id] for feature_id in edge_ids if feature_id in source_features]
        for feature in filtered_features:
            new_feature = QgsFeature(mst_layer.fields())
            new_feature.setGeometry(feature.geometry())
            new_feature.setAttributes(feature.attributes())
            provider.addFeatures([new_feature])
        mst_layer.commitChanges()
        mst_layer.updateExtents()
        QgsProject.instance().addMapLayer(mst_layer)