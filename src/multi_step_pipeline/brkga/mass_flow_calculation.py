from ...util.dhp_utility import DhpUtility

class MassFlowCalculation:

    ABSOLUTE_ROUGHNESS_IN_MM = 0.007
    MAX_PRESSURE_DROP_IN_BAR = 8
    SUPPLY_TEMPERATURE = 80
    WATER_HEAT_CAPACITY_IN_KJ_PER_KG_TIMES_K = 4.190
    WATER_DENSITY = 0.997

    def __init__(self):
        pass

    def calculate_mass_flow(self, demand, temperature_spread=30):
        water_heat_capacity = self.WATER_HEAT_CAPACITY_IN_KJ_PER_KG_TIMES_K
        supply_temperature = self.SUPPLY_TEMPERATURE
        return_temperature = supply_temperature - temperature_spread
        water_density = self.WATER_DENSITY
        mass_flow = demand / (water_heat_capacity * water_density * (supply_temperature - return_temperature))
        return mass_flow

    def calculate_mass_flows(self, demands: {str: float}):
        mass_flow_dict = {}
        for id_, demand in demands.items():
            mass_flow = self.calculate_mass_flow(float(demand))
            mass_flow_dict[id_] = mass_flow
        return mass_flow_dict