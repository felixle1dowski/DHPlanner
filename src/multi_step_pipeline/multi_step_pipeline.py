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
        # self.shortest_path_creator.set_required_fields(graph, line_layer, list(building_to_point_dict.values()))
        # shortest_paths = self.shortest_path_creator.start()
        #
        # if Config().get_distance_measuring_method() == "custom":
        #     # ToDo: Put this into function!
        #     adjacency_matrix = nx.adjacency_matrix(shortest_paths).todense()
        #     nodes = list(shortest_paths.nodes())
        #     # translate nodes
        #     translated_nodes = []
        #     reverse_translation = dict(zip(building_to_point_dict.values(), building_to_point_dict.keys()))
        #     for node in nodes:
        #         translated_nodes.append(reverse_translation[node])
        #     self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids,
        #                                                     adjacency_matrix,
        #                                                     translated_nodes)
        # else:
        #     self.clustering_first_stage.set_required_fields(preprocessing_result.building_centroids)
        # clustering_first_stage_results = self.clustering_first_stage.start()
        #
        # self.clustering_second_stage.set_required_fields(shortest_path_graph=shortest_paths,
        #                                                 first_stage_cluster_dict=clustering_first_stage_results,
        #                                                  # ToDo: This is only in because of sloppy visualization. Remove!!
        #                                                  buildings_layer=QgsProject.instance().mapLayersByName(Config().get_buildings_layer_name())[0],
        #                                                  building_centroids_layer=preprocessing_result.building_centroids,
        #                                                  feasible_solution_creator=self.feasible_solution_creator,
        #                                                  graph_translation_dict=building_to_point_dict)
        # clustering_second_stage_results = self.clustering_second_stage.start()

        clustering_second_stage_results = {'sums': {'sum_of_supplied_power': 3456.577550077139, 'sum_of_total_pipe_cost': 384592.94165053626,
                  'sum_of_total_cost': 1884592.9416505366, 'sum_of_fitness': 8216.052771286799}, 'clusters': [
            {'cluster_center': '170944151', 'pipe_result': [{'id': ['1130951896', '1130951783', '1130951603',
                                                                    '1130951602', '1130951501', '1130951787',
                                                                    '1130951898'], 'length': 129.0185213957052,
                                                             'pipe_type': {'type': 'duo', 'outer_diameter': 128,
                                                                           'price': 101.9},
                                                             'from_building': '170944151', 'to_building': '170944154',
                                                             'mass_flow': 0.48145784217223675,
                                                             'pipe_cost': 13146.98733022236}, {
                                                                'id': ['1130951896', '1130951784', '1130951489',
                                                                       '1130951490', '1130951785', '1130951786',
                                                                       '1130951586', '1130951812', '1130951811',
                                                                       '1130951810', '1130951809', '1130951808',
                                                                       '1130951904'], 'length': 244.80489417300967,
                                                                'pipe_type': {'type': 'duo', 'outer_diameter': 164,
                                                                              'price': 149.6},
                                                                'from_building': '170944151',
                                                                'to_building': '170944160',
                                                                'mass_flow': 1.0416913295328394,
                                                                'pipe_cost': 36622.812168282246}],
             'supplied_power': 248.13456508863985, 'total_pipe_cost': 49769.79949850461,
             'total_cost': 149769.7994985046, 'fitness': 603.5829770229839,
             'members': ['170944160', '170944154', '170944151']}, {'cluster_center': '249861107', 'pipe_result': [
                {'id': ['1130951907', '1130951835', '1130951657', '1130951934'], 'length': 22.261425481481233,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '249861107',
                 'to_building': '170944163', 'mass_flow': 1.0223285930241752, 'pipe_cost': 3330.3092520295922},
                {'id': ['1130951899', '1130951812', '1130951834', '1130951907'], 'length': 34.05029345041639,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9}, 'from_building': '170944163',
                 'to_building': '170944155', 'mass_flow': 0.6387604513074815, 'pipe_cost': 3469.72490259743},
                {'id': ['1130951899', '1130951811', '1130951810', '1130951905'], 'length': 46.34062605184752,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5}, 'from_building': '170944155',
                 'to_building': '170944161', 'mass_flow': 0.1869194407750672, 'pipe_cost': 3684.079771121878},
                {'id': ['1130951899', '1130951812', '1130951586', '1130951786', '1130951940'],
                 'length': 51.63844793331785, 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7},
                 'from_building': '170944155', 'to_building': '256314766', 'mass_flow': 0.25752615698076164,
                 'pipe_cost': 4580.3303316852935}], 'supplied_power': 230.71299501592762,
                                                                   'total_pipe_cost': 15064.444257434196,
                                                                   'total_cost': 115064.4442574342,
                                                                   'fitness': 498.7341274360837,
                                                                   'members': ['256314766', '170944163', '170944161',
                                                                               '170944155', '249861107']},
            {'cluster_center': '172146677', 'pipe_result': [{'id': ['1130951890', '1130951852', '1130951692',
                                                                    '1130951542', '1130951541', '1130951540',
                                                                    '1130951760', '1130951759', '1130951479',
                                                                    '1130951539', '1130951767', '1130951597',
                                                                    '1130951596', '1130951638', '1130951639',
                                                                    '1130951830', '1130951917'],
                                                             'length': 258.5642807469102,
                                                             'pipe_type': {'type': 'duo', 'outer_diameter': 164,
                                                                           'price': 149.6},
                                                             'from_building': '172146677', 'to_building': '170766315',
                                                             'mass_flow': 1.2073512255164063,
                                                             'pipe_cost': 38681.216399737765}],
             'supplied_power': 235.82180352910115, 'total_pipe_cost': 38681.216399737765,
             'total_cost': 138681.21639973775, 'fitness': 588.0763115384455, 'members': ['170766315', '172146677']},
            {'cluster_center': '253692529', 'pipe_result': [{'id': ['1130951889', '1130951713', '1130951711',
                                                                    '1130951559', '1130951826', '1130951825',
                                                                    '1130951824', '1130951556', '1130951555',
                                                                    '1130951554', '1130951553', '1130951873',
                                                                    '1130951938'], 'length': 154.28040895821997,
                                                             'pipe_type': {'type': 'duo', 'outer_diameter': 185,
                                                                           'price': 207.8},
                                                             'from_building': '253692529', 'to_building': '170766314',
                                                             'mass_flow': 1.4179167822722798,
                                                             'pipe_cost': 32059.468981518112}],
             'supplied_power': 228.2418998068092, 'total_pipe_cost': 32059.468981518112,
             'total_cost': 132059.46898151812, 'fitness': 578.59432949558, 'members': ['170766314', '253692529']},
            {'cluster_center': '256314767', 'pipe_result': [
                {'id': ['1130951893', '1130951825', '1130951941'], 'length': 15.000000000013388,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '256314767',
                 'to_building': '170766321', 'mass_flow': 1.0559360897549461, 'pipe_cost': 2244.0000000020027},
                {'id': ['1130951893', '1130951824', '1130951805', '1130951939'], 'length': 40.00000000001907,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '170766321',
                 'to_building': '256314765', 'mass_flow': 0.7791998874279709, 'pipe_cost': 5984.000000002853},
                {'id': ['1130951885', '1130951813', '1130951490', '1130951806', '1130951939'],
                 'length': 42.88211654105266, 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7},
                 'from_building': '256314765', 'to_building': '32789077', 'mass_flow': 0.3450139508083661,
                 'pipe_cost': 3803.643737191371},
                {'id': ['1130951903', '1130951781', '1130951782', '1130951489', '1130951806', '1130951939'],
                 'length': 133.2091948573473, 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5},
                 'from_building': '256314765', 'to_building': '170944159', 'mass_flow': 0.1791740779360311,
                 'pipe_cost': 10590.13099115911}], 'supplied_power': 170.9615855722678,
             'total_pipe_cost': 22621.77472835534, 'total_cost': 122621.77472835535, 'fitness': 717.2475285479933,
             'members': ['170766321', '32789077', '256314765', '170944159', '256314767']},
            {'cluster_center': '249672017', 'pipe_result': [
                {'id': ['1130951932', '1130951795', '1130951933'], 'length': 15.000000000026725,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '249672017',
                 'to_building': '249672015', 'mass_flow': 0.9530068779798077, 'pipe_cost': 2244.000000003998},
                {'id': ['1130951916', '1130951794', '1130951933'], 'length': 19.99999999995878,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '249672017',
                 'to_building': '172146675', 'mass_flow': 0.7817741540405599, 'pipe_cost': 2991.9999999938336},
                {'id': ['1130951914', '1130951717', '1130951796', '1130951932'], 'length': 19.35339873117868,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '249672015',
                 'to_building': '172146673', 'mass_flow': 0.8111197345433946, 'pipe_cost': 2895.26845018433},
                {'id': ['1130951914', '1130951858', '1130951929'], 'length': 8.612111470213893,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9}, 'from_building': '172146673',
                 'to_building': '249672012', 'mass_flow': 0.6662064382084723, 'pipe_cost': 877.5741588147957},
                {'id': ['1130951929', '1130951859', '1130951720', '1130951930'], 'length': 16.493528754027178,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5}, 'from_building': '249672012',
                 'to_building': '249672013', 'mass_flow': 0.17093173746570242, 'pipe_cost': 1311.2355359451606}, {
                    'id': ['1130951929', '1130951859', '1130951722', '1130951723', '1130951724', '1130951861',
                           '1130951931'], 'length': 39.61390361076257,
                    'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7}, 'from_building': '249672012',
                    'to_building': '249672014', 'mass_flow': 0.32722713540132303, 'pipe_cost': 3513.75325027464},
                {'id': ['1130951921', '1130951863', '1130951727', '1130951728', '1130951861', '1130951931'],
                 'length': 26.009342121234255, 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5},
                 'from_building': '249672014', 'to_building': '172146684', 'mass_flow': 0.16497590706147927,
                 'pipe_cost': 2067.7426986381233},
                {'id': ['1130951916', '1130951793', '1130951531', '1130951874', '1130951949'],
                 'length': 110.25172563262605, 'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9},
                 'from_building': '172146675', 'to_building': '256322122', 'mass_flow': 0.642177644501731,
                 'pipe_cost': 11234.650841964594}, {
                    'id': ['1130951892', '1130951846', '1130951845', '1130951473', '1130951530', '1130951874',
                           '1130951949'], 'length': 94.1236497388908,
                    'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9}, 'from_building': '256322122',
                    'to_building': '170766319', 'mass_flow': 0.4988058435848941, 'pipe_cost': 9591.199908392973}],
             'supplied_power': 237.4980885944503, 'total_pipe_cost': 36727.42484421245,
             'total_cost': 136727.42484421245, 'fitness': 575.6990536361201,
             'members': ['249672013', '249672015', '172146684', '170766319', '172146673', '249672014', '256322122',
                         '249672012', '172146675', '249672017']}, {'cluster_center': '246032667', 'pipe_result': [
                {'id': ['1130951923', '1130951801', '1130951802', '1130951924'], 'length': 17.35402770321305,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '246032667',
                 'to_building': '246032665', 'mass_flow': 1.306490809503311, 'pipe_cost': 2596.1625444006722},
                {'id': ['1130951913', '1130951864', '1130951729', '1130951802', '1130951924'],
                 'length': 41.40880129330723, 'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9},
                 'from_building': '246032667', 'to_building': '172146671', 'mass_flow': 0.4297052583130038,
                 'pipe_cost': 4219.5568517880065},
                {'id': ['1130951922', '1130951800', '1130951923'], 'length': 15.00000000003645,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '246032665',
                 'to_building': '246032663', 'mass_flow': 1.1723506570622886, 'pipe_cost': 2244.000000005453},
                {'id': ['1130951922', '1130951799', '1130951798', '1130951928'], 'length': 32.050196791078484,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5}, 'from_building': '246032663',
                 'to_building': '249672011', 'mass_flow': 0.1524953942878839, 'pipe_cost': 2547.9906448907395},
                {'id': ['1130951922', '1130951799', '1130951463', '1130951878', '1130951877', '1130951950'],
                 'length': 119.20806346426461, 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6},
                 'from_building': '246032663', 'to_building': '256322123', 'mass_flow': 0.8845118375188092,
                 'pipe_cost': 17833.526294253985}, {
                    'id': ['1130951888', '1130951782', '1130951784', '1130951783', '1130951467', '1130951466',
                           '1130951465', '1130951464', '1130951878', '1130951877', '1130951950'],
                    'length': 257.78623691240693, 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6},
                    'from_building': '256322123', 'to_building': '35405801', 'mass_flow': 0.737088087908686,
                    'pipe_cost': 38564.821042096075}, {'id': ['1130951913', '1130951918'], 'length': 0,
                                                       'pipe_type': {'type': 'duo', 'outer_diameter': 113,
                                                                     'price': 88.7}, 'from_building': '172146671',
                                                       'to_building': '172146678', 'mass_flow': 0.21348648384189758,
                                                       'pipe_cost': 0.0}], 'supplied_power': 248.47666183392403,
                                                                   'total_pipe_cost': 68006.05737743493,
                                                                   'total_cost': 168006.05737743492,
                                                                   'fitness': 676.1442146616016,
                                                                   'members': ['172146678', '256322123', '172146671',
                                                                               '246032665', '246032663', '35405801',
                                                                               '249672011', '246032667']},
            {'cluster_center': '170944167', 'pipe_result': {}, 'supplied_power': 206.93060858534577,
             'total_pipe_cost': 0, 'total_cost': 100000.0, 'fitness': 483.2537858156269, 'members': ['170944167']},
            {'cluster_center': '256314773', 'pipe_result': [
                {'id': ['1130951946', '1130951816', '1130951947'], 'length': 14.999999999992356,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 185, 'price': 207.8}, 'from_building': '256314773',
                 'to_building': '256314772', 'mass_flow': 1.643988508588918, 'pipe_cost': 3116.999999998412},
                {'id': ['1130951944', '1130951818', '1130951815', '1130951946'], 'length': 34.99999999998563,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9}, 'from_building': '256314772',
                 'to_building': '256314770', 'mass_flow': 0.6020757541948538, 'pipe_cost': 3566.499999998536}, {
                    'id': ['1130951942', '1130951821', '1130951760', '1130951540', '1130951604', '1130951815',
                           '1130951946'], 'length': 69.58987208910533,
                    'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7}, 'from_building': '256314772',
                    'to_building': '256314768', 'mass_flow': 0.3013237045464121, 'pipe_cost': 6172.621654303643}, {
                    'id': ['1130951946', '1130951815', '1130951604', '1130951541', '1130951542', '1130951543',
                           '1130951849', '1130951948'], 'length': 75.95861017020124,
                    'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9}, 'from_building': '256314772',
                    'to_building': '256322121', 'mass_flow': 0.43252320346187045, 'pipe_cost': 7740.182376343507},
                {'id': ['1130951944', '1130951819', '1130951608', '1130951945'], 'length': 13.33513023295631,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7}, 'from_building': '256314770',
                 'to_building': '256314771', 'mass_flow': 0.30145490618268844, 'pipe_cost': 1182.8260516632247}],
             'supplied_power': 247.81359403820105, 'total_pipe_cost': 21779.13008230732,
             'total_cost': 121779.13008230733, 'fitness': 491.4142444644695,
             'members': ['256314768', '256322121', '256314772', '256314770', '256314771', '256314773']},
            {'cluster_center': '249672006', 'pipe_result': [
                {'id': ['1130951926', '1130951876', '1130951877', '1130951927'], 'length': 34.99999999996926,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 185, 'price': 207.8}, 'from_building': '249672006',
                 'to_building': '249672010', 'mass_flow': 1.7349649725533942, 'pipe_cost': 7272.999999993613},
                {'id': ['1130951920', '1130951879', '1130951878', '1130951927'], 'length': 58.408012723364564,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '249672010',
                 'to_building': '172146681', 'mass_flow': 0.9528965244168252, 'pipe_cost': 8737.838703415338},
                {'id': ['1130951894', '1130951848', '1130951475', '1130951464', '1130951878', '1130951927'],
                 'length': 85.7729147448753, 'pipe_type': {'type': 'duo', 'outer_diameter': 128, 'price': 101.9},
                 'from_building': '249672010', 'to_building': '170766324', 'mass_flow': 0.6364794525497881,
                 'pipe_cost': 8740.260012502793},
                {'id': ['1130951894', '1130951688', '1130951687', '1130951847', '1130951846', '1130951901'],
                 'length': 43.0236991465849, 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5},
                 'from_building': '170766324', 'to_building': '170944157', 'mass_flow': 0.15600592280947514,
                 'pipe_cost': 3420.3840821535}], 'supplied_power': 237.8992912069363,
             'total_pipe_cost': 28171.482798065244, 'total_cost': 128171.48279806525, 'fitness': 538.7636177804981,
             'members': ['172146681', '170766324', '249672010', '170944157', '249672006']},
            {'cluster_center': '170944162', 'pipe_result': [
                {'id': ['1130951906', '1130951838', '1130951837', '1130951909'], 'length': 14.623066093633138,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 185, 'price': 207.8}, 'from_building': '170944162',
                 'to_building': '170944166', 'mass_flow': 1.524009926078088, 'pipe_cost': 3038.6731342569665},
                {'id': ['1130951902', '1130951839', '1130951906'], 'length': 25.59740303509617,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7}, 'from_building': '170944162',
                 'to_building': '170944158', 'mass_flow': 0.2066359508521963, 'pipe_cost': 2270.4896492130306}],
             'supplied_power': 243.1370426502681, 'total_pipe_cost': 5309.1627834699975, 'total_cost': 105309.16278347,
             'fitness': 433.1267734260807, 'members': ['170944166', '170944158', '170944162']},
            {'cluster_center': '172146674', 'pipe_result': [
                {'id': ['1130951912', '1130951828', '1130951915'], 'length': 20.00000000000083,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6}, 'from_building': '172146674',
                 'to_building': '172146670', 'mass_flow': 1.2687486511397816, 'pipe_cost': 2992.000000000124}, {
                    'id': ['1130951915', '1130951829', '1130951639', '1130951638', '1130951596', '1130951595',
                           '1130951536', '1130951804', '1130951925'], 'length': 71.05075357716129,
                    'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 88.7}, 'from_building': '172146674',
                    'to_building': '246032669', 'mass_flow': 0.23970797021035503, 'pipe_cost': 6302.2018422942065},
                {'id': ['1130951912', '1130951827', '1130951629', '1130951881', '1130951919'],
                 'length': 49.76868761663005, 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6},
                 'from_building': '172146670', 'to_building': '172146680', 'mass_flow': 1.0961737040790989,
                 'pipe_cost': 7445.395667447855}], 'supplied_power': 210.36510999218567,
             'total_pipe_cost': 16739.597509742187, 'total_cost': 116739.59750974219, 'fitness': 554.9380194941959,
             'members': ['172146680', '172146670', '246032669', '172146674']}, {'cluster_center': '253692526',
                                                                                'pipe_result': [{'id': ['1130951935',
                                                                                                        '1130951869',
                                                                                                        '1130951936'],
                                                                                                 'length': 4.999999999984269,
                                                                                                 'pipe_type': {
                                                                                                     'type': 'duo',
                                                                                                     'outer_diameter': 164,
                                                                                                     'price': 149.6},
                                                                                                 'from_building': '253692526',
                                                                                                 'to_building': '253692527',
                                                                                                 'mass_flow': 1.3861371590816338,
                                                                                                 'pipe_cost': 747.9999999976466},
                                                                                                {'id': ['1130951935',
                                                                                                        '1130951870',
                                                                                                        '1130951937'],
                                                                                                 'length': 8.071077198914287,
                                                                                                 'pipe_type': {
                                                                                                     'type': 'duo',
                                                                                                     'outer_diameter': 113,
                                                                                                     'price': 88.7},
                                                                                                 'from_building': '253692526',
                                                                                                 'to_building': '253692528',
                                                                                                 'mass_flow': 0.232196781788697,
                                                                                                 'pipe_cost': 715.9045475436973},
                                                                                                {'id': ['1130951895',
                                                                                                        '1130951867',
                                                                                                        '1130951936'],
                                                                                                 'length': 7.942906032721494,
                                                                                                 'pipe_type': {
                                                                                                     'type': 'duo',
                                                                                                     'outer_diameter': 164,
                                                                                                     'price': 149.6},
                                                                                                 'from_building': '253692527',
                                                                                                 'to_building': '170766331',
                                                                                                 'mass_flow': 1.1094816614887797,
                                                                                                 'pipe_cost': 1188.2587424951355},
                                                                                                {'id': ['1130951887',
                                                                                                        '1130951844',
                                                                                                        '1130951523',
                                                                                                        '1130951469',
                                                                                                        '1130951784',
                                                                                                        '1130951783',
                                                                                                        '1130951467',
                                                                                                        '1130951551',
                                                                                                        '1130951866',
                                                                                                        '1130951895'],
                                                                                                 'length': 253.68961389047493,
                                                                                                 'pipe_type': {
                                                                                                     'type': 'duo',
                                                                                                     'outer_diameter': 128,
                                                                                                     'price': 101.9},
                                                                                                 'from_building': '170766331',
                                                                                                 'to_building': '35405800',
                                                                                                 'mass_flow': 0.6914697914254142,
                                                                                                 'pipe_cost': 25850.971655439396}],
                                                                                'supplied_power': 240.82045679380488,
                                                                                'total_pipe_cost': 28503.134945475875,
                                                                                'total_cost': 128503.13494547587,
                                                                                'fitness': 533.605560990621,
                                                                                'members': ['253692527', '253692528',
                                                                                            '35405800', '170766331',
                                                                                            '253692526']},
            {'cluster_center': '170766316', 'pipe_result': [{'id': ['1130951891', '1130951853', '1130951694',
                                                                    '1130951693', '1130951548', '1130951547',
                                                                    '1130951546', '1130951823', '1130951943'],
                                                             'length': 101.63034435790351,
                                                             'pipe_type': {'type': 'duo', 'outer_diameter': 113,
                                                                           'price': 88.7}, 'from_building': '170766316',
                                                             'to_building': '256314769',
                                                             'mass_flow': 0.3014545434574689,
                                                             'pipe_cost': 9014.611544546042}],
             'supplied_power': 242.07235047680734, 'total_pipe_cost': 9014.611544546042,
             'total_cost': 109014.61154454605, 'fitness': 450.33896407343144, 'members': ['256314769', '170766316']},
            {'cluster_center': '170944165', 'pipe_result': [
                {'id': ['1130951900', '1130951841', '1130951790', '1130951908'], 'length': 18.028414372138407,
                 'pipe_type': {'type': 'duo', 'outer_diameter': 113, 'price': 79.5}, 'from_building': '170944165',
                 'to_building': '170944156', 'mass_flow': 0.18962553549359717, 'pipe_cost': 1433.2589425850033},
                {'id': ['1130951886', '1130951791', '1130951526', '1130951525', '1130951790', '1130951908'],
                 'length': 71.60679784189308, 'pipe_type': {'type': 'duo', 'outer_diameter': 164, 'price': 149.6},
                 'from_building': '170944165', 'to_building': '35405799', 'mass_flow': 0.7516409772326829,
                 'pipe_cost': 10712.376957147206}], 'supplied_power': 227.69149689246996,
             'total_pipe_cost': 12145.63589973221, 'total_cost': 112145.63589973221, 'fitness': 492.53326290306893,
             'members': ['35405799', '170944156', '170944165']},
            {'cluster_center': '-1', 'members': ['170944168', '170944152']}]}
        self.visualization.set_required_fields(preprocessing_result.exploded_roads, clustering_second_stage_results)
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
