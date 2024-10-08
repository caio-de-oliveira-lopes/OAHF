from typing import List, Optional, Dict
from oahf.Base.Solution import Solution

class ALWABP(Solution):
    def __init__(self, number_of_tasks: int, number_of_workers: int, number_of_stations: int) -> None:
        """
        Initializes the ALWABP problem with the given number of tasks, workers, and stations.

        Args:
            number_of_tasks (int): The total number of tasks in the problem.
            number_of_workers (int): The total number of workers.
            number_of_stations (int): The total number of stations.
        """
        super().__init__()
        self.tasks: List[int] = [(i + 1) for i in range(number_of_tasks)]  # List of tasks [1, 2, ..., number_of_tasks]
        self.workers: List[int] = [(w + 1) for w in range(number_of_workers)]  # List of workers [1, 2, ..., number_of_workers]
        self.stations: List[int] = [(s + 1) for s in range(number_of_stations)]  # List of stations [1, 2, ..., number_of_stations]

        # Dictionary where key = task, value = list of execution times for each worker
        self.task_execution_times: Dict[int, List[int]] = {task: [] for task in self.tasks}

        # Dictionary where key = station, value = dictionary {worker: list of tasks assigned to that worker}
        self.station_assignment: Dict[int, Dict[int, List[int]]] = {station: {worker: [] for worker in self.workers} for station in self.stations}

    def set_task_execution_times(self, task_number: int, execution_times: List[int]) -> None:
        """
        Sets the list of execution times for a specific task.

        Args:
            task_number (int): The task number for which to set the execution times.
            execution_times (List[int]): A list of execution times for each worker.
        
        Raises:
            ValueError: If the task number is invalid or if the length of execution times does not match the number of workers.
        """
        if task_number not in self.tasks:
            raise ValueError(f"Task number {task_number} is invalid. It must be between 1 and {len(self.tasks)}.")
        
        if len(execution_times) != len(self.workers):
            raise ValueError(f"Execution times must be provided for all {len(self.workers)} workers.")

        # Set the execution times for the task
        self.task_execution_times[task_number] = execution_times

    def copy(self) -> "ALWABP":
        """
        Creates a copy of the current solution.

        Returns:
            ALWABP: A new instance of the ALWABP solution with the same data.
        """
        new_copy = ALWABP(len(self.tasks), len(self.workers), len(self.stations))
        new_copy.task_execution_times = {task: times[:] for task, times in self.task_execution_times.items()}
        new_copy.station_assignment = {station: {worker: tasks[:] for worker, tasks in workers.items()} for station, workers in self.station_assignment.items()}
        return new_copy

    def decompose_solution(self, k: int) -> Optional[List["ALWABP"]]:
        """
        Decomposes the solution into smaller parts (not implemented).

        Args:
            k (int): The number of parts to decompose into.

        Raises:
            NotImplementedError: This function is not implemented.
        """
        raise NotImplementedError("Decomposition is not supported for this problem.")

    def merge_solutions(self, solutions: List["ALWABP"]) -> "ALWABP":
        """
        Merges multiple solutions into one (not implemented).

        Args:
            solutions (List[ALWABP]): A list of solutions to merge.

        Raises:
            NotImplementedError: This function is not implemented.
        """
        raise NotImplementedError("Merging is not supported for this problem.")

    def solution_hash(self) -> int:
        """
        Generates a hash for the solution based on tasks, workers, stations, and assignments.

        Returns:
            int: The hash value of the solution.
        """
        return hash((
            tuple(self.tasks), 
            tuple(self.workers), 
            tuple(self.stations),
            frozenset((task, tuple(times)) for task, times in self.task_execution_times.items()),
            frozenset((station, frozenset((worker, tuple(tasks)) for worker, tasks in workers.items())) for station, workers in self.station_assignment.items())
        ))

    def solution_string_representation(self) -> str:
        """
        Gets a string representation of the solution, focusing on the task allocations per station and its assigned worker.

        Returns:
            str: A structured string representing the task allocations per station.
        """
        result = []
        result.append(f"ALWABP Solution:")
        result.append(f"Number of Tasks: {len(self.tasks)}")
        result.append(f"Number of Workers: {len(self.workers)}")
        result.append(f"Number of Stations: {len(self.stations)}")
        result.append("Task Allocations (per station):")
    
        for station in self.stations:
            result.append(f"  Station {station}:")
            # Get the worker assigned to the station (there should be only one)
            for worker, tasks in self.station_assignment[station].items():
                if tasks:
                    tasks_str = ", ".join(map(str, tasks))
                    result.append(f"    Worker {worker}: Tasks -> [{tasks_str}]")

        return "\n".join(result)


    def calculate_cycle_time(self, station: int) -> int:
        """
        Calculates the cycle time for a given station.

        Args:
            station (int): The station ID to calculate cycle time for.

        Returns:
            int: The total cycle time for the specified station.
        """
        total_time = 0
        # Sum all the task times executed by all workers at this station
        for worker, tasks in self.station_assignment.get(station, {}).items():
            total_time += sum(self.task_execution_times[task][worker - 1] for task in tasks)
        return total_time

    def get_max_cycle_time(self) -> int:
        """
        Finds the maximum cycle time across all stations.

        Returns:
            int: The maximum cycle time among all stations.
        """
        return max(self.calculate_cycle_time(station) for station in self.stations)

    def get_min_cycle_time(self) -> int:
        """
        Finds the minimum cycle time across all stations.

        Returns:
            int: The minimum cycle time among all stations.
        """
        return min(self.calculate_cycle_time(station) for station in self.stations)

    def get_idle_time(self) -> int:
        """
        Calculates the idle time, which is the difference between the maximum and minimum cycle times across stations.

        Returns:
            int: The idle time (max cycle time - min cycle time).
        """
        return self.get_max_cycle_time() - self.get_min_cycle_time()

    def solution_diff(self, other: "ALWABP") -> float:
        """
        Calculates the difference between this solution and another based on idle time.

        Args:
            other (ALWABP): The other solution to compare against.

        Returns:
            float: The difference in idle time between the two solutions.
        """
        if not isinstance(other, ALWABP):
            raise TypeError("The other solution must be of type ALWABP.")
        
        idle_time_self = self.get_idle_time()
        idle_time_other = other.get_idle_time()

        return idle_time_self - idle_time_other
