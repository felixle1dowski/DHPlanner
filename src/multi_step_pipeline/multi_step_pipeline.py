import random

from ..dhc_creation_pipeline import DHCCreationPipeline
from ..util.logger import Logger
from ..util.logger import Config
import time
import networkx as nx
from qgis.core import QgsProject


class MultiStepPipeline(DHCCreationPipeline):
    preprocessing = None
    graph_creator = None
    shortest_path_creator = None
    mst_visualizer = None
    clustering_first_stage = None
    clustering_second_stage = None
    feasible_solution_creator = None
    visualization = None

    def __init__(self, preprocessor, clustering_first_stage, feasible_solution_creator, clustering_second_stage,
                 graph_creator, shortest_path_creator, mst_visualizer, visualization):
        self.preprocessing = preprocessor
        self.clustering_first_stage = clustering_first_stage
        self.feasible_solution_creator = feasible_solution_creator
        self.clustering_second_stage = clustering_second_stage
        self.graph_creator = graph_creator
        self.shortest_path_creator = shortest_path_creator
        self.mst_visualizer = mst_visualizer
        self.visualization = visualization

    def start(self):
        # Logger().info("Starting Preprocessing.")
        preprocessing_result = self.timed_wrapper(self.preprocessing.start)
        # Logger().info("Finished Preprocessing.")
        graph, building_to_point_dict, line_layer = self.graph_creator.start(
            strategy=Config().get_installation_strategy(),
            exploded_roads=preprocessing_result.exploded_roads,
            building_centroids=preprocessing_result.building_centroids)
        self.shortest_path_creator.set_required_fields(graph, line_layer, list(building_to_point_dict.values()))
        shortest_paths = self.shortest_path_creator.start()

        if Config().get_distance_measuring_method() == "custom":
            # ToDo: Put this into function!
            adjacency_matrix = nx.adjacency_matrix(shortest_paths).todense()
            nodes = list(shortest_paths.nodes())
            # translate nodes
            translated_nodes = []
            reverse_translation = dict(zip(building_to_point_dict.values(), building_to_point_dict.keys()))
            for node in nodes:
                translated_nodes.append(reverse_translation[node])
            self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids,
                                                            adjacency_matrix,
                                                            translated_nodes)
        else:
            self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids)
        clustering_first_stage_results = self.clustering_first_stage.start()

        self.clustering_second_stage.set_required_fields(shortest_path_graph=shortest_paths,
                                                        first_stage_cluster_dict=clustering_first_stage_results,
                                                         # ToDo: This is only in because of sloppy visualization. Remove!!
                                                         buildings_layer=QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0],
                                                         building_centroids_layer=preprocessing_result.building_centroids,
                                                         feasible_solution_creator=self.feasible_solution_creator,
                                                         graph_translation_dict=building_to_point_dict)
        clustering_second_stage_results = self.clustering_second_stage.start()

    #     clustering_second_stage_results = {
    #     "sums": {
    #         "sum_of_supplied_power": 1680.206429740167,
    #         "sum_of_total_pipe_cost": 508706.5432302234,
    #         "sum_of_pipe_investment_cost": 319068.7781890031,
    #         "sum_of_trench_cost": 189637.76504122038,
    #         "sum_of_total_cost": 1208706.5432302235,
    #         "sum_of_fitness": 719.3797868141369
    #     },
    #     "clusters": [
    #         {
    #             "cluster_center": "170944160",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951904",
    #                         "1130951808",
    #                         "1130951809",
    #                         "1130951905"
    #                     ],
    #                     "length": 16.35274560579839,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "170944160",
    #                     "to_building": "170944161",
    #                     "mass_flow": 0.937465466671611,
    #                     "pipe_cost": 2446.370742627439,
    #                     "trench_cost": 1420.4805929378529
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951886",
    #                         "1130951791",
    #                         "1130951526",
    #                         "1130951525",
    #                         "1130951790",
    #                         "1130951789",
    #                         "1130951523",
    #                         "1130951778",
    #                         "1130951883",
    #                         "1130951884",
    #                         "1130951631",
    #                         "1130951632",
    #                         "1130951810",
    #                         "1130951905"
    #                     ],
    #                     "length": 245.4715520243166,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "170944161",
    #                     "to_building": "35405799",
    #                     "mass_flow": 0.7516409772326829,
    #                     "pipe_cost": 36722.54418283776,
    #                     "trench_cost": 21322.87654773018
    #                 }
    #             ],
    #             "supplied_power": 248.06590319760676,
    #             "pipe_investment_cost": 39168.9149254652,
    #             "trench_cost": 22743.35714066803,
    #             "total_pipe_cost": 61912.27206613323,
    #             "total_cost": 161912.2720661332,
    #             "fitness": 652.698617500671,
    #             "members": [
    #                 "35405799",
    #                 "170944161",
    #                 "170944160"
    #             ]
    #         },
    #         {
    #             "cluster_center": "32789077",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951885",
    #                         "1130951814",
    #                         "1130951659",
    #                         "1130951837",
    #                         "1130951838",
    #                         "1130951839",
    #                         "1130951902"
    #                     ],
    #                     "length": 65.6042359206526,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "32789077",
    #                     "to_building": "170944158",
    #                     "mass_flow": 0.2066359508521963,
    #                     "pipe_cost": 5819.095726161886,
    #                     "trench_cost": 4544.335881733529
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951885",
    #                         "1130951813",
    #                         "1130951490",
    #                         "1130951806",
    #                         "1130951805",
    #                         "1130951556",
    #                         "1130951555",
    #                         "1130951606",
    #                         "1130951817",
    #                         "1130951816",
    #                         "1130951815",
    #                         "1130951604",
    #                         "1130951541",
    #                         "1130951542",
    #                         "1130951692",
    #                         "1130951852",
    #                         "1130951890"
    #                     ],
    #                     "length": 201.35352035937998,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 185,
    #                         "price": 207.8
    #                     },
    #                     "from_building": "32789077",
    #                     "to_building": "170766315",
    #                     "mass_flow": 1.4423124193955947,
    #                     "pipe_cost": 41841.26153067916,
    #                     "trench_cost": 19028.612411282673
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951890",
    #                         "1130951852",
    #                         "1130951692",
    #                         "1130951542",
    #                         "1130951541",
    #                         "1130951540",
    #                         "1130951760",
    #                         "1130951759",
    #                         "1130951479",
    #                         "1130951539",
    #                         "1130951538",
    #                         "1130951537",
    #                         "1130951536",
    #                         "1130951804",
    #                         "1130951803",
    #                         "1130951924"
    #                     ],
    #                     "length": 216.37981846164635,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "170766315",
    #                     "to_building": "246032667",
    #                     "mass_flow": 0.23664580197078472,
    #                     "pipe_cost": 19192.889897548033,
    #                     "trench_cost": 14988.400662230673
    #                 }
    #             ],
    #             "supplied_power": 249.9944557844258,
    #             "pipe_investment_cost": 66853.24715438907,
    #             "trench_cost": 38561.348955246875,
    #             "total_pipe_cost": 105414.59610963595,
    #             "total_cost": 205414.59610963595,
    #             "fitness": 821.6766066475019,
    #             "members": [
    #                 "170766315",
    #                 "170944158",
    #                 "246032667",
    #                 "32789077"
    #             ]
    #         },
    #         {
    #             "cluster_center": "249672017",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951916",
    #                         "1130951794",
    #                         "1130951933"
    #                     ],
    #                     "length": 19.99999999995878,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "249672017",
    #                     "to_building": "172146675",
    #                     "mass_flow": 0.94633367926094,
    #                     "pipe_cost": 2991.9999999938336,
    #                     "trench_cost": 1737.2991999964195
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951928",
    #                         "1130951797",
    #                         "1130951796",
    #                         "1130951795",
    #                         "1130951933"
    #                     ],
    #                     "length": 32.558511849673565,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "249672017",
    #                     "to_building": "249672011",
    #                     "mass_flow": 0.7497991106597537,
    #                     "pipe_cost": 4870.753372711165,
    #                     "trench_cost": 2828.19382948142
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951916",
    #                         "1130951793",
    #                         "1130951531",
    #                         "1130951874",
    #                         "1130951875",
    #                         "1130951926"
    #                     ],
    #                     "length": 125.25172563263806,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "172146675",
    #                     "to_building": "249672006",
    #                     "mass_flow": 0.8077305541542669,
    #                     "pipe_cost": 18737.658154642653,
    #                     "trench_cost": 10879.986137010079
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951901",
    #                         "1130951845",
    #                         "1130951473",
    #                         "1130951530",
    #                         "1130951874",
    #                         "1130951875",
    #                         "1130951926"
    #                     ],
    #                     "length": 97.49718429490228,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 128,
    #                         "price": 101.9
    #                     },
    #                     "from_building": "249672006",
    #                     "to_building": "170944157",
    #                     "mass_flow": 0.6540478443231028,
    #                     "pipe_cost": 9934.963079650543,
    #                     "trench_cost": 7244.415182298932
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951892",
    #                         "1130951846",
    #                         "1130951901"
    #                     ],
    #                     "length": 11.626465444000527,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 128,
    #                         "price": 101.9
    #                     },
    #                     "from_building": "170944157",
    #                     "to_building": "170766319",
    #                     "mass_flow": 0.4988058435848941,
    #                     "pipe_cost": 1184.7368287436536,
    #                     "trench_cost": 863.8910281165441
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951928",
    #                         "1130951797",
    #                         "1130951717",
    #                         "1130951858",
    #                         "1130951859",
    #                         "1130951720",
    #                         "1130951930"
    #                     ],
    #                     "length": 46.90052710579888,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 79.5
    #                     },
    #                     "from_building": "249672011",
    #                     "to_building": "249672013",
    #                     "mass_flow": 0.17093173746570242,
    #                     "pipe_cost": 3728.5919049110107,
    #                     "trench_cost": 3248.7497980599564
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951913",
    #                         "1130951864",
    #                         "1130951729",
    #                         "1130951801",
    #                         "1130951800",
    #                         "1130951799",
    #                         "1130951798",
    #                         "1130951928"
    #                     ],
    #                     "length": 95.813025787643,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 128,
    #                         "price": 101.9
    #                     },
    #                     "from_building": "249672011",
    #                     "to_building": "172146671",
    #                     "mass_flow": 0.4297052583130038,
    #                     "pipe_cost": 9763.347327760823,
    #                     "trench_cost": 7119.2757380409
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951913",
    #                         "1130951918"
    #                     ],
    #                     "length": 0,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "172146671",
    #                     "to_building": "172146678",
    #                     "mass_flow": 0.21348648384189758,
    #                     "pipe_cost": 0.0,
    #                     "trench_cost": 0.0
    #                 }
    #             ],
    #             "supplied_power": 232.15787472368424,
    #             "pipe_investment_cost": 51212.05066841368,
    #             "trench_cost": 33921.81091300426,
    #             "total_pipe_cost": 85133.86158141794,
    #             "total_cost": 185133.86158141794,
    #             "fitness": 797.4481236174539,
    #             "members": [
    #                 "172146675",
    #                 "170766319",
    #                 "172146678",
    #                 "249672006",
    #                 "170944157",
    #                 "172146671",
    #                 "249672013",
    #                 "249672011",
    #                 "249672017"
    #             ]
    #         },
    #         {
    #             "cluster_center": "35405801",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951888",
    #                         "1130951782",
    #                         "1130951784",
    #                         "1130951896"
    #                     ],
    #                     "length": 70.88174838343818,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "35405801",
    #                     "to_building": "170944151",
    #                     "mass_flow": 0.899349109247685,
    #                     "pipe_cost": 10603.909558162351,
    #                     "trench_cost": 6157.140238057422
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951888",
    #                         "1130951781",
    #                         "1130951780",
    #                         "1130951456",
    #                         "1130951792",
    #                         "1130951791",
    #                         "1130951526",
    #                         "1130951525",
    #                         "1130951841",
    #                         "1130951900"
    #                     ],
    #                     "length": 170.85660035332225,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 79.5
    #                     },
    #                     "from_building": "35405801",
    #                     "to_building": "170944156",
    #                     "mass_flow": 0.18962553549359717,
    #                     "pipe_cost": 13583.099728089119,
    #                     "trench_cost": 11835.055598478259
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951896",
    #                         "1130951783",
    #                         "1130951467",
    #                         "1130951466",
    #                         "1130951465",
    #                         "1130951464",
    #                         "1130951878",
    #                         "1130951927"
    #                     ],
    #                     "length": 171.90448852895744,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 128,
    #                         "price": 101.9
    #                     },
    #                     "from_building": "170944151",
    #                     "to_building": "249672010",
    #                     "mass_flow": 0.4450114856222209,
    #                     "pipe_cost": 17517.067381100765,
    #                     "trench_cost": 12773.16361093749
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951927",
    #                         "1130951877",
    #                         "1130951950"
    #                     ],
    #                     "length": 15.000000000011308,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "249672010",
    #                     "to_building": "256322123",
    #                     "mass_flow": 0.2922373796150517,
    #                     "pipe_cost": 1330.5000000010032,
    #                     "trench_cost": 1039.0341000007834
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951949",
    #                         "1130951875",
    #                         "1130951876",
    #                         "1130951950"
    #                     ],
    #                     "length": 34.99999999996996,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 79.5
    #                     },
    #                     "from_building": "256322123",
    #                     "to_building": "256322122",
    #                     "mass_flow": 0.14412185870017283,
    #                     "pipe_cost": 2782.4999999976117,
    #                     "trench_cost": 2424.412899997919
    #                 }
    #             ],
    #             "supplied_power": 229.32691862125608,
    #             "pipe_investment_cost": 45817.076667350855,
    #             "trench_cost": 34228.80644747188,
    #             "total_pipe_cost": 80045.88311482272,
    #             "total_cost": 180045.88311482273,
    #             "fitness": 785.1057529455439,
    #             "members": [
    #                 "170944151",
    #                 "170944156",
    #                 "256322123",
    #                 "256322122",
    #                 "249672010",
    #                 "35405801"
    #             ]
    #         },
    #         {
    #             "cluster_center": "253692528",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951937",
    #                         "1130951872",
    #                         "1130951938"
    #                     ],
    #                     "length": 5.000000000004809,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "253692528",
    #                     "to_building": "253692529",
    #                     "mass_flow": 1.3201609891106378,
    #                     "pipe_cost": 748.0000000007193,
    #                     "trench_cost": 434.32480000041767
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951935",
    #                         "1130951870",
    #                         "1130951937"
    #                     ],
    #                     "length": 8.071077198914287,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "253692528",
    #                     "to_building": "253692526",
    #                     "mass_flow": 0.3000701788839824,
    #                     "pipe_cost": 715.9045475436973,
    #                     "trench_cost": 559.0749622269618
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951938",
    #                         "1130951873",
    #                         "1130951553",
    #                         "1130951554",
    #                         "1130951606",
    #                         "1130951817",
    #                         "1130951816",
    #                         "1130951946"
    #                     ],
    #                     "length": 81.72273290272497,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 164,
    #                         "price": 149.6
    #                     },
    #                     "from_building": "253692529",
    #                     "to_building": "256314772",
    #                     "mass_flow": 0.9201676385935758,
    #                     "pipe_cost": 12225.720842247656,
    #                     "trench_cost": 7098.841924685888
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951944",
    #                         "1130951818",
    #                         "1130951815",
    #                         "1130951946"
    #                     ],
    #                     "length": 34.99999999998563,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "256314772",
    #                     "to_building": "256314770",
    #                     "mass_flow": 0.3013240671439091,
    #                     "pipe_cost": 3104.499999998726,
    #                     "trench_cost": 2424.412899999005
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951942",
    #                         "1130951821",
    #                         "1130951760",
    #                         "1130951540",
    #                         "1130951604",
    #                         "1130951815",
    #                         "1130951946"
    #                     ],
    #                     "length": 69.58987208910533,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "256314772",
    #                     "to_building": "256314768",
    #                     "mass_flow": 0.3013237045464121,
    #                     "pipe_cost": 6172.621654303643,
    #                     "trench_cost": 4820.416674347912
    #                 }
    #             ],
    #             "supplied_power": 232.89932017688685,
    #             "pipe_investment_cost": 22966.74704409444,
    #             "trench_cost": 15337.071261260186,
    #             "total_pipe_cost": 38303.81830535462,
    #             "total_cost": 138303.81830535462,
    #             "fitness": 593.8352168667259,
    #             "members": [
    #                 "253692529",
    #                 "253692526",
    #                 "256314770",
    #                 "256314772",
    #                 "256314768",
    #                 "253692528"
    #             ]
    #         },
    #         {
    #             "cluster_center": "249672012",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951923",
    #                         "1130951800",
    #                         "1130951799",
    #                         "1130951798",
    #                         "1130951797",
    #                         "1130951717",
    #                         "1130951858",
    #                         "1130951929"
    #                     ],
    #                     "length": 77.45719514288663,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 185,
    #                         "price": 207.8
    #                     },
    #                     "from_building": "249672012",
    #                     "to_building": "246032665",
    #                     "mass_flow": 1.7881204930611345,
    #                     "pipe_cost": 16095.605150691843,
    #                     "trench_cost": 7319.97604118579
    #                 },
    #                 {
    #                     "id": [
    #                         "1130951910",
    #                         "1130951855",
    #                         "1130951510",
    #                         "1130951550",
    #                         "1130951549",
    #                         "1130951548",
    #                         "1130951547",
    #                         "1130951546",
    #                         "1130951545",
    #                         "1130951628",
    #                         "1130951629",
    #                         "1130951827",
    #                         "1130951828",
    #                         "1130951829",
    #                         "1130951639",
    #                         "1130951638",
    #                         "1130951596",
    #                         "1130951595",
    #                         "1130951536",
    #                         "1130951804",
    #                         "1130951803",
    #                         "1130951802",
    #                         "1130951801",
    #                         "1130951923"
    #                     ],
    #                     "length": 333.0377679230925,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 185,
    #                         "price": 207.8
    #                     },
    #                     "from_building": "246032665",
    #                     "to_building": "170944167",
    #                     "mass_flow": 1.6518783677591768,
    #                     "pipe_cost": 69205.24817441862,
    #                     "trench_cost": 31473.23470091998
    #                 }
    #             ],
    #             "supplied_power": 245.68956132095434,
    #             "pipe_investment_cost": 85300.85332511047,
    #             "trench_cost": 38793.21074210577,
    #             "total_pipe_cost": 124094.06406721624,
    #             "total_cost": 224094.06406721624,
    #             "fitness": 912.1025039174252,
    #             "members": [
    #                 "170944167",
    #                 "246032665",
    #                 "249672012"
    #             ]
    #         },
    #         {
    #             "cluster_center": "170766316",
    #             "pipe_result": [
    #                 {
    #                     "id": [
    #                         "1130951891",
    #                         "1130951853",
    #                         "1130951694",
    #                         "1130951693",
    #                         "1130951548",
    #                         "1130951620",
    #                         "1130951611",
    #                         "1130951610",
    #                         "1130951820",
    #                         "1130951945"
    #                     ],
    #                     "length": 87.37190985546108,
    #                     "pipe_type": {
    #                         "type": "duo",
    #                         "outer_diameter": 113,
    #                         "price": 88.7
    #                     },
    #                     "from_building": "170766316",
    #                     "to_building": "256314771",
    #                     "mass_flow": 0.30145490618268844,
    #                     "pipe_cost": 7749.888404179398,
    #                     "trench_cost": 6052.159581463343
    #                 }
    #             ],
    #             "supplied_power": 242.07239591535287,
    #             "pipe_investment_cost": 7749.888404179398,
    #             "trench_cost": 6052.159581463343,
    #             "total_pipe_cost": 13802.047985642741,
    #             "total_cost": 113802.04798564274,
    #             "fitness": 470.1157583677434,
    #             "members": [
    #                 "256314771",
    #                 "170766316"
    #             ]
    #         },
    #         {
    #             "cluster_center": "-1",
    #             "members": [
    #                 "170766314",
    #                 "170944168",
    #                 "170944155",
    #                 "256322121",
    #                 "246032669",
    #                 "170944165",
    #                 "172146674",
    #                 "170766331",
    #                 "256314773",
    #                 "249672014",
    #                 "170766324",
    #                 "246032663",
    #                 "170944154",
    #                 "249861107",
    #                 "172146673",
    #                 "172146670",
    #                 "170944166",
    #                 "35405800",
    #                 "170944162",
    #                 "170766321",
    #                 "256314766",
    #                 "172146677",
    #                 "172146684",
    #                 "256314765",
    #                 "256314769",
    #                 "253692527",
    #                 "170944152",
    #                 "249672015",
    #                 "170944163",
    #                 "170944159",
    #                 "172146681",
    #                 "256314767",
    #                 "172146680"
    #             ]
    #         }
    #     ]
    # }
        self.visualization.set_required_fields(preprocessing_result.exploded_roads, clustering_second_stage_results,
                                               preprocessing_result.building_centroids)
        self.visualization.start()
        #
        # random_items = dict(random.sample(building_to_point_dict.items(), 5)).values()
        # ToDo: testing...
        # self.mst_creator.visualize_subgraph_mst(shortest_paths, random_items)
        # Logger().info("Finished MST Creation.")


    def timed_wrapper(self, function_call, *args, **kwargs):
        function_name = self.get_fully_qualified_name(function_call)
        start_time = time.time()
        result = function_call(*args, **kwargs)
        end_time = time.time()
        Logger().info(f"Function {function_name} took {end_time - start_time} seconds.")
        return result

    @staticmethod
    def get_fully_qualified_name(function_call):
        """Returns the fully qualified name of a function."""
        if hasattr(function_call, "__self__") and function_call.__self__:
            # Method of a class instance
            class_name = function_call.__self__.__class__.__name__
            return f"{class_name}.{function_call.__name__}"
        elif hasattr(function_call, "__module__"):
            # Function from a module
            return f"{function_call.__module__}.{function_call.__name__}"
        else:
            # Standalone function
            return function_call.__name__
