import logging
from pathlib import Path
from typing import Any

from oahf.Base.Entity import Entity
from oahf.Logger.JsonFormatter import JsonFormatter
from oahf.Logger.JsonListFileHandler import JsonListFileHandler


class Logger(Entity):
    def __init__(
        self, log_file: str = "log.json", level: int = logging.DEBUG, show_messages=True
    ) -> None:
        """
        Initializes the logger with a log file and the specified level.

        Args:
            log_file (str): The path to the file where logs will be recorded.
            level (int): The logging level. The default is DEBUG.
        """
        super().__init__()
        from oahf.Utils.Util import Util

        self.logger: logging.Logger = logging.getLogger("JsonLogger")
        self.logger.setLevel(level)
        self.show_messages = show_messages

        self.format = ".json"
        if self.format not in log_file:
            log_file += self.format

        full_log_file = Path(
            Util.default_output_path(),
            Util.input_name(),
            Util.get_optimization_start_time(),
            log_file,
        )
        full_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use the custom JSON list handler
        file_handler = JsonListFileHandler(full_log_file)
        file_handler.setLevel(level)

        # Set the custom JSON formatter
        formatter = JsonFormatter()
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def show_message(self, message: str):
        if self.show_messages:
            print(message)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a debug message.

        Args:
            message (str): The log message.
        """
        self.logger.debug(message, *args, **kwargs)
        self.show_message(message)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs an informational message.

        Args:
            message (str): The log message.
        """
        self.logger.info(message, *args, **kwargs)
        self.show_message(message)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a warning message.

        Args:
            message (str): The log message.
        """
        self.logger.warning(message, *args, **kwargs)
        self.show_message(message)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs an error message.

        Args:
            message (str): The log message.
        """
        self.logger.error(message, *args, **kwargs)
        self.show_message(message)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a critical message.

        Args:
            message (str): The log message.
        """
        self.logger.critical(message, *args, **kwargs)
        self.show_message(message)
