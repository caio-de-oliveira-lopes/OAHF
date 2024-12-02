from logging import FileHandler, LogRecord


class JsonListFileHandler(FileHandler):
    """
    Custom FileHandler to write logs as part of a JSON array.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_first_log = True  # Track if the current log is the first
        self.stream.write("[\n")
        self.stream.flush()

    def emit(self, record: LogRecord) -> None:
        """
        Override emit to manage comma placement correctly.
        """
        if not self._is_first_log:
            self.stream.write(",\n")
        else:
            self._is_first_log = False
        self.stream.write(self.format(record))
        self.stream.flush()

    def close(self) -> None:
        """
        Override close to write the closing array bracket.
        """
        self.stream.write("\n]\n")
        self.stream.flush()
        super().close()
