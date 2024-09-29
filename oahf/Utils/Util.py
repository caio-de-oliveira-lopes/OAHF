from typing import List, ClassVar, Optional
import multiprocessing
from oahf.Logger.Logger import Logger
import hashlib

class Util:
    _eps: ClassVar[float] = 1e-5
    _threads: ClassVar[int] = multiprocessing.cpu_count() - 1
    _logger: ClassVar[Optional[Logger]] = None

    @property
    def eps(cls) -> float:
        """
        Returns the numerical precision value (epsilon).
        """
        return cls._eps
    
    @property
    def threads(cls) -> int:
        """
        Returns the number of available threads, subtracting 1 from the total CPU count.
        """
        return cls._threads

    @property
    def logger(cls) -> Optional[Logger]:
        """        
        Returns:
            Optional[Logger]: logger currently associated with the class.
        """
        return cls._logger
    
    @classmethod
    def set_logger(cls, value: Logger) -> None:
        """
        Sets a new logger for the Util class.
        """
        cls._logger = value
    
    @staticmethod
    def get_current_method_name() -> str:
        """
        Retrieves the name of the currently running method.
        """
        import inspect
        # Get the current frame
        frame = inspect.currentframe()
        if frame is None or frame.f_back is None:
            return "Unknown method"
        # Get the method name from the previous frame
        method_name = frame.f_back.f_code.co_name
        return method_name
        
    @classmethod 
    def create_hash_from_list(cls, strings: List[str]) -> str:
        """
        Creates a SHA-256 hash from a list of strings.

        Args:
            strings (List[str]): List of strings to compute the hash from.

        Returns:
            str: The resulting hash in hexadecimal format.
        """
        # Initialize a hashlib object (using SHA-256)
        hash_object = hashlib.sha256()

        # Iterate over the list of strings and update the hash with string bytes
        for s in strings:
            hash_object.update(s.encode('utf-8'))

        # Return the final hexadecimal digest
        return hash_object.hexdigest()
