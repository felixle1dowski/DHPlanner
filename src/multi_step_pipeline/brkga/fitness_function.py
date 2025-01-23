from collections import defaultdict

import networkx as nx

from ...util.dhp_utility import DhpUtility


class FitnessFunction:

    def __init__(self, complete_graph, mst_creator):
        self.complete_graph = complete_graph
        self.mst = mst_creator

    def compute_fitness(self, id_subset, cluster_center_id):
        subset_graph = self.build_subset_graph(id_subset, cluster_center_id)
        mst = self.mst(subset_graph)
        tree = self.extract_tree(mst, cluster_center_id)
        pipe_cost = self.compute_pipe_cost(tree)

    def build_subset_graph(self, id_subset: list, cluster_center_id):
        subset_graph = self.complete_graph.subgraph(id_subset)
        return subset_graph

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
                tree.add_edge(parent, node, weight=weight)
            for neighbor in mst.neighbors(node):
                if neighbor not in visited:
                    dfs(neighbor, node)
        dfs(root)
        return tree

    def compute_pipe_cost(self, tree):
        # ToDo: This is only temporary.
        # ToDo: Calculate Diameter by finding longest path.
        # for now only returns the distance as a cost.
        costs = []
        pipe_dict = defaultdict(dict)
        for u, v, data in tree.edges(data=True):
            pipe_dict[(u, v)] = {
                "length" : data['weight'],
                "diameter" : self.compute_diameter()
            }
            costs.append(data['weight'])
        return sum(costs), pipe_dict

    def compute_trenching_cost(self, pipe_dict):
        trenching_costs = []
        for pair, inner_dict in pipe_dict.items():
            length = inner_dict['length']
            diameter = inner_dict['diameter']
            trenching_costs.append(self.calculate_trench_cost(length, diameter))

    # ToDo: Still to be done!
    def compute_diameter(self):
        return 0

    # ToDo: Still to be done!
    def calculate_trench_cost(self, length, diameter):
        return 0


