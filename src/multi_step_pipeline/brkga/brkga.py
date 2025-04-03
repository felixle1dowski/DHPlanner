from collections import defaultdict

from .clustering_instance import ClusteringInstance
from .clustering_decoder import ClusteringDecoder
from brkga_mp_ipr.types_io import load_configuration
from brkga_mp_ipr.algorithm import BrkgaMpIpr
from brkga_mp_ipr.enums import Sense
from ...util.logger import Logger
from ...util.config import Config
from ...util.results_saver import ResultsSaver
from datetime import datetime
import os
import time
import copy

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
        self.brkga_params.population_size = int(self.instance.get_number_of_nodes() * Config().get_population_factor())
        self.initial_solution = initial_solution
        self.do_warm_start = Config().get_do_warm_start()
        self.timestamp_dict = {}
        self.requested_new_folder = False

    def do_brkga(self):
        brkga = BrkgaMpIpr(
            decoder = self.decoder,
            seed = self.seed,
            sense = self.sense, # Seed.MINIMIZE
            chromosome_size = self.instance.get_number_of_nodes(),
            params = self.brkga_params
        )
        if self.do_warm_start:
            Logger().info("Initializing initial solution with warm start.")
            warm_start_solution = self.get_result_for_chromosome(self.initial_solution)
            warm_start_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
            self.timestamp_dict[-1] = warm_start_time
            Logger().info(f"calculated warm start solution {warm_start_solution}")
            Logger().info(f"Decoded warm start: {self.decoder.decode_chromosome(self.initial_solution)}")
            self.save_result(datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f"), warm_start_solution, -1)
            brkga.set_initial_population([self.initial_solution])
        else:
            Logger().info("Not doing a warm start")
        brkga.initialize()
        Logger().info("Brkga initialized")
        best_result = self.evolve_with_stop_criterion(brkga)
        # brkga.evolve(self.num_generations)
        return best_result

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
        best_result = self.get_result_for_chromosome(brkga.get_best_chromosome())
        best_cost = brkga.get_best_fitness()
        current_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
        Logger().info(f"{current_time} intermediate result: {best_result}")
        self.save_result(current_time, best_result, iteration)
        run = True
        start_time = time.time()
        self.timestamp_dict[iteration] = current_time
        # Evolving:
        Logger().info(f"{datetime.now()} Evolving...")
        while run:
            iteration += 1
            brkga.evolve()
            fitness = brkga.get_best_fitness()
            current_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
            self.timestamp_dict[iteration] = current_time
            if fitness < best_cost:
                update_offset = iteration - last_update_iteration
                if large_offset < update_offset:
                    large_offset = update_offset
                last_update_iteration = iteration
                best_cost = fitness
                best_chromosome = copy.deepcopy(brkga.get_best_chromosome())
                Logger().info("new best chromosome found!")
                best_result = self.get_result_for_chromosome(best_chromosome)
                Logger().info(f"{current_time} intermediate result: {best_result}")
                self.save_result(current_time, best_result, iteration)
            iter_without_improvement = iteration - last_update_iteration
            Logger().info(f"currently {iter_without_improvement} iterations without improvement.")
            if iter_without_improvement >= Config().get_num_generations_to_break():
                break
        total_elapsed_time = time.time() - start_time
        total_num_iterations = iteration
        current_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
        Logger().info(f"{current_time} Total elapsed time: {total_elapsed_time}")
        Logger().info(f"Total number of iterations: {total_num_iterations}")
        self.save_times(self.timestamp_dict)
        self.save_result(current_time, best_result, iteration)
        return best_result

    def save_result(self, timestamp, result_dict, num_generations):
        current_generation = num_generations
        amount_of_clusters = self.decoder.num_clusters
        population_size = self.brkga_params.population_size
        elite_percentage = self.brkga_params.elite_percentage
        mutant_percentage = self.brkga_params.mutants_percentage
        number_of_parents = self.brkga_params.total_parents
        number_of_elite_parents = self.brkga_params.num_elite_parents
        create_new_folder = not self.requested_new_folder
        ResultsSaver.save_result(file_name=f"brkga_generation_{num_generations}",
                                 create_new_folder=create_new_folder,
                                  time=timestamp, random_seed=self.seed,
                                  buildings_observed=self.instance.get_number_of_nodes() - 1,
                                  population_factor=Config().get_population_factor(),
                                  pivot_element=self.decoder.pivot_element,
                                  current_generation=current_generation,
                                  do_warm_start=str(self.do_warm_start),
                                  population_size=population_size,
                                  elite_percentage=elite_percentage,
                                  mutant_percentage=mutant_percentage,
                                  number_of_parents=number_of_parents,
                                  number_of_elite_parents=number_of_elite_parents,
                                  number_of_desired_clusters=amount_of_clusters,
                                  result_dict=result_dict)
        self.requested_new_folder = True

    def save_times(self, timestamp_dict):
        create_new_folder = not self.requested_new_folder
        ResultsSaver.save_result(file_name=f"times_per_generation",
                                 create_new_folder=create_new_folder,
                                 timestamps=timestamp_dict)
        self.requested_new_folder = True