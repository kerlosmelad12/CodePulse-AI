from abc import ABC , abstractmethod
from .ParserEnums import ParserLanguages

class ParserInterface(ABC):


    @abstractmethod 
    def initlize_parser(self):
        pass

    @abstractmethod 
    def getfile_root_node(self,source_code:str):
        pass




    


