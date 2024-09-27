import logging
import json

class JsonFormatter(logging.Formatter):
    """
    Custom class to format logs as JSON.
    Formats the log record with level, message, time, logger name,
    filename, function name, and line number.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            'level': record.levelname,
            'message': record.getMessage(),
            'time': self.formatTime(record, self.datefmt),
            'name': record.name,
            'filename': record.filename,
            'funcName': record.funcName,
            'lineno': record.lineno,
        }
        return json.dumps(log_record)
