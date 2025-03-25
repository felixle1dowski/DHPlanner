import networkx as nx

from ..util import function_timer
from ..util.logger import Logger
from ..util.dhp_utility import DhpUtility
from ..util.function_timer import FunctionTimer
from ..util.config import Config
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsFeature, QgsProject, QgsPointXY
from time import gmtime, strftime
import json


class ShortestPathGraphCreator:
    graph_creator_result = None
    relevant_nodes = None
    graph = None
    building_centroids = None
    line_layer = None
    access_point_lines = None
    LOG_PATH = True
    exploded_roads = None
    DESIRED_CRS = QgsCoordinateReferenceSystem('EPSG:4839')
    function_timer = FunctionTimer()

    ROAD_ID_FIELD_NAME = "osm_id"
    ROAD_DISTANCE_FIELD_NAME = "length"
    ROAD_TYPE_FIELD_NAME = "fclass"

    def __init__(self):
        pass


    @function_timer.timed_function
    def set_required_fields(self, graph, line_layer, relevant_nodes, exploded_roads):
        self.graph = graph
        self.line_layer = line_layer
        self.relevant_nodes = relevant_nodes
        self.exploded_roads = exploded_roads

    @function_timer.timed_function
    def start(self):
        if not Config().get_load_graph():
            is_custom_weight_calculation_necessary = self.is_custom_weight_calculation_necessary()
            shortest_path_graph = self.construct_shortest_paths_graph(self.relevant_nodes, is_custom_weight_calculation_necessary)
            if Config().get_save_graph():
                serialized_graph = self.serialize_graph(shortest_path_graph)
                file_name = Config().get_saved_graph_path()
                with open(file_name, "w") as f:
                    json.dump(serialized_graph, f, indent=2)
                Logger().info("succesfully saved shortest path graph!")
        else:
            with open(Config().get_saved_graph_path(), "r") as f:
                serialized_graph = json.load(f)
                shortest_path_graph = self.deserialize_graph(serialized_graph)
                Logger().info("successfully loaded shortest path graph from file system.")
        mst = self.create_mst(shortest_path_graph)
        self.visualize_mst(mst)
        return shortest_path_graph

    def serialize_point_xy(self, point):
        if type(point).__name__ == "QgsPointXY":
            return {"x": point.x(), "y": point.y()}
        return point

    def deserialize_point_xy(self, data):
        if isinstance(data, dict) and "x" in data and "y" in data:
            return QgsPointXY(data["x"], data["y"])
        return data

    def serialize_graph(self, graph):
        serialized_graph = {
            "nodes": [],
            "edges": []
        }
        for node, attribute in graph.nodes(data=True):
            serialized_graph["nodes"].append(self.serialize_point_xy(node))

        for u, v, attributes in graph.edges(data=True):
            serialized_edge = {"source": self.serialize_point_xy(u), "target": self.serialize_point_xy(v)}
            for key, value in attributes.items():
                serialized_edge[key] = self.serialize_point_xy(value)
            serialized_graph["edges"].append(serialized_edge)
        return serialized_graph

    def deserialize_graph(self, serialized_graph):
        graph = nx.Graph()
        for node_data in serialized_graph["nodes"]:
            deserialized_point = self.deserialize_point_xy(node_data)
            graph.add_node(deserialized_point)
        for edge_data in serialized_graph["edges"]:
            source = self.deserialize_point_xy(edge_data.pop("source"))
            target = self.deserialize_point_xy(edge_data.pop("target"))
            attributes = {key: self.deserialize_point_xy(value) for key, value in edge_data.items()}
            graph.add_edge(source, target, **attributes)
        return graph

    @function_timer.timed_function
    def construct_shortest_paths_graph(self, relevant_nodes, is_custom_weight_calculation_necessary):
        shortest_path_graph = nx.Graph()
        shortest_paths = {}
        for i in range(len(relevant_nodes)):
            for j in range(i + 1, len(relevant_nodes)):
                source = relevant_nodes[i]
                target = relevant_nodes[j]
                Logger().debug(f"finding the shortest path from {source} to {target}")
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
                shortest_path_graph.add_edge(source, target, weight=path_info['length'], edge_ids=edge_ids,
                                             street_type_cost_factor=self.calculate_street_type_cost_factor(edge_ids,
                                                                                                            is_custom_weight_calculation_necessary))
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

    def calculate_street_type_cost_factor(self, edge_ids, is_custom_weight_calculation_necessary):
        default_factor = 1.0
        if not is_custom_weight_calculation_necessary:
            Logger().debug(f"no custom weight calculation necessary for {edge_ids}. Using {default_factor}.")
            return default_factor
        factor_sum = 0.0
        distance_sum = 0.0
        for edge_id in edge_ids:
            if not edge_id:
                Logger().warning(
                    f'No street type cost factor for empty edge_id list found. Setting default value of {default_factor}')
                return default_factor
            multiplication_distances = []
            length = DhpUtility.get_value_from_feature_by_id_field(self.exploded_roads,
                                                                   self.ROAD_ID_FIELD_NAME,
                                                                   edge_id,
                                                                   self.ROAD_DISTANCE_FIELD_NAME)
            road_type = DhpUtility.get_value_from_feature_by_id_field(self.exploded_roads,
                                                                      self.ROAD_ID_FIELD_NAME,
                                                                      edge_id,
                                                                      self.ROAD_TYPE_FIELD_NAME)
            road_type_factor = Config().get_specific_street_type_multiplier(road_type)
            if not road_type_factor:
                road_type_factor = 1.0
                Logger().warning(f"No street type multiplier found for road_id {edge_id}, searched road type "
                                 f" was {road_type},"
                                 f"Setting road type factor "
                                 f"to default value of {default_factor}")
            multiplication_distances.append((road_type_factor, length))
            factor_sum += road_type_factor * length
            distance_sum += length
        if distance_sum == 0:
            Logger().warning(f"found distance sum of 0 for ids: {edge_ids}. Returning default value.")
            return default_factor
        cumulated_factor = factor_sum / distance_sum
        Logger().debug(
            f'added street type cost factor to road for {edge_ids}, with factor_sum of {factor_sum} and a'
            f'distance sum of {distance_sum}. Result is {cumulated_factor}')
        return cumulated_factor

    def get_adjacency_matrix_with_custom_weights(self, shortest_path_graph):
        new_graph = shortest_path_graph.copy()
        for u, v, data in new_graph.edges(data=True):
            previous_weight = data['weight']
            new_weight = data['weight'] * new_graph[u][v]['street_type_cost_factor']
            new_graph.edges[u, v]['weight'] = new_weight
            Logger().debug(f"New custom weight for path between {u} and {v} is {new_weight}, was {previous_weight}")
        adjacency_matrix = nx.adjacency_matrix(new_graph).todense()
        return adjacency_matrix

    def is_custom_weight_calculation_necessary(self):
        all_street_type_entries = Config().get_street_type_multipliers()
        all_multipliers = [multiplier for fclass, multiplier in all_street_type_entries.items()]
        custom_weight_calculation_necessary = any(multiplier != 1.0 for multiplier in all_multipliers)
        Logger().debug(f"Is a custom weight calculation necessary? {custom_weight_calculation_necessary}.")
        return custom_weight_calculation_necessary