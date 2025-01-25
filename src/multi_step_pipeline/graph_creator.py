from .graph_creator_greenfield import GraphCreatorGreenfield
from .graph_creator_street_following import GraphCreatorStreetFollowing
from ..util.not_yet_implemented_exception import NotYetImplementedException


class GraphCreator:

    @staticmethod
    def start(strategy: str, **kwargs):
        # ToDo: All of THIS has to be in the invoking class!
        # ToDo: This is a crutch for now. This Creator has to be a parent class for the other two strategies!
        graph_creator = None
        if strategy == "greenfield":
            if "building_centroids" not in kwargs.keys():
                raise Exception("Graph could not be created: centroids not provided")
            else:
                graph_creator = GraphCreatorGreenfield(kwargs["building_centroids"])
                # ToDo: Be diligent! Don't have one rely on __init__ and the other on a setter!!!
                graph_creator.start()
        elif strategy == "street-following":
            exception_string = ""
            if "exploded_roads" not in kwargs.keys():
                exception_string += " exploded_roads not provided"
            if "building_centroids" not in kwargs.keys():
                exception_string += " building_centroids not provided"
            if exception_string != "":
                raise Exception("Graph could not be created: " + exception_string)
            else:
                graph_creator = GraphCreatorStreetFollowing()
                graph_creator.set_required_fields(exploded_roads=kwargs["exploded_roads"],
                                                  building_centroids=kwargs["building_centroids"])
        else:
            raise NotYetImplementedException(f"Strategy {strategy} is not implemented")
        result = graph_creator.start()
        return result