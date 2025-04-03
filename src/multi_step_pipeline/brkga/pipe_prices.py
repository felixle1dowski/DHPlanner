import json
from ...util.logger import Logger

class PipePrices:

    def __init__(self):
        pass

    @staticmethod
    def open_prices_json(json_path):
        with open(json_path) as json_file:
            data = json.load(json_file)
            # Logger().debug(f"successfully opened json file {data}")
            return data