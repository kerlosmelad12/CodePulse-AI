from enum import Enum


class FileType(Enum):
    CODE = "code"
    CONCEPT = "concept"
    RATIONALE = "rationale"

class DataOrigin(Enum):
    AST = "ast"
