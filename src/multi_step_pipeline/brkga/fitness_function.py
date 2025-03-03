from collections import defaultdict
from ...util.config import Config

import networkx as nx
import pandas as pd

from .clustering_instance import ClusteringInstance
from ...util.dhp_utility import DhpUtility

from ...util.logger import Logger


class FitnessFunction:

    DEMAND_FIELD = "peak_demand"
    MASS_FLOW_COL_NAME = "Volumenstrom"
    PRESSURE_LOSS_THRESHOLD = 250

    def __init__(self, instance: ClusteringInstance, id_to_node_translation_dict, pipe_diameter_catalogue, pipe_prices, mass_flow_dict):
        # ToDo: Also pass dict - id: street-type-multiplicator
        self.instance = instance
        self.buildings_to_point_dict = id_to_node_translation_dict
        self.points_to_building_dict = {value: key for key, value in id_to_node_translation_dict.items()}
        self.fixed_cost = Config().get_fixed_cost()
        self.pipe_diameter_catalogue = pipe_diameter_catalogue
        self.pipe_prices = pipe_prices
        self.mass_flow_dict = mass_flow_dict

    def compute_fitness_for_all(self, cluster_dict):
        fitness_scores = []
        for cluster_center_id, members in cluster_dict.items():
            if cluster_center_id != "-1":
                members.append(cluster_center_id)
                fitness = self.compute_fitness(members,
                                           cluster_center_id)
                fitness_scores.append(fitness)
        sum_of_fitness = sum(fitness_scores)
        Logger().debug(f"fitness for permutation calculated: {sum_of_fitness}")
        return sum_of_fitness

    def compute_fitness(self, id_subset : list, cluster_center_id):
        Logger().debug(f"Calculating fitness for {id_subset} with {cluster_center_id} as it's cluster center.")
        subset_graph = self.instance.get_subgraph(id_subset)
        mst = self.create_mst(subset_graph)
        tree = self.extract_tree(mst, self.buildings_to_point_dict[cluster_center_id])

        pipe_mass_flows = self.calculate_cumulative_mass_flows(tree, self.buildings_to_point_dict[cluster_center_id])

        Logger().debug(f"pipe flows calculated: {pipe_mass_flows}")
        pipes = self.pipes_to_construct(tree, pipe_mass_flows)
        pipe_cost = self.calculate_pipe_cost(pipes)

        # ToDo: be careful!! cluster center id_subset needs to contain cluster center!!
        fitness = self.instance.get_point_demands(id_subset) / (self.fixed_cost + pipe_cost)
        Logger().debug(f"fitness calculated for {id_subset} with cluster center {cluster_center_id}: {fitness}")
        return fitness

    def create_mst(self, subset_graph):
        mst = nx.minimum_spanning_tree(subset_graph, weight='weight')
        return mst

    def extract_tree(self, mst, root):
        # We have to make the graph into a tree with a root so that we can
        # calculate the pipe diameters later on.
        root = root
        tree = nx.DiGraph()
        visited = set()

        def dfs(node, parent=None):
            visited.add(node)
            if parent is not None:
                weight = mst.edges[parent, node]['weight']
                edge_ids = mst.edges[parent, node]['edge_ids']
                tree.add_edge(parent, node, weight=weight, edge_ids=edge_ids)
            for neighbor in mst.neighbors(node):
                if neighbor not in visited:
                    dfs(neighbor, node)
        dfs(root)
        return tree

    def calculate_cumulative_mass_flows(self, tree, heat_source_node):
        mass_flows = self.mass_flow_dict.copy()
        for node in nx.dfs_postorder_nodes(tree, source=heat_source_node):
            for child in tree.successors(node):
                mass_flows[self.points_to_building_dict[child]] += float(mass_flows[self.points_to_building_dict[child]])
        edge_demands = {}
        for u, v in tree.edges():
            edge_demands[(u, v)] = float(mass_flows[self.points_to_building_dict[v]])
        return edge_demands

    def pipes_to_construct(self, network_tree, cumulative_mass_flows):
        pipes = []
        for u, v, data in network_tree.edges(data=True):
            Logger().debug(f"creating pipe from {self.points_to_building_dict[u]} to {self.points_to_building_dict[v]}")
            pipe = {
                'id': data['edge_ids'],
                'length': data['weight'],
                'pipe_type': self.compute_pipe_type(cumulative_mass_flows[(u, v)])}
            pipes.append(pipe)
        return pipes

    # ToDo: This should probably go into the catalogue class, right?
    def compute_pipe_type(self, mass_flow):
        Logger().debug(f"computing pipe type for {mass_flow}")
        pdf = self.pipe_diameter_catalogue
        filtered_pdf = pdf[pdf[self.MASS_FLOW_COL_NAME] >= mass_flow]
        if filtered_pdf.empty:
            Logger().error(f"No valid mass flow found for {mass_flow}")
            return None
        first_to_undershoot_threshold = filtered_pdf.iloc[0,:]
        # We're skipping the first column, since that's the mass flow column.
        pipe_columns = [col for col in pdf.columns if col != self.MASS_FLOW_COL_NAME]
        selected_column = None
        pipe_type = None
        for col in pipe_columns:
            if pd.notna(first_to_undershoot_threshold[col]) and float(first_to_undershoot_threshold[col]) < self.PRESSURE_LOSS_THRESHOLD:
                selected_column = col
                pipe_type = self.pipe_prices[selected_column]
                Logger().debug(f"Calculated pipe type for {mass_flow}: {pipe_type}")
                break
        if pipe_type is None:
            Logger().error(f"No valid mass flow found for {mass_flow}")
            # ToDo: Raise Exception!
        return pipe_type

    def calculate_pipe_cost(self, pipe_list):
        pipe_costs = 0
        for pipe in pipe_list:
            pipe_cost = self.calculate_single_pipe_cost(pipe)
            pipe_costs += pipe_cost
        Logger().debug(f"Pipe cost calculated: {pipe_costs}")
        return pipe_costs

    def calculate_single_pipe_cost(self, pipe):
        pipe_cost = 0
        trench_cost = 0
        pipe_cost = self.calculate_single_pipe_investment_cost(pipe)
        trench_cost = self.calculate_single_trench_cost(pipe)
        return pipe_cost + trench_cost

    def calculate_single_pipe_investment_cost(self, pipe):
        length = float(pipe['length'])
        type = pipe['pipe_type']
        cost_per_m = float(type['price'])
        cost = length * cost_per_m
        Logger().debug(f"calculated cost for pipe with length {length} and type {type} : {cost}")
        return cost

    def calculate_single_trench_cost(self, pipe):
        return 0


    ###### ToDo: Still needed???

    # def extract_paths(self, network_tree, root_id):
    #     root = self.buildings_to_point_dict[root_id]
    #     leaves = [node for node in network_tree.nodes if network_tree.out_degree(node) == 0]
    #     all_paths = []
    #     for leaf in leaves:
    #         paths = nx.all_simple_paths(network_tree, root, leaf)
    #         all_paths.extend(paths)
    #     return all_paths
    #
    # def calculate_critical_path_length(self, paths, network_tree):
    #     max_length = 0
    #     longest_path = None
    #     for path in paths:
    #         path_length = self.calculate_path_length(path, network_tree)
    #         if path_length > max_length:
    #             max_length = path_length
    #             longest_path = path
    #     return max_length, longest_path
    #
    # def calculate_maximum_pressure_gradient(self, critical_path_length):
    #     max_pressure_gradient = self.MAX_PRESSURE_DROP_IN_BAR / critical_path_length
    #     return max_pressure_gradient
    #
    # def calculate_minimum_diameter(self, path, network_tree, max_pressure_gradient):
    #     # ToDo: available_pipes have to be sorted by diameter
    #     mass_flow = self.calculate_mass_flow(path, network_tree)
    #     # ToDo: Create Lookup Dataframe
    #     pressure_gradient, diameter = self.look_up_minimum_pipe_diameter(mass_flow, max_pressure_gradient)
    #     if pressure_gradient > max_pressure_gradient:
    #         raise Exception("No diameter available that does not violate maximum pressure gradient constraint.")
    #
    # def calculate_path_length(self, path, network_tree):
    #     path_length = 0
    #     for i in range(len(path) - 1):
    #         u, v = path[i], path[i + 1]
    #         path_length += network_tree.edges[u][v]['weight']
    #     return path_length
    #
    # # ToDo: Still to be done!
    # def calculate_trenching_cost(self, pipe_list):
    #     trenching_cost = 0
    #     for pipe in pipe_list:
    #         connection_id = pipe['id']
    #         # street_type_factor = self.street_type_factors[connection_id]
    #         street_type_factor = 1.0
    #         length = pipe['length']
    #         diameter = pipe['diameter']
    #         trench_cost = self.calculate_trench_cost(float(length), float(diameter), street_type_factor)
    #         trenching_cost += trench_cost
    #     return trenching_cost
    #
    #
    # def calculate_trench_cost(self, length, diameter, street_type_factor):
    #     return 0
    #
    # def look_up_minimum_pipe_diameter(self, mass_flow, max_pressure_gradient):
    #     pass