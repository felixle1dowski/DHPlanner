from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from brkga_mp_ipr.types_io import load_configuration
from brkga_mp_ipr.algorithm import BrkgaMpIpr
from brkga_mp_ipr.enums import Sense
from ...util.logger import Logger

class Brkga:

    CONFIG_FILE_PATH = "./config.conf"

    def __init__(self, instance: ClusteringInstance,
                 seed: int,
                 num_generations: int,
                 sense: Sense,
                 decoder: ClusteringDecoder):
        self.instance = instance
        self.decoder = decoder
        self.sense = sense
        self.seed = seed
        self.num_generations = num_generations
        self.brkga_params = load_configuration(self.CONFIG_FILE_PATH)

    def do_brkga(self):
        brkga = BrkgaMpIpr(
            decoder = self.decoder,
            seed = self.seed,
            sense = self.sense, # Seed.MINIMIZE
            chromosome_size = self.instance.get_number_of_nodes(),
            params = self.brkga_params
        )
        brkga.initialize()
        Logger().info("Brkga initialized")
        Logger().info(f"Evolving for {self.num_generations} generations")
        brkga.evolve(self.num_generations)
        best_distance = brkga.get_best_fitness()
        Logger().info(f"best distance sum: {best_distance}")