import networkx as nx

class FitnessFunction:

    def __init__(self, complete_graph, mst_creator):
        self.complete_graph = complete_graph
        self.mst = mst_creator

    def build_subset_graph(self, id_subset: list):
        self.complete_graph.subgraph(id_subset)
        pass

    def create_mst(self):
        pass

    def compute_pipe_cost(self):
        pass

    def compute_trenching_cost(self):
        pass

    def compute_fitness(self):
        pass

