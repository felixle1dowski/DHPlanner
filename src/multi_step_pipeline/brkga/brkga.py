from collections import defaultdict

from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from brkga_mp_ipr.types_io import load_configuration
from brkga_mp_ipr.algorithm import BrkgaMpIpr
from brkga_mp_ipr.enums import Sense
from ...util.logger import Logger
from datetime import datetime
import os
import time

class Brkga:

    SCRIPT_DIR = os.path.dirname(__file__)
    CONFIG_FILE_PATH = os.path.join(SCRIPT_DIR, "./config.conf")
    N_ITERATIONS_WITHOUT_IMPROVEMENT = 20

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
        best_chromosome = self.evolve_with_stop_criterion(brkga)

        # brkga.evolve(self.num_generations)

        best_distance = brkga.get_best_fitness()
        Logger().info(f"best distance sum: {best_distance}")
        end_result = self.get_result_for_chromosome(best_chromosome)
        Logger().info(f"end result brkga: {end_result}")
        return end_result

    def get_result_for_chromosome(self, chromosome):
        """Only used for end result."""
        end_result = self.decoder.decode_end_result(chromosome)
        return end_result

    def evolve_with_stop_criterion(self, brkga, stop_criterion="improvement"):
        Logger().info("Evolving with stop criterion")
        Logger().info(f"Started Evolving at: {datetime.now()}")
        Logger().info(f"Stopping criterion: {stop_criterion}")

        # Warm Start:
        iteration = 0
        last_update_iteration = 0
        large_offset = 0
        Logger().info(f"{datetime.now()} Warm Start...")
        Logger().info(f"{iteration}")
        warm_start_result = self.get_result_for_chromosome(brkga.get_best_chromosome())
        best_cost = brkga.get_best_fitness()
        best_chromosome =brkga.get_best_chromosome()
        Logger().info(f"{datetime.now()} intermediate result: {warm_start_result}")

        run = True
        start_time = time.time()
        # Evolving:
        Logger().info(f"{datetime.now()} Evolving...")
        while run:
            iteration += 1
            brkga.evolve()
            fitness = brkga.get_best_fitness()
            if fitness < best_cost:
                update_offset = iteration - last_update_iteration
                if large_offset < update_offset:
                    large_offset = update_offset
                last_update_iteration = iteration
                best_cost = fitness
                best_chromosome = brkga.get_best_chromosome()
                Logger().info("new best chromosome found!")
                intermediate_result = self.get_result_for_chromosome(best_chromosome)
                Logger().info(f"{datetime.now()} intermediate result: {intermediate_result}")
            iter_without_improvement = iteration - last_update_iteration
            Logger().info(f"currently {iter_without_improvement} iterations without improvement.")
            if iter_without_improvement >= self.N_ITERATIONS_WITHOUT_IMPROVEMENT:
                break
        total_elapsed_time = time.time() - start_time
        total_num_iterations = iteration
        Logger().info(f"{datetime.now()} Total elapsed time: {total_elapsed_time}")
        Logger().info(f"Total number of iterations: {total_num_iterations}")
        return best_chromosome
