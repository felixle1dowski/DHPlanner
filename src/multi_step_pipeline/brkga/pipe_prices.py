import json


class PipePrices:

    def __init__(self):
        pass

    @staticmethod
    def open_prices_json(self, json_path):
        with open(json_path) as json_file:
            data = json.load(json_file)
            return data