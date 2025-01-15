from brkga_mp_ipr.types import BaseChromosome

class ClusteringChromosome(BaseChromosome):
    def __init__(self, value):
        super().__init__(value)
        self.capacity_used = 0.0
        self.constraints_violated = False