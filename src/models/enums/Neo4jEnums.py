from enum import Enum


class ProjectSource(str, Enum):
    GITHUB = "github"
    LOCAL = "local"


class CallConfidence(str, Enum):
    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    BUILTIN = "BUILTIN"


class RelationType(str, Enum):
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    CONTAINS = "CONTAINS"
    HAS_METHOD = "HAS_METHOD"
    INHERITS = "INHERITS"