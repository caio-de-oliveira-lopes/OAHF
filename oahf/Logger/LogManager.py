import os
import json
from pathlib import Path
from typing import Dict, Optional, Union

from oahf.Base.Evaluation import Evaluation
from oahf.Logger.LogMessages import LogMessages
from oahf.Utils.Util import Util


class LogManager:
    """Static class to manage and retrieve log messages from a JSON file."""

    _log_messages: Dict[LogMessages, str] = {}

    @classmethod
    def __load_messages_from_json(cls, json_file: Path) -> None:
        """Load log messages from a JSON file into the internal dictionary."""
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            for key, message in data.items():
                if not key:
                    continue
                try:
                    cls._log_messages[LogMessages[key]] = message
                except KeyError:
                    Util.logger().warning(f"Unknown log key '{key}' in JSON file.")
        except Exception as e:
            cls.something_went_wrong(cls.__name__, e)

    @staticmethod
    def get_message(message_type: LogMessages) -> str:
        """Get the log message by message type."""
        if not LogManager._log_messages:
            current_directory = Path(__file__).parent
            json_path = current_directory / "LogMessages.json"
            LogManager.__load_messages_from_json(json_path)

        return LogManager._log_messages.get(message_type, "Message not found")

    @classmethod
    def something_went_wrong(cls, name: str, ex: Union[Exception, str]):
        log_key: LogMessages = LogMessages.SOMETHING_WENT_WRONG
        Util.logger().error(LogManager.get_message(log_key).format(name, ex))

    @classmethod
    def unable_to_get_neighborhood(cls):
        log_key: LogMessages = LogMessages.UNABLE_TO_GET_NEIGHBORHOOD
        Util.logger().error(LogManager.get_message(log_key))

    @classmethod
    def log_solution(cls, evaluation: Evaluation):
        log_key: LogMessages = LogMessages.LOG_SOLUTION
        Util.logger().info(LogManager.get_message(log_key).format(evaluation))

    @classmethod
    def invalid_action(cls, action: str, name: str, ex: Optional[Exception] = None):
        log_key: LogMessages = LogMessages.INVALID_ACTION
        Util.logger().error(LogManager.get_message(log_key).format(action, name))

        if ex:
            cls.something_went_wrong(name, ex)