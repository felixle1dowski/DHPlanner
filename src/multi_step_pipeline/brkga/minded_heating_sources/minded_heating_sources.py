import pandas as pd
import os
from .heating_source import HeatingSource
from ....util.logger import Logger

class MindedHeatingSources:
    SCRIPT_DIR = os.path.dirname(__file__)
    HEATING_SOURCES_CSV_PATH = os.path.join(SCRIPT_DIR, "./minded_heating_sources.csv")
    HEATING_SOURCE_CAPACITY_COL_NAME = "heating_source_capacity_kw"

    def __init__(self):
        self.heating_sources_info = pd.read_csv(self.HEATING_SOURCES_CSV_PATH, delimiter=";")
        self.heating_sources_info.sort_values(by=self.HEATING_SOURCE_CAPACITY_COL_NAME, inplace=True)
        self.heating_sources = []
        for heating_source in self.heating_sources_info.itertuples():
            self.heating_sources.append(HeatingSource(heating_source.heating_source_name,
                                                      heating_source.heating_source_capacity_kw,
                                                      heating_source.heating_source_cost_euro,
                                                      heating_source.heating_source_lifetime_years))

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