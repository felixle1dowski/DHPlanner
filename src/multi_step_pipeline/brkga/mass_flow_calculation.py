from ...util.dhp_utility import DhpUtility

class MassFlowCalculation:

    @staticmethod
    def calculate_mass_flow(demand, temperature_spread=30):
        max_pressure_drop_in_bar = 8
        supply_temperature = 80
        water_heat_capacity_in_kj_per_kg_times_k = 4.190
        water_density = 0.997
        water_heat_capacity = water_heat_capacity_in_kj_per_kg_times_k
        supply_temperature = supply_temperature
        return_temperature = supply_temperature - temperature_spread
        water_density = water_density
        mass_flow = demand / (water_heat_capacity * water_density * (supply_temperature - return_temperature))
        return mass_flow

    @staticmethod
    def calculate_mass_flows(demands: {str: float}):
        mass_flow_dict = {}
        for id_, demand in demands.items():
            mass_flow = MassFlowCalculation.calculate_mass_flow(float(demand))
            mass_flow_dict[id_] = mass_flow
        return mass_flow_dict