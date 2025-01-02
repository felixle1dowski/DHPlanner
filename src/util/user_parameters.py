from qgis.core import QgsVectorLayer
from .energy_unit import EnergyUnit
from .topology_creation_strategy import TopologyCreationStrategy

class UserParameters:
    """Singleton dataclass for all user parameters that have been passed through the GUI."""

    building_layer : QgsVectorLayer
    road_layer : QgsVectorLayer
    selection_layer : QgsVectorLayer
    heating_source_capacity : float
    heating_source_capacity_unit : EnergyUnit
    max_distance_between_buildings : float
    min_buildings_for_cluster : int
    warming_threshold_capacity : float
    topology_creation_strategy : TopologyCreationStrategy
    excluded_road_types : list[str]
    heat_demand_reduction_factor : float

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def is_fully_initialized(self):
        layers_bool = self.building_layer is not None and self.road_layer is not None and self.selection_layer is not None
        heating_source_bool = self.heating_source_capacity is not None and self.heating_source_capacity_unit is not None
        clustering_bool = self.max_distance_between_buildings is not None and self.min_buildings_for_cluster is not None and self.warming_threshold_capacity is not None
        topology_bool = self.topology_creation_strategy is not None and self.excluded_road_types is not None
        heat_demand_reduction_bool = self.heat_demand_reduction_factor is not None
        return layers_bool and heating_source_bool and clustering_bool and topology_bool and heat_demand_reduction_bool