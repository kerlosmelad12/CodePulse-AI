from ..ParserInterface import ParserInterface
import tree_sitter_python
from tree_sitter import Language, Parser 


class PythonParser(ParserInterface):

    def __init__(self):
        super().__init__()
        self.parser= self.initlize_parser()
        

    def initlize_parser(self):
        PY_LANGUAGE = Language(tree_sitter_python.language())
        parser = Parser(PY_LANGUAGE)
        return parser

    def getfile_root_node(self,source_code:str):
        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node
        return root_node

    

    

    

    

        


        