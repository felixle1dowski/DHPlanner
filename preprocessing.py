from .config import Config
from qgis.core import QgsProject, QgsSpatialIndex, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMessageLog, Qgis
from .logger import Logger

class Preprocessing:

    DESIRED_CRS = QgsCoordinateReferenceSystem('EPSG:3857')

    selection_layer = None
    roads_layer_path = None
    roads_layer = None
    buildings_layer_path = None
    buildings_layer = None

    def __init__(self):
        pass

    def start(self):
        self.selection_layer = None
        self.roads_layer_path = Config().get_roads_path()
        self.buildings_layer_path = Config().get_buildings_path()
        self.__verify_selection()
        self.selection_layer = QgsProject.instance().mapLayersByName(Config().get_selection_layer_name())[0]

    # needs to be tested.
    def __verify_selection(self):
        selection_layer_name = Config().get_selection_layer_name()
        selection_layer = QgsProject.instance().mapLayersByName(selection_layer_name)[0]
        if selection_layer is None:
            raise Exception("No selection layer found.")
        if selection_layer.crs() != self.DESIRED_CRS:
            Logger().warning(f"Selection Layer has the wrong CRS."
                             "It is: {selection_layer.crs()} The right"
                             "CRS is necessary in order to calculate pipe"
                             "lengths in meters."
                             "Changing CRS to EPSG:3857")
            self.__convert_to_crs(selection_layer, self.DESIRED_CRS)
        Logger().info("Selection has been verified successfully.")

    def __convert_to_crs(self, layer, crs):
        source_crs = layer.crs()
        transform = QgsCoordinateTransform(source_crs, crs, QgsProject.instance())
        layer.startEditing()
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                geom.transform(transform)
            layer.changeGeometry(feature.id(), geom)
        layer.setCrs(crs)
        layer.commitChanges()
        Logger().info("Selection CRS has been changed successfully.")

