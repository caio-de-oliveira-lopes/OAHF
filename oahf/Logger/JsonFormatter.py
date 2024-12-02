import json
import logging
import os
import traceback


class JsonFormatter(logging.Formatter):
    """
    Custom class to format logs as pretty-printed JSON.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Extract the stack trace
        stack = (
            traceback.extract_stack()
            if not record.exc_info
            else traceback.extract_tb(record.exc_info[2])
        )

        # Filter out logging-related stack frames (logging/__init__.py or your Logger.py)
        caller = next(
            (frame for frame in reversed(stack) if not self._is_logging_related(frame)),
            None,
        )

        # Get just the filename (no path)
        filename = (
            os.path.basename(caller.filename)
            if caller
            else os.path.basename(record.filename)
        )

        # Get the logger name (either from the caller's context or fallback to the default)
        logger_name = record.name if caller else "Unknown"

        # Build the log record
        log_record = {
            "level": record.levelname,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
            "name": logger_name,
            "filename": filename,  # Just the file name, no path
            "funcName": caller.name if caller else record.funcName,
            "lineno": caller.lineno if caller else record.lineno,
        }

        # Return the JSON-formatted string with indentation for readability
        return json.dumps(log_record, indent=4)

    def _is_logging_related(self, frame) -> bool:
        """
        Helper function to determine if the current frame is part of the logging library or custom Logger code.
        Checks if the path contains substrings related to logging or Logger code.
        """
        # Substrings that identify logging-related frames
        keywords = [
            "__init__.py",
            "logger.py",
            "logging.handlers",
            "Logger.py",
            "LogManager.py",
            "JsonFormatter.py",
            "JsonLogger",
        ]

        # Check if any part of the filename contains any of the keywords
        # This now checks if any part of the path contains the relevant substrings.
        return any(
            frame.filename.lower().find(keyword.lower()) != -1 for keyword in keywords
        )
