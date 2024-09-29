import logging
from typing import Any
from JsonFormatter import JsonFormatter
from oahf.Base.Entity import Entity

class Logger(Entity):
    """
    Custom class to encapsulate the logging process with JSON formatting.
    
    This class allows creating logs with different severity levels 
    (DEBUG, INFO, WARNING, ERROR, CRITICAL) and records them in a JSON file.
    """

    def __init__(self, log_file: str, level: int = logging.DEBUG) -> None:
        """
        Initializes the logger with a log file and the specified level.
        
        Args:
            log_file (str): The path to the file where logs will be recorded.
            level (int): The logging level. The default is DEBUG.
        """
        super().__init__()
        self.logger: logging.Logger = logging.getLogger('JsonLogger')
        self.logger.setLevel(level)
        
        # Create a FileHandler to direct logs to the specified file
        file_handler: logging.FileHandler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Set the custom format as JSON
        formatter: JsonFormatter = JsonFormatter()
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        self.logger.addHandler(file_handler)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a debug message.
        
        Args:
            message (str): The log message.
        """
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs an informational message.
        
        Args:
            message (str): The log message.
        """
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a warning message.
        
        Args:
            message (str): The log message.
        """
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs an error message.
        
        Args:
            message (str): The log message.
        """
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a critical message.
        
        Args:
            message (str): The log message.
        """
        self.logger.critical(message, *args, **kwargs)

# Example of using the custom logger class
#if __name__ == "__main__":
#    # Create a logger that logs to logs.json
#    json_logger = Logger(log_file='logs.json')
#
#    # Example log entries
#    json_logger.debug("Debug message")
#    json_logger.info("Informational message")
#    json_logger.warning("Warning")
#    json_logger.error("Error encountered")
#    json_logger.critical("Critical error")
