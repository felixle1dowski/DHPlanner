class HeatingSource:
    def __init__(self, heating_source_name, heating_source_capacity_kw, heating_source_cost_euro,
                 heating_source_lifetime_years):
        self.name = heating_source_name
        self.capacity_kw = heating_source_capacity_kw
        self.cost_euro = heating_source_cost_euro
        self.lifetime_years = heating_source_lifetime_years