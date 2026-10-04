from enum import Enum

class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class IndexingStatus(Enum):
    INDEXED = "indexed"
    NOT_INDEXED = "not_indexed"
    CLONED = "cloned"
    