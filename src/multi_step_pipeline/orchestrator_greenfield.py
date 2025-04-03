from .preprocessing import Preprocessing
from ..util.config import Config
from qgis.core import QgsProject

class OrchestratorGreenfield:

    def __init__(self, preprocessor, clustering_first_stage, feasible_solution_creator, clustering_second_stage,
                 graph_creator, visualization):
        self.preprocessing = preprocessor
        self.clustering_first_stage = clustering_first_stage
        self.feasible_solution_creator = feasible_solution_creator
        self.clustering_second_stage = clustering_second_stage
        self.graph_creator = graph_creator
        self.visualization = visualization

    def start(self):
        preprocessing_result = self.preprocessing.start()
        graph, building_to_point_dict, line_layer = self.graph_creator.start("greenfield",
                                                                 building_centroids=preprocessing_result.building_centroids)
        translated_nodes = []
        reverse_translation = dict(zip(building_to_point_dict.values(), building_to_point_dict.keys()))
        nodes = list(graph.nodes())
        for node in nodes:
            translated_nodes.append(reverse_translation[node])
        self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids)
        clustering_first_stage_results = self.clustering_first_stage.start()
        self.clustering_second_stage.set_required_fields(shortest_path_graph=graph,
                                                         first_stage_cluster_dict=clustering_first_stage_results,
                                                         # ToDo: This is only in because of sloppy visualization. Remove!!
                                                         buildings_layer=QgsProject.instance().mapLayersByName(
                                                             Config().get_buildings_layer_name())[0],
                                                         building_centroids_layer=preprocessing_result.building_centroids,
                                                         feasible_solution_creator=self.feasible_solution_creator,
                                                         graph_translation_dict=building_to_point_dict)
        clustering_second_stage_results = self.clustering_second_stage.start()
        self.visualization.set_required_fields(line_layer, clustering_second_stage_results,
                                               preprocessing_result.building_centroids)
        self.visualization.start()