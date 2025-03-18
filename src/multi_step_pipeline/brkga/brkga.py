from collections import defaultdict

from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from brkga_mp_ipr.types_io import load_configuration
from brkga_mp_ipr.algorithm import BrkgaMpIpr
from brkga_mp_ipr.enums import Sense
from ...util.logger import Logger
import os

class Brkga:

    SCRIPT_DIR = os.path.dirname(__file__)
    CONFIG_FILE_PATH = os.path.join(SCRIPT_DIR, "./config.conf")

    def __init__(self, instance: ClusteringInstance,
                 seed: int,
                 num_generations: int,
                 sense: Sense,
                 decoder: ClusteringDecoder,
                 initial_solution: list):
        self.instance = instance
        self.decoder = decoder
        self.sense = sense
        self.seed = seed
        self.num_generations = num_generations
        self.brkga_params, _ = load_configuration(self.CONFIG_FILE_PATH)
        self.initial_solution = initial_solution

    def do_brkga(self):
        brkga = BrkgaMpIpr(
            decoder = self.decoder,
            seed = self.seed,
            sense = self.sense, # Seed.MINIMIZE
            chromosome_size = self.instance.get_number_of_nodes(),
            params = self.brkga_params
        )
        brkga.set_initial_population([self.initial_solution])
        brkga.initialize()
        Logger().info("Brkga initialized")
        Logger().info(f"Evolving for {self.num_generations} generations")
        brkga.evolve(self.num_generations)
        best_distance = brkga.get_best_fitness()
        Logger().info(f"best distance sum: {best_distance}")
        end_result = self.get_result_for_chromosome(brkga.get_best_chromosome())
        Logger().info(f"end result brkga: {end_result}")
        return end_result

    def get_result_for_chromosome(self, chromosome):
        """Only used for end result."""
        end_result = self.decoder.decode_end_result(chromosome)
        return end_result
