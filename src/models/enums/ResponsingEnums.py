from enum import Enum

class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"


class ResponseMessage(Enum):
    INDEXED = "indexed"
    NOT_INDEXED = "not_indexed"
    CLONED = "cloned"
    PARSING_FAILD="No valid Python files found in the repository."
    PARSING_SUCCESS="Parsing completed successfully."
    