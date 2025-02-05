import os
import pandas as pd


class PipeDiameterCatalogue:
    TITLE_ROW = 0
    SPECIFICATION_ROW = 1
    UNIT_ROW = 2
    DATA_START = 3

    MASS_FLOW_COL = 0
    PIPE_TITLE_COLS_START = -6
    PIPE_TITLE_COLS_END = -1
    PIPE_DIAMETER_COLS = [-6, -5, -4, -3, -2, -1]

    MASS_FLOW_DATA_COL = 0
    PIPE_DATA_COLS = [6, 8, 10, 12, 14, 16]

    MASS_FLOW_COL_NAME = "Volumenstrom"

    CORRESPONDING_DATA_INDEX = {
         0 : 0,
        -6 : 6,
        -5 : 8,
        -4 : 10,
        -3 : 12,
        -2 : 14,
        -1 : 16
    }

    # careful - this is not a normal hyphen.
    CATALOGUE_NONE_VALUE_INDICATOR = '–'

    def open_catalogue(self, path):
        catalogue = open(path)
        return catalogue

    def open_catalogues(self, dir_path):
        catalogues = []
        processed_catalogues = []
        for catalogue in os.listdir(dir_path):
            catalogues.append(self.open_catalogue(os.path.join(dir_path, catalogue)))
        for catalogue in catalogues:
            processed_catalogues.append(self.interpret_lines(catalogue))
        return processed_catalogues

    def interpret_lines(self, catalogue):
        processed_catalogue = []
        for line in catalogue.readlines():
            elements = line.split(" ")
            elements = [element.replace('\n', '') for element in elements]
            elements = [element.replace(',', '.') for element in elements]
            processed_catalogue.append(elements)
        return processed_catalogue

    def prepare_for_dataframe_creation(self, catalogues):
        relevant_cols = [self.MASS_FLOW_DATA_COL]
        list_of_dicts = []
        for value in self.PIPE_DATA_COLS:
            relevant_cols.append(value)

        for catalogue in catalogues:
            ### TITLES
            column_titles = {self.MASS_FLOW_COL: catalogue[self.TITLE_ROW][self.MASS_FLOW_COL]}
            for title_index in self.PIPE_DIAMETER_COLS:
                title = catalogue[self.TITLE_ROW][title_index]
                column_titles[title_index] = title

            ### DATA IN DICT
            for line in catalogue[self.DATA_START:]:
                line_dict = {}
                for index, title in column_titles.items():
                    value = line[self.CORRESPONDING_DATA_INDEX[index]]
                    if value != self.CATALOGUE_NONE_VALUE_INDICATOR:
                        line_dict[title] = value
                list_of_dicts.append(line_dict)
        print(list_of_dicts)
        return list_of_dicts

    def create_dataframe(self, catalogues):
        list_of_dicts = self.prepare_for_dataframe_creation(catalogues)
        df = pd.DataFrame(list_of_dicts)
        df = df.astype(float)
        df = df.sort_values(by=self.MASS_FLOW_COL_NAME)
        return df
