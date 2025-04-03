from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
from .config_exception import ConfigException
from qgis.core import QgsCoordinateReferenceSystem
from datetime import datetime

import os

class Config:

    REQUIRED_FIELDS = ["buildings-layer-name", "roads-layer-name",
                       "selection-layer-name", "heat-demands-layer-name",
                       "installation-strategy", "street-type-multipliers", "insulation-factor",
                       "log-level", "method", "crs", "distance-measuring-method", "fixed-cost", "pivot-strategy",
                       "save-graph", "load-graph", "graph-file-name", "decrease-max-clusters-to-find-pctg",
                       "num-generations-to-break", "population-factor", "eps", "life-time-in-years"]
    SCRIPT_DIR = os.path.dirname(__file__)
    # config file has to be placed in plugin folder!
    CONFIG_FILE_PATH = os.path.join(SCRIPT_DIR, "../../config.yaml")
    DEBUG_FOLDER = os.path.join(SCRIPT_DIR, "../../debug/")
    SAVED_GRAPHS_FOLDER = os.path.join(SCRIPT_DIR, "../../saved_graphs/")
    _instance = None
    config = None
    created_results_subfolder = False
    results_folder_path = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            stream = open(self.CONFIG_FILE_PATH, 'r')
            self.config = load(stream, Loader=Loader)
            stream.close()
            self._initialized = True
            self.config_validation()

    def get_config(self):
        return self.config

    def config_validation(self):
        for field in self.REQUIRED_FIELDS:
            if field not in self.config:
                raise ConfigException(f"{field} is required in config.yaml.")
        if self.config.get("installation-strategy") not in ["greenfield", "street-following", "adjacent"]:
            raise ConfigException("Installation Strategy is not valid.")
        if self.config.get("log-level") not in ["debug", "info", "warning", "error", "critical"]:
            raise ConfigException("Log Level is not valid.")
        if self.config.get("method") not in ["one-step", "multi-step"]:
            raise ConfigException("Method is not valid.")
        # data_folder_path = Path(self.config.get("data-folder"))
        # if not data_folder_path.is_dir():
        #     raise ConfigException(f"Data Folder {data_folder_path} is not valid.")
        # roads_file_path = data_folder_path / self.config.get("roads-file-name")
        # ToDo: Add back in, once we're using files, not layers.
        # if not roads_file_path.is_file():
        #     raise ConfigException(f"Roads File {roads_file_path} is not valid.")
        # buildings_file_path = data_folder_path / self.config.get("buildings-file-name")
        # if not buildings_file_path.is_file():
        #     raise ConfigException(f"Buildings File {buildings_file_path} is not valid.")
        if self.config.get("insulation-factor") < 0:
            raise ConfigException(f"Insulation factor is not valid. Needs to be greater than or equal to 0. "
                                  f"but is: {self.config.get('insulation-factor')}")
        if self.config.get("save-graph") not in ["True", "False"]:
            raise ConfigException(f"Invalid entry for save-graph! has to be 'True' or 'False' is "
                                  f"{self.config.get('save-graph')}")
        if self.config.get("eps") <= 0.0:
            raise ConfigException(f"Eps is invalid. Needs to be greater than or equal to 0. But is {self.config.get('eps')}")

    def get_selection_layer_name(self):
        return self.config.get("selection-layer-name")

    def get_installation_strategy(self):
        return self.config.get("installation-strategy")

    def get_log_level(self):
        return self.config.get("log-level")

    def get_method(self):
        return self.config.get("method")

    # ToDo: Add back in
    # def get_roads_path(self):
    #     return Path(self.config.get("data-folder")) / self.config.get("roads-file-name")
    #
    # ToDo: Add back in
    # def get_buildings_path(self):
    #     return Path(self.config.get("data-folder")) / self.config.get("buildings-file-name")

    def get_logger_path_name(self):
        return self.config.get("logger-path-name")

    def get_roads_layer_name(self):
        return self.config.get("roads-layer-name")

    def get_buildings_layer_name(self):
        return self.config.get("buildings-layer-name")

    def get_heat_demands_layer_name(self):
        return self.config.get("heat-demands-layer-name")

    def get_crs(self):
        return QgsCoordinateReferenceSystem('EPSG:4839')

    def get_debug_folder_path(self):
        return self.DEBUG_FOLDER

    def get_load_factor(self, building_type):
        building_type_string = str(building_type)
        if building_type_string == "NULL":
            building_type_string = "NULL_replacement"
        conversion_type = self.config["building-type-conversion"].get(building_type_string, building_type_string)
        load_profile = self.config["load-profile-factors"].get(conversion_type, None)
        return load_profile

    def get_excluded_road_fclasses(self):
        result = []
        for entry in self.config["excluded-road-fclasses"]:
            result.append(entry)
        return result

    def get_heat_capacity(self):
        return self.config.get("heat-capacity")

    def get_minimum_heat_capacity_exhaustion(self):
        return self.config.get("minimum-heat-capacity-exhaustion")

    def get_minimum_heat_capacity_exhaustion_as_decimal(self):
        return self.config.get("minimum-heat-capacity-exhaustion") / 100

    def get_distance_measuring_method(self):
        return self.config.get("distance-measuring-method")

    def get_fixed_cost(self):
        return float(self.config.get("fixed-cost"))

    def get_pivot_strategy(self):
        return self.config.get("pivot-strategy")

    def get_street_type_multipliers(self):
        return self.config.get("street-type-multipliers")

    def get_specific_street_type_multiplier(self, fclass):
        try:
            multiplier = float(self.config.get("street-type-multipliers")[fclass])
            return multiplier
        except KeyError:
            return None

    def get_insulation_factor(self):
        return self.config.get("insulation-factor")

    def get_saved_graphs_folder(self):
        return self.SAVED_GRAPHS_FOLDER

    def get_saved_graph_path(self):
        return os.path.join(self.get_saved_graphs_folder(), self.config.get("graph-file-name"))

    def get_save_graph(self):
        return self.config.get("save-graph").lower() == "true"

    def get_load_graph(self):
        return self.config.get("load-graph").lower() == "true"

    def get_trench_cost_per_cubic_m(self):
        return self.config.get("trench-cost-per-cubic-m")

    def get_decrease_max_clusters_to_find_pctg(self):
        return self.config.get("decrease-max-clusters-to-find-pctg")

    def get_log_detailed_results(self):
        return self.config.get("log-detailed-results").lower() == "true"

    def get_result_folder_path(self, create_new_folder):
        if not create_new_folder and not self.results_folder_path:
            raise Exception("No folder has been created.")
        if self.get_log_detailed_results():
            if create_new_folder:
                now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S.%f")
                dir_name = f"{now}-results"
                folder_path = os.path.join(self.config.get("results-file-path"), dir_name)
                os.makedirs(folder_path, exist_ok=True)
                self.results_folder_path = folder_path
        return self.results_folder_path

    def get_population_factor(self):
        return self.config.get("population-factor")

    def get_num_generations_to_break(self):
        return self.config.get("num-generations-to-break")

    def get_do_warm_start(self):
        return self.config.get("do-warm-start").lower() == "true"

    def get_eps(self):
        return self.config.get("eps")

    def get_life_time_of_heating_source(self):
        return int(self.config.get("life-time-in-years"))

    def get_use_random_seed(self):
        return self.config.get("use-random-seed").lower() == "true"