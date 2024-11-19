import hashlib
import json
import multiprocessing
import os
from datetime import datetime
from pathlib import Path
from typing import ClassVar, List, Optional, Type

from oahf.Base.Solution import Solution
from oahf.Logger.Logger import Logger


class Util:
    _eps: ClassVar[float] = 1e-3
    _threads: ClassVar[int] = multiprocessing.cpu_count() - 1
    _logger: ClassVar[Optional[Logger]] = None
    _optimization_start_time: ClassVar[str] = ""
    _default_output_path: ClassVar[Path] = Path(os.getcwd(), "Outputs")
    _input_name: ClassVar[str] = "dummy"
    _line: ClassVar[str] = (
        "-------------------------------------------------------------------"
    )

    @classmethod
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
    def logger(cls) -> Logger:
        """
        Returns:
            Logger: logger currently associated with the class.
        """
        if cls._logger is None:
            cls._logger = Logger()
        return cls._logger

    @classmethod
    def set_logger(cls, value: Logger) -> None:
        """
        Sets a new logger for the Util class.
        """
        cls._logger = value

    @classmethod
    def default_output_path(cls) -> Path:
        return cls._default_output_path

    @classmethod
    def set_default_output_path(cls, path: Path) -> None:
        cls._default_output_path = path

    @classmethod
    def input_name(cls) -> str:
        return cls._input_name

    @classmethod
    def set_input_name(cls, input_name: str) -> None:
        cls._input_name = input_name

    @classmethod
    def line(cls) -> str:
        return cls._line

    @classmethod
    def set_line(cls, line: str) -> None:
        cls._line = line

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
    # @classmethod
    # def get_current_thread_id(cls) -> Optional[int]:
    #    return threading.current_thread().ident

    @classmethod
    def read_input(cls, problem_data: "ProblemData") -> Optional[Solution]:
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

        solution = None

        if problem_data.input_type is Type[AlwabpSolution]:
            solution = cls.read_ALWABP_input(problem_data.input_file)

            if not solution or not isinstance(solution, AlwabpSolution):
                return None

            solution.cycle_time_limit = Util.get_recommeded_maximum_mean_cycle_time(
                problem_data.cycle_time_path, problem_data.file_name
            )

        return solution

    @classmethod
    def read_ALWABP_input(cls, input_file: Path) -> Optional[Solution]:
        """
        Reads ALWABP input file and returns an ALWABP instance.
        """
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
        from oahf.Logger.LogManager import LogManager

        try:
            with open(input_file, "r") as sr:
                # Read all lines once to reduce I/O time
                lines = sr.readlines()

                # Check the first line (number of tasks)
                if not lines or not lines[0].strip():
                    return None

                number_of_tasks = int(lines[0].strip())

                # Second line is the task-worker relationship matrix
                worker_lines = lines[1].split()
                number_of_workers = len(worker_lines)
                number_of_stations = number_of_workers

                alwabp_instance = AlwabpSolution(
                    number_of_tasks, number_of_workers, number_of_stations
                )

                # Reading task execution times in one go
                for task in range(1, number_of_tasks + 1):
                    task_values = list(map(float, worker_lines))
                    alwabp_instance.set_task_execution_times(task, task_values)
                    # Move to the next line for the next task
                    worker_lines = lines[task + 1].split()

                # Read precedence graph (task pairs) directly
                for line in lines[(number_of_tasks + 1) :]:
                    splited_lines = line.split()
                    u_task, v_task = int(splited_lines[0]), int(splited_lines[-1])

                    if u_task == -1 or v_task == -1:
                        break

                    alwabp_instance.add_precedence(u_task, v_task)

        except Exception as e:
            LogManager.something_went_wrong(cls.__name__, e)
            return None

        print(f'Input "{input_file}" successfully read!\n{Util.line()}')

        if alwabp_instance:
            alwabp_instance.process_graph_data()
            return alwabp_instance
        else:
            LogManager.something_went_wrong(
                cls.__name__, f'File "{input_file}" is not a valid input!'
            )
            return None

    @classmethod
    def get_recommeded_maximum_mean_cycle_time(
        cls, file_path: Path, input_name: str
    ) -> int:
        """
        This function reads a JSON file and retrieves the integer value
        corresponding to a key (input_name).

        :param file_path: The full path of the JSON file to read from.
        :param input_name: The key whose value needs to be retrieved.
        :return: The integer value associated with the key, or None if not found.
        """

        # Load JSON data from the file
        with open(file_path, "r") as f:
            data = json.load(f)

        # Get the value from the JSON data
        value: int = int(data.get(input_name, None))

        return value

    @classmethod
    def set_optimization_start_time(cls, optimization_time: datetime) -> None:
        cls._optimization_start_time = optimization_time.strftime(
            "output_%m-%d-%Y_%Hh-%Mm-%Ss"
        ).replace(":", "_")

    @classmethod
    def get_optimization_start_time(cls):
        return cls._optimization_start_time
