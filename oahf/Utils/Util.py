import hashlib
import multiprocessing
from typing import ClassVar, List, Optional, Type, Tuple
from oahf.Base.Solution import Solution
from pathlib import Path
import json

from oahf.Logger.Logger import Logger


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

    @classmethod
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
            hash_object.update(s.encode("utf-8"))

        # Return the final hexadecimal digest
        return hash_object.hexdigest()

    #
    #@classmethod
    #def get_current_thread_id(cls) -> Optional[int]:
    #    return threading.current_thread().ident
    
    @classmethod
    def read_input(cls, input_file: Path, input_type: Type) -> Optional[Solution]:
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
        if input_type is Type[AlwabpSolution]:
            return cls.read_ALWABP_input(input_file)
        else:
            pass

    @classmethod
    def read_ALWABP_input(cls, input_file: Path) -> Optional["ALWABP"]:
        """
        Reads ALWABP input file and returns an ALWABP instance.
        """
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
        from oahf.Logger.LogManager import LogManager
        
        line: Optional[str] = None
        number_of_workers: int = 0
        number_of_stations: int = 0
        number_of_tasks: int = 0
        alwabp_instance: Optional[AlwabpSolution] = None

        try:
            with open(input_file, "r") as sr:
                # Read first line (number of tasks)
                line = sr.readline().strip()
                if not line:
                    return None

                number_of_tasks = int(line)

                # Read second line (task-worker relationship matrix)
                line = sr.readline().strip()
                if not line:
                    return None

                splited_lines = line.split()
                number_of_workers = len(splited_lines)
                number_of_stations = number_of_workers
                
                alwabp_instance = AlwabpSolution(number_of_tasks, number_of_workers, number_of_stations)

                task = 1
                while task <= number_of_tasks:
                    values = [float(i) for i in splited_lines]
                    alwabp_instance.set_task_execution_times(task, values)

                    line = sr.readline().strip()
                    if not line:
                        return None
                    splited_lines = line.split()
                    task += 1

                # Read precedence graph (task pairs)
                while True:
                    u_task = int(splited_lines[0])
                    v_task = int(splited_lines[-1])

                    if u_task != -1 and v_task != -1:
                        alwabp_instance.add_precedence(u_task, v_task)

                        line = sr.readline().strip()
                        if not line:
                            break
                        splited_lines = line.split()
                    else:
                        break
        except Exception as e:
            LogManager.something_went_wrong(cls.__name__, e)
        finally:
            print("Input Reading Finished!")

        if alwabp_instance:
            alwabp_instance.process_graph_data()
            return alwabp_instance
        else:
            LogManager.something_went_wrong(cls.__name__, "Not a Valid Input!")
            return None

    @classmethod
    def get_recommeded_maximum_mean_cycle_time(cls, file_path: Path, input_name: str) -> int:
        """
        This function reads a JSON file and retrieves the integer value 
        corresponding to a key (input_name).

        :param file_path: The full path of the JSON file to read from.
        :param input_name: The key whose value needs to be retrieved.
        :return: The integer value associated with the key, or None if not found.
        """

        # Load JSON data from the file
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Get the value from the JSON data
        value: int = int(data.get(input_name, None))
        
        return value
