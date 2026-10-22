from enum import Enum

class RelationType(Enum):
    CALLS = "calls"
    IMPORTS = "imports"
    INDIRECT_CALL = "indirect_call"    
    IMPORTS_FROM = "imports_from"
    SUBMODULE_IMPORT = "submodule_import"
    CONTAINS = "contains"
    METHOD = "method"
    INHERITS = "inherits"
    RE_EXPORTS = "re_exports"
    USES = "uses"
    REFERENCES = "references"
    RATIONALE_FOR = "rationale_for"
    HAS_CODE = "has_chunk"
    UNKNOWN = "unknown"                  

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN



class LinkContext(str, Enum):
    CALL = "call"
    IMPORT = "import"
    SUBMODULE_IMPORT = "submodule_import"
    EXPORT = "export"
    DECORATOR = "decorator"
    PARAMETER_TYPE = "parameter_type"
    RETURN_TYPE = "return_type"
    GENERIC_ARG = "generic_arg"
    ARGUMENT = "argument"           
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


