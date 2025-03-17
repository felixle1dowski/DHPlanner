from PyQt5.QtCore import QVariant
from qgis.core import QgsField, QgsFeatureRequest, QgsExpression, QgsVectorLayer, QgsProject
from qgis import processing
from .logger import Logger
from .id_wallet import IdWallet

class DhpUtility:
    """Offers utility methods for DHP"""
    @staticmethod
    def assign_unique_ids(layer, id_field_name):
        """Assigns unique IDs."""
        layer.startEditing()
        layer.dataProvider().addAttributes([QgsField(f"{id_field_name}", QVariant.Int)])
        layer.updateFields()
        idx = 1
        for feature in layer.getFeatures():
            feature.setAttribute(f"{id_field_name}", idx)
            layer.updateFeature(feature)
            idx += 1

    @staticmethod
    def assign_unique_ids_custom_name(layer, id_field_name):
        """Assigns unique IDs in a layer that has partially unique ids."""
        layer.startEditing()
        id_set = set()
        feature_list = DhpUtility.convert_iterator_to_list(layer.getFeatures())
        for feature in feature_list:
            value = DhpUtility.get_value_from_field(layer, feature, id_field_name)
            id_set.add(value)
            if value in id_set:
                DhpUtility.assign_unique_id_custom_id_field(layer, feature, id_field_name)


    @staticmethod
    def assign_unique_id(layer, feature, id_field_name):
        """Assigns a unique ID to one feature of the layer.
        Caution: Layer still has to be updated after calling this method!"""

        # Check if the field exists
        id_field_index = layer.fields().indexFromName(id_field_name)
        if id_field_index == -1:
            raise ValueError(f"Field '{id_field_name}' does not exist in the layer.")
        max_id = max(
            [f.attribute(id_field_name) for f in layer.getFeatures() if
             isinstance(f.attribute(id_field_name), (int, float))],
            default=1
        )
        if max_id is None:
            max_id = 1
        unique_id = max_id + 1
        feature.setAttribute(id_field_index, unique_id)
        return unique_id

    @staticmethod
    def assign_unique_id_custom_id_field(layer, feature, id_field_name):
        new_highest_id = IdWallet().get_new_id(layer, id_field_name)
        DhpUtility.assign_value_to_field(layer, id_field_name, feature, new_highest_id)
        Logger().debug(f"assigned new id {new_highest_id} to feature {feature.id()}")
        return new_highest_id

    @staticmethod
    def assign_value_to_field(layer, field_name, feature, value):
        layer.startEditing()
        field_idx = layer.fields().indexFromName(field_name)
        feature.setAttribute(field_idx, value)
        layer.updateFeature(feature)
        layer.commitChanges()

    @staticmethod
    def assign_value_to_field_by_id(layer, id_field_name, id_value, value_field_name, value):
        """Usable for custom ids."""
        layer.startEditing()
        field_idx = layer.fields().indexFromName(id_field_name)
        value_field_idx = layer.fields().indexFromName(value_field_name)
        expression = f"{id_field_name} = '{id_value}'"
        request = QgsFeatureRequest().setFilterExpression(expression)
        for feature in layer.getFeatures(request):
            feature[value_field_idx] = value
            layer.updateFeature(feature)
        layer.commitChanges()

    @staticmethod
    def add_field_and_copy_values(layer, new_field_name, existing_field_name):
        """
        Adds a new field to the layer and copies the values from an existing field into the new field.

        :param layer: QgsVectorLayer (the layer to modify)
        :param new_field_name: str (name of the new field to add)
        :param existing_field_name: str (name of the existing field to copy values from)
        """
        layer.startEditing()
        existing_field_idx = layer.fields().indexFromName(existing_field_name)
        if existing_field_idx == -1:
            raise ValueError(f"Field '{existing_field_name}' not found in the layer.")

        existing_field = layer.fields()[existing_field_idx]
        field_type = existing_field.type()
        layer.dataProvider().addAttributes([QgsField(f"{new_field_name}", field_type)])
        layer.updateFields()
        new_field_idx = layer.fields().indexFromName(new_field_name)
        for feature in layer.getFeatures():
            value = feature[existing_field_name]

            feature.setAttribute(new_field_idx, value)
            layer.updateFeature(feature)
        layer.commitChanges()

    @staticmethod
    def add_field(layer, new_field_name, field_type):
        layer.startEditing()
        existing_field_idx = layer.fields().indexFromName(new_field_name)
        if existing_field_idx != -1:
            raise ValueError(f"Field '{new_field_name}' already exists in the layer.")
        layer.dataProvider().addAttributes([QgsField(f"{new_field_name}", field_type)])
        layer.updateFields()
        layer.commitChanges()
        Logger().debug(f"Field '{new_field_name}' added to layer '{layer.name()}'.")

    @staticmethod
    def copy_values_between_fields(layer, source_field_name, target_field_name):
        """
        Copies values from an existing source field to an existing target field in the same layer.

        :param layer: QgsVectorLayer (the layer to modify)
        :param source_field_name: str (name of the field to copy values from)
        :param target_field_name: str (name of the field to copy values to)
        """
        layer.startEditing()
        source_field_idx = layer.fields().indexFromName(source_field_name)
        target_field_idx = layer.fields().indexFromName(target_field_name)
        if source_field_idx == -1:
            raise ValueError(f"Source field '{source_field_name}' not found in the layer.")
        if target_field_idx == -1:
            raise ValueError(f"Target field '{target_field_name}' not found in the layer.")
        for feature in layer.getFeatures():
            value = feature[source_field_name]
            feature.setAttribute(target_field_idx, value)
            layer.updateFeature(feature)
        layer.commitChanges()

        print(f"Values copied from '{source_field_name}' to '{target_field_name}'.")

    @staticmethod
    def create_new_field(layer, new_field_name, q_Type: QVariant):
        # Check if the field already exists
        field_names = [field.name() for field in layer.fields()]

        if new_field_name not in field_names:
            layer.startEditing()
            layer_provider = layer.dataProvider()
            field = QgsField(new_field_name, q_Type)
            layer_provider.addAttributes([field])
            layer.commitChanges()
            print(f"Field '{new_field_name}' created.")
        else:
            print(f"Field '{new_field_name}' already exists.")

    @staticmethod
    def transfer_values_by_matching_id(target_layer,
                                       source_layer_features,
                                       target_layer_features,
                                       transferred_field_name,
                                       matching_field_name):
        """transferred_field_name and matching_field_name have to be the same for both layers."""
        """ToDo: Make sure that this is valid."""
        target_layer.startEditing()
        target_layer_transferred_idx = target_layer.fields().indexFromName(transferred_field_name)
        transferred_data = {}
        for feature in source_layer_features:
            value_to_match = feature[matching_field_name]
            transferred_value = feature[transferred_field_name]
            transferred_data[value_to_match] = transferred_value

        Logger().debug((f"Transferred data: {transferred_data}"))

        for feature in target_layer_features:
            value_to_match = feature[matching_field_name]
            if value_to_match in transferred_data:
                value_to_transfer = transferred_data[value_to_match]
                feature.setAttribute(target_layer_transferred_idx, value_to_transfer)
                target_layer.updateFeature(feature)
        target_layer.commitChanges()
        Logger().debug(("Transfer completed."))

    @staticmethod
    def convert_iterator_to_list(iterator):
        """Converts QGIS-Iterator to list."""
        # This is useful if we have to rewind iterators frequently for example in nested for-loops.
        # We hereby forgo making a lot of feature requests.
        iterator_list = []
        for element in iterator:
            iterator_list.append(element)
        return iterator_list

    @staticmethod
    def get_features_by_id_field(layer, id_field_name, ids):
        # ToDo: Get all features from specifying request with custom id field.
        id_string = str.join(", ", ids)
        expression = QgsExpression(f'"{id_field_name}" IN ({id_string})')
        request = QgsFeatureRequest(expression)
        features = layer.getFeatures(request)
        return features

    @staticmethod
    def get_feature_by_id_field(layer, id_field_name, id_):
        expression = QgsExpression(f'"{id_field_name}" IN ({id_})')
        request = QgsFeatureRequest(expression)
        feature = layer.getFeatures(request)
        feature_list = DhpUtility.convert_iterator_to_list(feature)
        if len(feature_list) > 1:
            raise Exception(f"Multiple features found for id {id}."
                            f"Ids in id field may not be unique.")
        if len(feature_list) == 0:
            return None
        return feature_list[0]

    @staticmethod
    def get_value_from_field(layer, feature, field_name):
        idx = layer.fields().indexFromName(field_name)
        value = feature[idx]
        return value

    @staticmethod
    def get_value_from_feature_by_id_field(layer, id_field_name, id_to_find, field_name_to_look_up):
        """Only usable for one id."""
        look_up_field_idx = layer.fields().indexFromName(field_name_to_look_up)
        expression = QgsExpression(f'"{id_field_name}" IN ({id_to_find})')
        request = QgsFeatureRequest(expression)
        feature = layer.getFeatures(request)
        feature_list = DhpUtility.convert_iterator_to_list(feature)
        if len(feature_list) > 1:
            raise Exception(f"More than one feature found for id '{id_field_name}'. Not permitted!")
        value = feature_list[0][look_up_field_idx]
        return value

    @staticmethod
    def flatten_list(list_of_lists):
        result = []
        for item in list_of_lists:
            if isinstance(item, list):
                result.extend(DhpUtility.flatten_list(item))  # Recursively flatten list
            else:
                result.append(item)
        return result

    @staticmethod
    def get_xy_by_id_field(layer, id_field_name, id):
        expression = QgsExpression(f'"{id_field_name}" IN ({id})')
        request = QgsFeatureRequest(expression)
        feature = layer.getFeatures(request)
        feature_list = DhpUtility.convert_iterator_to_list(feature)
        if len(feature_list) > 1:
            raise Exception(f"More than one feature found for id '{id_field_name}'. Not permitted!")
        feature_geom = feature_list[0].geometry()
        feature_xy = (feature_geom.asPoint().x(), feature_geom.asPoint().y())
        return feature_xy

    @staticmethod
    def convert_line_to_points(layer: QgsVectorLayer, distance_of_points: float, debug=False) -> QgsVectorLayer:
        """
        Creates a point layer from a line layer.

        :param layer: A line layer.
        :type layer: QgsVectorLayer
        :return: A converted line layer that now features points along every line.
        :rtype: QgsVectorLayer
        """
        output_layer_path = "memory:"
        result = processing.run("native:pointsalonglines", {
            'INPUT': layer,
            'OUTPUT': output_layer_path,
            'DISTANCE': distance_of_points,
        })
        output_layer = result['OUTPUT']
        output_layer.setName('points_on_line')
        DhpUtility.assign_unique_ids(output_layer, "idx")
        if debug:
            QgsProject.instance().addMapLayer(output_layer)
        return output_layer

    @staticmethod
    def delete_features_custom_id(layer, id_field_name, id_value):
        provider = layer.dataProvider()
        feature = DhpUtility.get_feature_by_id_field(layer, id_field_name, id_value)
        provider.deleteFeatures([feature.id()])
        layer.commitChanges()