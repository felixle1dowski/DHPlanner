from collections import defaultdict
from ...util.config import Config
from .mass_flow_calculation import MassFlowCalculation as mfc

import networkx as nx
import pandas as pd

from .clustering_instance import ClusteringInstance
from ...util.dhp_utility import DhpUtility

from ...util.logger import Logger


class FitnessFunction:

    DEMAND_FIELD = "peak_demand"
    MASS_FLOW_COL_NAME = "Volumenstrom"
    PRESSURE_LOSS_THRESHOLD = 250

    def __init__(self, instance: ClusteringInstance, id_to_node_translation_dict, pipe_diameter_catalogue, pipe_prices):
        # ToDo: Also pass dict - id: street-type-multiplicator
        self.instance = instance
        self.buildings_to_point_dict = id_to_node_translation_dict
        self.points_to_building_dict = {value: key for key, value in id_to_node_translation_dict.items()}
        self.fixed_cost = Config().get_fixed_cost()
        self.pipe_diameter_catalogue = pipe_diameter_catalogue
        self.pipe_prices = pipe_prices

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
        number_of_consumers = defaultdict(lambda: 1)
        cumulative_demands = self.instance.demands.copy()
        cumulative_demands = {key: float(value) for key, value in cumulative_demands.items()}
        for node in nx.dfs_postorder_nodes(tree, source=heat_source_node):
            for child in tree.successors(node):
                number_of_consumers[self.points_to_building_dict[node]] += number_of_consumers[self.points_to_building_dict[child]]
                cumulative_demands[self.points_to_building_dict[node]] += cumulative_demands[self.points_to_building_dict[child]]
        pipe_mass_flows = {}
        for u, v in tree.edges():
            simultaneity_factor = self.calculate_simultaneity_factor(number_of_consumers[self.points_to_building_dict[v]])
            demand = cumulative_demands[self.points_to_building_dict[v]] * simultaneity_factor
            mass_flow = mfc.calculate_mass_flow(demand)
            pipe_mass_flows[(u, v)] = mass_flow
        Logger().debug(f"pipe_mass_flows: {pipe_mass_flows}")
        return pipe_mass_flows

    def calculate_simultaneity_factor(self, number_of_consumers):
        # values from Winter (2001)
        a = 0.449677646267461
        b = 0.551234688
        c = 53.84382392
        d = 1.762743268
        inner_calc = pow((number_of_consumers / c), d)
        sf = a + (b / (1 + inner_calc))
        return sf

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
        pressure_loss_threshold = 250
        pdf = self.pipe_diameter_catalogue
        filtered_pdf = pdf[pdf[self.MASS_FLOW_COL_NAME] >= mass_flow]
        if filtered_pdf.empty:
            Logger().error(f"No valid mass flow found for {mass_flow}")
            return None
        first_to_undershoot_threshold = filtered_pdf.iloc[0,:]
        multiple_values = filtered_pdf[filtered_pdf[self.MASS_FLOW_COL_NAME] == first_to_undershoot_threshold[self.MASS_FLOW_COL_NAME]]
        # We're skipping the first column, since that's the mass flow column.
        pipe_columns = [col for col in pdf.columns if col != self.MASS_FLOW_COL_NAME]
        pipe_type = None
        for row in multiple_values.iterrows():
            value_found = False
            for col in pipe_columns:
                if pd.notna(row[1][col]) and float(
                        row[1][col]) < pressure_loss_threshold:
                    selected_column = col
                    pipe_type = self.pipe_prices[selected_column]
                    value_found = True
                    break
            if value_found:
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