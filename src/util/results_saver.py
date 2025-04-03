import json

from .config import Config
from .logger import Logger
from datetime import datetime
import os

class ResultsSaver:

    @staticmethod
    def save_result(file_name, create_new_folder, **fields_to_save):
        folder_path = Config().get_result_folder_path(create_new_folder)
        result_file_path = os.path.join(folder_path, f"{file_name}.json")
        json_dict = {
            **fields_to_save
        }
        with open(result_file_path, "w") as result_file:
            json.dump(json_dict, result_file, indent=4)
        # Logger().debug(f"Result saved to {result_file_path}")