import os
import xml.etree.ElementTree as ET
from typing import Dict
from pathlib import Path
from LogMessages import LogMessages

class LogManager:
    """Static class to manage log messages and convert .resx files to JSON format."""
    _log_messages: Dict[LogMessages, str] = {}
    __calls_counter: int = 0

    @classmethod
    def __convert_resx_to_json(cls, resx_file: Path) -> None:
        """Convert a .resx file to JSON format."""
        
        LogManager.__calls_counter += 1
        
        # Parse the .resx file as an XML tree
        try:
            xml_tree = ET.parse(resx_file)
            root = xml_tree.getroot()

            for data_node in root.findall(".//data"):
                # Extract the 'name' attribute as the key
                key = str(data_node.get("name"))

                if key == "":
                    continue

                # Find the <value> element
                value_element = data_node.find("./value")
                if value_element is not None:
                    # Extract the text content of the <value> element as the value
                    value = value_element.text
                    # Check if value is not None and not empty
                    if value is not None and value.strip():
                        # Store the key-value pair in the 'log_messages' dictionary
                        cls._log_messages[LogMessages[key]] = str(value)
                    else:
                        # Handle the case when value is None or empty
                        print(f"Warning: No valid value found for key '{key}' in '{resx_file}'")
                else:
                    # Handle the case when <value> element is not found
                    print(f"Warning: No <value> element found for key '{key}' in '{resx_file}'")
        except Exception as e:
            LogManager.log_error(e)
    
    @staticmethod
    def get_message(message_type: LogMessages) -> str:
        """Get the log message by message type."""
        
        if LogManager.__calls_counter <= 0:
            # Get the absolute path of the current Python script
            current_file_path = os.path.abspath(__file__)

            # Get the directory containing the current Python script
            current_directory = os.path.dirname(current_file_path)

            LogManager.__convert_resx_to_json(Path(fr"{current_directory}\LogMessages.resx"))
            
        return LogManager._log_messages.get(message_type, "Message not found")
