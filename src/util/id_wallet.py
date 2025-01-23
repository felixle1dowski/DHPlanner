from collections import defaultdict

class IdWallet:
    """Holds the highest ids for custom id fields.
        Thus one needs to iterate through all ids only once.
        """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(IdWallet, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.highest_ids = defaultdict(dict)
        """layer : {id_field : highest_id}"""

    # ToDo: Add validity checks.
    def _get_highest_id(self, layer, id_field_name):
        """Assumes ID is a string and came be made into an integer."""
        if self.highest_ids.get(layer) is None or self.highest_ids.get(layer).get(id_field_name) is None:
            features = layer.getFeatures()
            id_idx = layer.fields().indexFromName(id_field_name)
            id_list = []
            for feature in features:
                id_list.append(feature[id_idx])
            id_list_int = list(map(int, id_list))
            highest_id = str(max(id_list_int))
            self.highest_ids[layer][id_field_name] = highest_id
            return highest_id
        else:
            return self.highest_ids[layer][id_field_name]

    def get_new_id(self, layer, id_field_name):
        highest_id = self._get_highest_id(layer, id_field_name)
        highest_id_int = int(highest_id)
        highest_id_int += 1
        highest_id_str = str(highest_id_int)
        self.highest_ids[layer][id_field_name] = highest_id_str
        return highest_id_str