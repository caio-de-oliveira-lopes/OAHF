import os
from pathlib import Path
from typing import Dict, Optional, Union

from defusedxml.ElementTree import parse

from oahf.Base.Evaluation import Evaluation
from oahf.Logger.LogMessages import LogMessages
from oahf.Utils.Util import Util


class LogManager:
    """Static class to manage and convert .resx files to JSON format."""

    _log_messages: Dict[LogMessages, str] = {}
    __calls_counter: int = 0

    @classmethod
    def __convert_resx_to_json(cls, resx_file: Path) -> None:
        """Convert a .resx file to JSON format."""

        LogManager.__calls_counter += 1

        # Parse the .resx file as an XML tree
        try:
            xml_tree = parse(resx_file)
            root = xml_tree.getroot()

            for data_node in root.findall(".//data"):
                # Extract the 'name' attribute as the key
                key = str(data_node.get("name"))

                if key == "":
                    continue

                # Find the <value> element
                value_element = data_node.find("./value")
                if value_element is not None:
                    value = value_element.text
                    # Check if value is not None and not empty
                    if value is not None and value.strip():
                        cls._log_messages[LogMessages[key]] = str(value)
                    else:
                        # Handle the case when value is None or empty
                        Util.logger.warning(f"No value found for key '{key}'")
                else:
                    # Handle the case when <value> element is not found
                    Util.logger.warning(
                        f"Warning: No <value> element found for key '{key}'"
                    )
        except Exception as e:
            LogManager.something_went_wrong(type(cls).__name__, e)

    @staticmethod
    def get_message(message_type: LogMessages) -> str:
        """Get the log message by message type."""

        if LogManager.__calls_counter <= 0:
            # Get the absolute path of the current Python script
            current_file_path = os.path.abspath(__file__)

            # Get the directory containing the current Python script
            current_directory = os.path.dirname(current_file_path)

            LogManager.__convert_resx_to_json(
                Path(rf"{current_directory}\LogMessages.resx")
            )

        return LogManager._log_messages.get(message_type, "Message not found")

    @classmethod
    def something_went_wrong(cls, name: str, ex: Union[Exception, str]):
        log_str: LogMessages = LogMessages.SOMETHING_WENT_WRONG
        logger = Util.logger()
        if logger:
            logger.error(LogManager.get_message(log_str).format(name, ex))

    @classmethod
    def unable_to_get_neighborhood(cls):
        log_str: LogMessages = LogMessages.UNABLE_TO_GET_NEIGHBORHOOD
        logger = Util.logger()
        if logger:
            logger.error(LogManager.get_message(log_str))

    @classmethod
    def log_solution(cls, evaluation: Evaluation):
        log_str: LogMessages = LogMessages.LOG_SOLUTION
        logger = Util.logger()
        if logger:
            logger.info(LogManager.get_message(log_str).format(evaluation))

    @classmethod
    def invalid_action(cls, action: str, name: str, ex: Optional[Exception] = None):
        log_str: LogMessages = LogMessages.INVALID_ACTION
        logger = Util.logger()
        if logger:
            logger.error(LogManager.get_message(log_str).format(action, name))

            if ex:
                cls.something_went_wrong(name, ex)
