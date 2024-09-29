from enum import Enum, auto


class LogMessages(Enum):
    """
    Enum class to represent different types of log messages dynamically.
    """

    DUPLICATED_VARIABLE = auto()
    OPTIMIZATION_ERROR = auto()
    DUPLICATED_CONSTRAINT = auto()
    VARIABLE_NOT_FOUND = auto()
    VARIABLE_DATA_MISSING = auto()
    BUILD_MODEL_ERROR = auto()
    UNRELATED_VARIABLES = auto()
    INPUT_NAME_NOT_MATCHING = auto()
    OUTPUT_WRITING_ERROR = auto()
