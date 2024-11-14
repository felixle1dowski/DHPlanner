from abc import ABC, abstractmethod

class DHCCreationPipeline(ABC):

    @abstractmethod
    def start(self):
        pass