from enum import Enum, auto


class LogMessages(Enum):
    """
    Enum class to represent different types of log messages dynamically.
    """

    DUPLICATED_VARIABLE = auto()
    OPTIMIZATION_ERROR = auto()
    DUPLICATED_CONSTRAINT = auto()
    VARIABLE_NOT_FOUND = auto()
    BUILD_MODEL_ERROR = auto()
    OUTPUT_WRITING_ERROR = auto()
    SOMETHING_WENT_WRONG = auto()
    UNABLE_TO_GET_NEIGHBORHOOD = auto()
    LOG_SOLUTION = auto()
    INVALID_ACTION = auto()
