import pandas as pd
from heating_source import HeatingSource

class MindedHeatingSources:

    HEATING_SOURCES_CSV_RELATIVE_PATH = "./minded_heating_sources.csv"
    HEATING_SOURCE_CAPACITY_COL_NAME = "heating_source_capacity_kw"

    def __init__(self):
        self.heating_sources_info = pd.read_csv(self.HEATING_SOURCES_CSV_RELATIVE_PATH, delimiter=";")
        self.heating_sources_info.sort_values(by=self.HEATING_SOURCE_CAPACITY_COL_NAME, inplace=True)
        self.heating_sources = []
        for heating_source in self.heating_sources_info.itertuples():
            self.heating_sources.append(HeatingSource(heating_source.name,
                                                      heating_source.capacity_kw,
                                                      heating_source.cost_euro,
                                                      heating_source.lifetime_years))

    def get_number_of_heating_sources(self):
        return self.heating_sources_info.shape[0]

    def get_heating_sources(self):
        return self.heating_sources

    # ToDo: What to do in the case of collisions?
    def get_heating_source_by_name(self, heating_source_name):
        for heating_source in self.heating_sources:
            if heating_source.name == heating_source_name:
                return heating_source
            else:
                raise Exception(f"No heating source with {heating_source_name} found")

    def get_heating_source_by_index(self, heating_source_index):
        return self.heating_sources[heating_source_index]