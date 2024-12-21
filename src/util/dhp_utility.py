from PyQt5.QtCore import QVariant
from qgis.core import QgsField, QgsFeatureRequest
from .logger import Logger

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
        expression = f"'{id_field_name}' = '{id_value}'"
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

        # Get the data type of the existing field
        existing_field = layer.fields()[existing_field_idx]
        field_type = existing_field.type()
        # Add the new field to the layer
        layer.dataProvider().addAttributes([QgsField(f"{new_field_name}", field_type)])
        layer.updateFields()  # Update the layer with the new field

        # Get the index of the newly added field
        new_field_idx = layer.fields().indexFromName(new_field_name)

        # Copy values from the existing field to the new field
        for feature in layer.getFeatures():
            # Get the value from the existing field
            value = feature[existing_field_name]

            # Set the value in the new field
            feature.setAttribute(new_field_idx, value)
            layer.updateFeature(feature)  # Save the feature with the updated field

        # Commit the changes to the layer
        layer.commitChanges()

        print(f"Field '{new_field_name}' added and values from '{existing_field_name}' copied.")

    @staticmethod
    def copy_values_between_fields(layer, source_field_name, target_field_name):
        """
        Copies values from an existing source field to an existing target field in the same layer.

        :param layer: QgsVectorLayer (the layer to modify)
        :param source_field_name: str (name of the field to copy values from)
        :param target_field_name: str (name of the field to copy values to)
        """
        # Ensure the layer is editable
        layer.startEditing()

        # Get the indices of the source and target fields
        source_field_idx = layer.fields().indexFromName(source_field_name)
        target_field_idx = layer.fields().indexFromName(target_field_name)

        if source_field_idx == -1:
            raise ValueError(f"Source field '{source_field_name}' not found in the layer.")
        if target_field_idx == -1:
            raise ValueError(f"Target field '{target_field_name}' not found in the layer.")

        # Copy values from the source field to the target field
        for feature in layer.getFeatures():
            # Get the value from the source field
            value = feature[source_field_name]

            # Set the value in the target field
            feature.setAttribute(target_field_idx, value)

            # Update the feature with the new value in the target field
            layer.updateFeature(feature)

        # Commit the changes to the layer
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
    def get_value_from_field(layer, feature, field_name):
        idx = layer.fields().indexFromName(field_name)
        value = feature[idx]
        return value