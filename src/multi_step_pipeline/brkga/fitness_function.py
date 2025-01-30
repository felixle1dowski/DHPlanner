from collections import defaultdict
from ...util.config import Config

import networkx as nx

from .clustering_instance import ClusteringInstance

from ...util.dhp_utility import DhpUtility


class FitnessFunction:

    def __init__(self, instance: ClusteringInstance, id_to_node_translation_dict):
        # ToDo: Also pass dict - id: street-type-multiplicator
        self.instance = instance
        self.buildings_to_point_dict = id_to_node_translation_dict
        self.points_to_building_dict = {value: key for key, value in id_to_node_translation_dict.items()}
        self.fixed_cost = Config().get_fixed_cost()

    def compute_fitness_for_all(self, cluster_dict):
        fitness_scores = []
        for cluster_center_id, members in cluster_dict.items():
            if cluster_center_id != "-1":
                members.append(cluster_center_id)
                fitness = self.compute_fitness(members,
                                           cluster_center_id)
                fitness_scores.append(fitness)
        sum_of_fitness = sum(fitness_scores)
        return sum_of_fitness

    def compute_fitness(self, id_subset : list, cluster_center_id):
        subset_graph = self.instance.get_subgraph(id_subset)
        mst = self.create_mst(subset_graph)
        tree = self.extract_tree(mst, self.buildings_to_point_dict[cluster_center_id])

        # ToDo: This does not really make sense
        # pipe_cost = self.compute_pipe_cost(tree)

        # ToDo: Do it like this:
        pipes = self.pipes_to_construct(tree)
        pipe_cost = self.calculate_pipe_cost(pipes)
        trenching_cost = self.calculate_trenching_cost(pipes)
        variable_cost = pipe_cost + trenching_cost

        # ToDo: be careful!! cluster center id_subset needs to contain cluster center!!
        fitness = self.instance.get_point_demands(id_subset) / (self.fixed_cost + variable_cost)
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

    def pipes_to_construct(self, network_tree):
        pipes = []
        for u, v, data in network_tree.edges(data=True):
            pipe = {
                'id': data['edge_ids'],
                'length': data['weight'],
                'diameter': self.compute_diameter(data['weight'])} # is this all that is needed?
            pipes.append(pipe)
        return pipes

    # ToDo: Still to be done!
    def compute_diameter(self, length_of_pipe):
        return 0

    # ToDo: Still to be done!
    def calculate_trenching_cost(self, pipe_list):
        trenching_cost = 0
        for pipe in pipe_list:
            connection_id = pipe['id']
            # street_type_factor = self.street_type_factors[connection_id]
            street_type_factor = 1.0
            length = pipe['length']
            diameter = pipe['diameter']
            trench_cost = self.calculate_trench_cost(float(length), float(diameter), street_type_factor)
            trenching_cost += trench_cost
        return trenching_cost

    def calculate_pipe_cost(self, pipe_list):
        # ToDo: Implement properly.
        pipe_length = 0
        pipe_lengths = [float(pipe['length']) for pipe in pipe_list]
        return sum(pipe_lengths)

    def calculate_trench_cost(self, length, diameter, street_type_factor):
        return 0



