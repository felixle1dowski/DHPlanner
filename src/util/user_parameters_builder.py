from .energy_unit import EnergyUnit
from .topology_creation_strategy import TopologyCreationStrategy
from .user_parameters import UserParameters
from qgis.core import QgsVectorLayer

class UserParametersBuilder:
    """Builds User Parameters. Validates user inputs."""

    user_parameters : UserParameters

    def __init__(self):
        self.user_parameters = UserParameters()

    def set_selection_layer(self, selection_layer: list[QgsVectorLayer]):
        if len(selection_layer) > 1:
            return (f"There are {len(selection_layer)} selection layers with the same name."
                    f"There can only be one.")
        self.user_parameters.selection_layer = selection_layer[0]
        return self

    def set_building_layer(self, building_layer: list[QgsVectorLayer]):
        if len(building_layer) > 1:
            return(f"There are {len(building_layer)} building layers with the same name."
                   f"There can only be one.")
        self.user_parameters.building_layer = building_layer[0]
        return self

    def set_road_layer(self, road_layer: list[QgsVectorLayer]):
        if len(road_layer) > 1:
            return  (f"There are {len(road_layer)} road layers with the same name."
                    f"There can only be one.")
        self.user_parameters.road_layer = road_layer[0]
        return self

    def set_heating_source_capacity(self, heating_source_capacity: float):
        self.user_parameters.heating_source_capacity = heating_source_capacity
        return self

    def set_heating_source_capacity_unit(self, energy_unit: EnergyUnit):
        self.user_parameters.heating_source_capacity_unit = energy_unit
        return self

    def set_max_distance_between_buildings(self, max_distance_between_buildings: float):
        self.user_parameters.max_distance_between_buildings = max_distance_between_buildings
        return self

    def set_min_buildings_for_cluster(self, min_buildings_for_cluster: int):
        self.user_parameters.min_buildings_for_cluster = min_buildings_for_cluster
        return self

    def set_warming_threshold_capacity(self, warming_threshold_capacity: float):
        self.user_parameters.warming_threshold_capacity = warming_threshold_capacity
        return self

    def set_topology_creation_strategy(self, topology_creation_strategy: TopologyCreationStrategy):
        self.user_parameters.topology_creation_strategy = topology_creation_strategy
        return self

    def set_excluded_road_types(self, excluded_road_types: list):
        self.user_parameters.excluded_road_types = excluded_road_types
        return self

    def set_heat_demand_reduction_factor(self, heat_demand_reduction_factor: float):
        self.user_parameters.heat_demand_reduction_factor = heat_demand_reduction_factor
        return self

    def build(self):
        if self.user_parameters.is_fully_initialized():
            return self.user_parameters
        else:
            raise Exception("User Parameters is not fully initialized")

    # ToDo: I don't want to use this in the end! But I don't need a fully initialized User Parameters yet!
    def build_test(self):
        return self.user_parameters
