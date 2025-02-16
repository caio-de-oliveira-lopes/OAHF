"""
AlwabpSolution Module

This module defines the AlwabpSolution class, which extends the base Solution class to model
Assembly Line Worker Assignment and Balancing Problems (ALWABP). It provides methods to manage
task assignments, worker allocations, precedence constraints, cycle time calculations, and related
operations necessary to build, evaluate, and transform solutions.
"""

import copy
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Solution import Solution
from oahf.ImplementedBase import AlwabpRemovalMovement
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.Logger.LogManager import LogManager
from oahf.Utils import EnumUtil


class GraphOrientation(Enum):
    """
    Enumeration for graph orientations.
    """
    FORWARD = auto()
    BACKWARD = auto()

    @classmethod
    def reverse(cls, graph_orientation: "GraphOrientation") -> "GraphOrientation":
        """
        Reverses the given graph orientation.
        
        Args:
            graph_orientation (GraphOrientation): The current orientation.
            
        Returns:
            GraphOrientation: BACKWARD if input is FORWARD, and vice versa.
        """
        if graph_orientation == GraphOrientation.FORWARD:
            return GraphOrientation.BACKWARD
        else:
            return GraphOrientation.FORWARD


class TaskOrderingRule(Enum):
    """
    Enumeration for different task ordering rules used in the solution.
    """
    MAX_F = auto()
    MAX_IF = auto()    
    MAX_TIME_MINUS = auto()
    MAX_TIME_PLUS = auto()
    MAX_TIME_AVERAGE = auto()
    MIN_TIME_MINUS = auto()
    MIN_TIME_PLUS = auto()
    MIN_TIME_AVERAGE = auto()
    MAX_PW_PLUS = auto()
    MAX_PW_MINUS = auto()
    MAX_PW_AVERAGE = auto()
    MIN_D = auto()
    MIN_R = auto()
    MAX_F_TIME = auto()
    MAX_IF_TIME = auto()
    MIN_RANK = auto()


class AlwabpSolution(Solution):
    """
    Represents a solution for the ALWABP problem.

    This class handles the setup and management of tasks, workers, and stations, including:
      - Storing execution times and their bounded versions.
      - Managing assignments of workers and tasks to stations.
      - Handling precedence relationships among tasks.
      - Calculating cycle times and evaluating solution quality.
      - Performing operations such as copying, resetting, and transforming solutions.
    """

    __slots__ = (
        "tasks",
        "workers",
        "stations",
        "_task_execution_times",
        "_bounded_task_execution_times",
        "station_worker_assignment",
        "worker_station_assignment",
        "station_tasks_assignment",
        "task_station_assignment",
        "_unassigned_workers",
        "_unassigned_tasks",
        "immediate_task_precedences",
        "tasks_executed_by_worker",
        "all_task_precedences",
        "task_ordering_rules",
        "station_cycle_time_memo",
        "_cycle_time_limit",
        "_default_graph_orientation",
        "print_solution_updates",
        "name",
    )

    # key is one hash that, once solution is reversed, the value hash is valid
    _hash_reverse_map: Dict[int, int] = {}

    # key = tuple(solution_hash, station, task), value is the new hash
    _hash_task_insertion_map: Dict[tuple[int, int, int], int] = {}
    _hash_task_removal_map: Dict[tuple[int, int, int], int] = {}

    # key = tuple(solution_hash, station, worker), value is the new hash
    _hash_worker_insertion_map: Dict[tuple[int, int, int], int] = {}
    _hash_worker_removal_map: Dict[tuple[int, int, int], int] = {}

    def __init__(self, number_of_tasks: int, number_of_workers: int, number_of_stations: int) -> None:
        """
        Initializes an AlwabpSolution instance.

        Sets up tasks, workers, and stations as tuples, initializes execution time matrices (both original
        and bounded), and prepares data structures for assignments, precedence relationships, cycle time memoization,
        and other solution-related information.
        
        Args:
            number_of_tasks (int): Total number of tasks.
            number_of_workers (int): Total number of workers.
            number_of_stations (int): Total number of stations.
        """
        super().__init__()  # Calls Entity.__init__ via Solution

        # Initialize tasks, workers, and stations as immutable tuples.
        self.tasks: Tuple[int, ...] = tuple(range(1, number_of_tasks + 1))
        self.workers: Tuple[int, ...] = tuple(range(1, number_of_workers + 1))
        self.stations: Tuple[int, ...] = tuple(range(1, number_of_stations + 1))

        # Initialize execution times for tasks (one per worker), set to infinity by default.
        self._task_execution_times: Dict[int, List[float]] = {
            task: [float("inf")] * number_of_workers for task in self.tasks
        }
        self._bounded_task_execution_times: Dict[int, List[float]] = {
            task: times.copy() for task, times in self._task_execution_times.items()
        }

        # Initialize station-worker and worker-station assignments.
        self.station_worker_assignment: Dict[int, Optional[int]] = {
            station: None for station in self.stations
        }
        self.worker_station_assignment: Dict[int, Optional[int]] = {
            worker: None for worker in self.workers
        }
        # Initialize station-tasks and task-station assignments.
        self.station_tasks_assignment: Dict[int, List[int]] = {
            station: [] for station in self.stations
        }
        self.task_station_assignment: Dict[int, Optional[int]] = {
            task: None for task in self.tasks
        }

        # Lists to track unassigned workers and tasks.
        self._unassigned_workers: List[int] = list(self.workers)
        self._unassigned_tasks: List[int] = list(self.tasks)

        # Initialize immediate precedences for tasks in both graph orientations.
        self.immediate_task_precedences: Dict[GraphOrientation, Dict[int, List[int]]] = { # type: ignore
            graph_orientation: {task: [] for task in self.tasks}
            for graph_orientation in EnumUtil.get_values(GraphOrientation)
        }
        # Map each worker to the tasks they can execute.
        self.tasks_executed_by_worker: Dict[int, Tuple[int, ...]] = {
            worker: tuple() for worker in self.workers
        }
        self._cycle_time_limit: Optional[float] = None

        # Initialize all precedences (immediate and transitive) for tasks.
        self.all_task_precedences: Dict[GraphOrientation, Dict[int, List[int]]] = { # type: ignore
            graph_orientation: {task: [] for task in self.tasks}
            for graph_orientation in EnumUtil.get_values(GraphOrientation)
        }

        # Initialize task ordering rules for various criteria.
        self.task_ordering_rules: Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]] = { # type: ignore
            weight_type: {task: (-1.0,) * number_of_workers for task in self.tasks}
            for weight_type in EnumUtil.get_values(TaskOrderingRule)
        }

        # Initialize cycle time memoization per station.
        self.station_cycle_time_memo: Dict[int, float] = {
            station: 0.0 for station in self.stations
        }

        self._default_graph_orientation: GraphOrientation = GraphOrientation.FORWARD
        self.print_solution_updates: bool = False
        self._first_unassigned_station: Optional[int] = 1
        self._number_of_tasks: int = number_of_tasks
        self._number_of_workers: int = number_of_workers
        self._number_of_stations: int = number_of_stations
        self._hash_memo: Optional[int] = None

        self._empty_sol_hash: Dict[GraphOrientation, int] = {
            GraphOrientation.FORWARD: hash(self)
        }
        self.default_graph_orientation = GraphOrientation.BACKWARD
        self._empty_sol_hash[GraphOrientation.BACKWARD] = hash(self)
        self.default_graph_orientation = GraphOrientation.FORWARD
        self._best_worker_for_task: Dict[int, int] = {task: 0 for task in self.tasks}
        self._workers_ranks: Dict[int, Dict[int, int]] = {
            task: {worker: 0 for worker in self.workers}
            for task in self.tasks
        }

    def __deepcopy__(self, memo):
        """
        Creates a deep copy of the current solution instance.
        
        This method handles the custom copying of __slots__ attributes and ensures that mutable
        objects are properly duplicated while preserving the identity of shared immutable objects.
        
        Args:
            memo (dict): Dictionary to track already copied objects.
        
        Returns:
            AlwabpSolution: A deep copy of the solution.
        """
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # Copy parent's private attributes.
        for attr in ("_Entity__id", "_Entity__name"):
            if attr in self.__dict__:
                setattr(result, attr, self.__dict__[attr])

        result.get_new_id()

        # Copy attributes from Solution and AlwabpSolution.
        result.print_solution_updates = self.print_solution_updates
        result.name = self.name
        result.tasks = self.tasks
        result.workers = self.workers
        result.stations = self.stations
        result._cycle_time_limit = self._cycle_time_limit
        result._default_graph_orientation = self._default_graph_orientation
        result._first_unassigned_station = self._first_unassigned_station
        result._number_of_tasks = self._number_of_tasks
        result._number_of_workers = self._number_of_workers
        result._number_of_stations = self._number_of_stations
        result._hash_memo = self._hash_memo
        result.immediate_task_precedences = self.immediate_task_precedences
        result.tasks_executed_by_worker = self.tasks_executed_by_worker
        result.all_task_precedences = self.all_task_precedences
        result.task_ordering_rules = self.task_ordering_rules
        result._empty_sol_hash = self._empty_sol_hash
        result._best_worker_for_task = self._best_worker_for_task
        result._workers_ranks = self._workers_ranks

        # Copy assignment dictionaries.
        result.station_worker_assignment = self.station_worker_assignment.copy()
        result.worker_station_assignment = self.worker_station_assignment.copy()
        result.task_station_assignment = self.task_station_assignment.copy()
        result._unassigned_workers = self._unassigned_workers.copy()
        result._unassigned_tasks = self._unassigned_tasks.copy()
        result.station_cycle_time_memo = self.station_cycle_time_memo.copy()

        # Copy lists within dictionaries.
        result._task_execution_times = {k: v.copy() for k, v in self._task_execution_times.items()}
        result._bounded_task_execution_times = {k: v.copy() for k, v in self._bounded_task_execution_times.items()}
        result.station_tasks_assignment = {k: v.copy() for k, v in self.station_tasks_assignment.items()}

        return result

    def copy(self) -> "AlwabpSolution":
        """
        Creates a deep copy of the current solution using the custom __deepcopy__ method.
        
        Returns:
            AlwabpSolution: A new, deep-copied instance of the solution.
        """
        return copy.deepcopy(self)

    def validate_aspects(self) -> bool:
        """
        Validates the solution’s aspects.

        If a cycle time limit is set and there are unassigned tasks or workers,
        the cycle time limit is incremented, the solution is reset, and False is returned.
        Otherwise, the parent class's validate_aspects method is used.
        
        Returns:
            bool: True if the solution is valid; False otherwise.
        """
        if self.cycle_time_limit and (self.unassigned_tasks or self._unassigned_workers):
            self.cycle_time_limit = self.cycle_time_limit + 1
            self.reset()
            return False
        return super().validate_aspects()

    def narrow_bounds(self) -> None:
        """
        Narrows the execution time bounds by setting the cycle time limit to the maximum cycle time.
        """
        self.cycle_time_limit = self.get_max_cycle_time()

    def reset(self) -> None:
        """
        Resets the solution state.

        This clears the worker and task assignments to stations, resets unassigned workers and tasks,
        and reinitializes cycle time memoization and the first unassigned station marker.
        """
        self.station_worker_assignment = {station: None for station in self.stations}
        self.worker_station_assignment = {worker: None for worker in self.workers}
        self.station_tasks_assignment = {station: [] for station in self.stations}
        self.task_station_assignment = {task: None for task in self.tasks}
        self._unassigned_workers = list(self.workers)
        self._unassigned_tasks = list(self.tasks)
        self.station_cycle_time_memo = {station: 0.0 for station in self.stations}
        self._first_unassigned_station = 1
        self._hash_memo = self._empty_sol_hash[self.default_graph_orientation]

    def process_graph_data(self) -> None:
        """
        Processes and updates all graph-related data for the solution.

        This includes updating the tasks each worker can execute, computing all transitive task precedences,
        adjusting bounded execution times based on a default cycle time, computing the best worker for each task,
        updating worker ranks, and calculating task ordering rules.
        """
        self._update_tasks_executed_by_worker()
        self._fill_all_task_precedences()
        self._update_bounded_task_execution_times(499)
        self._compute_best_workers_for_tasks()
        self._compute_workers_ranks()
        self._calculate_task_ordering_rules()

    def _compute_workers_ranks(
        self,
        priority_matrix: Optional[Dict[int, List[int]]] = None,
        task: Optional[int] = None,
        worker: Optional[int] = None
    ) -> Dict[int, Dict[int, int]]:
        """
        Computes the ranking of workers for tasks based on execution times.

        For each task (or a specified task), it sorts workers by their execution times (ascending).
        If a specific worker is provided, only that worker's rank is updated; otherwise, ranks for all workers are computed.
        
        Args:
            priority_matrix (Optional[Dict[int, List[int]]]): Optional alternative matrix of execution times.
            task (Optional[int]): Specific task to update. If None, all tasks are processed.
            worker (Optional[int]): Specific worker to update. If None, all workers are processed.
        
        Returns:
            Dict[int, Dict[int, int]]: A mapping of task IDs to dictionaries of worker ranks.
        """
        task_times_dict = priority_matrix or self._bounded_task_execution_times

        if priority_matrix:
            result_storage: Dict[int, Dict[int, int]] = {t: {w: 0 for w in self.workers} for t in self.tasks}
        else:
            result_storage = self._workers_ranks

        tasks_to_process = [task] if task else task_times_dict.keys()

        for t in tasks_to_process:
            if t not in task_times_dict:
                continue
            labeled_task_order = list(zip(task_times_dict[t], self.workers))
            ordered = sorted(labeled_task_order)
            if worker:
                if worker not in self.workers:
                    continue
                for rank, (_, w) in enumerate(ordered):
                    if w == worker:
                        result_storage.setdefault(t, {})[worker] = rank
                        break
            else:
                result_storage[t] = {w: rank for rank, (_, w) in enumerate(ordered)}

        return result_storage

    def _compute_best_workers_for_tasks(self) -> None:
        """
        Determines the best (i.e., fastest) worker for each task.

        For each task, the worker with the minimum execution time is identified and stored.
        """
        self._best_worker_for_task = {
            task: min(enumerate(times, start=1), key=lambda pair: pair[1])[0]
            for task, times in self._bounded_task_execution_times.items()
        }

    def _update_tasks_executed_by_worker(self) -> None:
        """
        Updates the mapping of workers to the tasks they can execute.

        Iterates over each worker and records the tasks for which their execution time is finite.
        """
        self.tasks_executed_by_worker = {
            worker: self.__get_tasks_executed_by_worker(worker)
            for worker in self.workers
        }

    @property
    def unassigned_workers(self):
        """
        Returns the list of currently unassigned workers.
        """
        return self._unassigned_workers

    @property
    def cycle_time_limit(self) -> Optional[float]:
        """
        Retrieves the current cycle time limit.
        
        Returns:
            Optional[float]: The cycle time limit if set, otherwise None.
        """
        return self._cycle_time_limit

    @cycle_time_limit.setter
    def cycle_time_limit(self, value: float) -> None:
        """
        Sets a new cycle time limit for the solution.

        If a cycle time limit already exists, an update message is printed; otherwise, the starting limit is printed.
        The new limit is then stored for subsequent calculations.
        
        Args:
            value (float): The new cycle time limit.
        """
        if self._cycle_time_limit:
            self.print_update(f"Updated cycle time limit to {str(value)}.")
        else:
            print(f"Starting with cycle time limit as {str(value)}.")
        self._cycle_time_limit = value

    @property
    def default_graph_orientation(self) -> GraphOrientation:
        """
        Retrieves the default graph orientation of the solution.
        
        Returns:
            GraphOrientation: The current default graph orientation.
        """
        return self._default_graph_orientation

    @default_graph_orientation.setter
    def default_graph_orientation(self, graph_orientation: GraphOrientation) -> None:
        """
        Sets a new default graph orientation.

        If the new orientation differs from the current one, the solution is reversed (swapping task and worker assignments
        as well as cycle times) to reflect the new orientation.
        
        Args:
            graph_orientation (GraphOrientation): The new default graph orientation.
        """
        if self._default_graph_orientation == graph_orientation:
            return

        old_hash = hash(self)
        self._default_graph_orientation = graph_orientation
        self._reverse_solution(old_hash)

    def _reverse_solution(self, old_hash: int) -> None:
        """
        Reverses the solution assignments based on the new graph orientation.

        Swaps tasks, workers, and cycle times between mirrored stations. Also updates worker-to-station assignments
        and the task-to-station mapping accordingly. Uses a reverse hash map to update the solution hash.
        
        Args:
            old_hash (int): The hash of the solution prior to reversal.
        """
        num_stations = self._number_of_stations
        half_stations = num_stations // 2

        for i in range(1, half_stations + 1):
            mirror_idx = num_stations - i + 1

            # Swap tasks between station i and its mirror.
            (self.station_tasks_assignment[i],
             self.station_tasks_assignment[mirror_idx]) = (
                self.station_tasks_assignment[mirror_idx],
                self.station_tasks_assignment[i],
            )

            # Swap worker assignments.
            (self.station_worker_assignment[i],
             self.station_worker_assignment[mirror_idx]) = (
                self.station_worker_assignment[mirror_idx],
                self.station_worker_assignment[i],
            )

            # Swap cycle times.
            (self.station_cycle_time_memo[i],
             self.station_cycle_time_memo[mirror_idx]) = (
                self.station_cycle_time_memo[mirror_idx],
                self.station_cycle_time_memo[i],
            )

        # Update worker-to-station mapping.
        for station, worker in self.station_worker_assignment.items():
            if worker is not None:
                self.worker_station_assignment[worker] = station

        for station, tasks in self.station_tasks_assignment.items():
            self.task_station_assignment.update({task: station for task in tasks})

        if (reversed_hash := AlwabpSolution._hash_reverse_map.get(old_hash)):
            self._hash_memo = reversed_hash
        else:
            self._hash_memo = None
            AlwabpSolution._hash_reverse_map[old_hash] = hash(self)
            AlwabpSolution._hash_reverse_map[hash(self)] = old_hash

    def fix_solution(self) -> None:
        """
        Fixes the solution by enforcing a FORWARD graph orientation, reordering tasks,
        and updating the cycle time limit.
        """
        self.default_graph_orientation = GraphOrientation.FORWARD
        self.order_solution_tasks()
        self.narrow_bounds()

    def _update_bounded_task_execution_times(self, cycle_time: Optional[float]) -> None:
        """
        Updates the bounded execution times for tasks based on the provided cycle time.

        For each task, if any execution time is infinite, it is replaced with cycle_time + 1.
        
        Args:
            cycle_time (Optional[float]): The cycle time to use for bounding execution times.
        """
        self._bounded_task_execution_times = copy.deepcopy(self._task_execution_times)

        if cycle_time:
            for task in self.tasks:
                float_array = np.array(self._bounded_task_execution_times[task])
                float_array[float_array == np.inf] = cycle_time + 1
                self._bounded_task_execution_times[task] = float_array.tolist()

    @property
    def unassigned_tasks(self):
        """
        Returns the list of currently unassigned tasks.
        """
        return self._unassigned_tasks

    def set_task_execution_times(self, task_number: int, execution_times: List[float]) -> None:
        """
        Sets the execution times for a specific task across all workers.

        Args:
            task_number (int): The task identifier.
            execution_times (List[float]): A list of execution times for each worker.
        
        Raises:
            ValueError: If the task number is invalid or the execution times list does not match the number of workers.
        """
        if task_number not in self.tasks:
            raise ValueError(
                f"Task number {task_number} is invalid. It must be between 1 and {self._number_of_tasks}."
            )

        if len(execution_times) != self._number_of_workers:
            raise ValueError(
                f"Execution times must be provided for all {self._number_of_workers} workers."
            )

        self._task_execution_times[task_number] = execution_times

    def decompose_solution(self, k: int) -> Optional[List["AlwabpSolution"]]:
        """
        Attempts to decompose the current solution into k sub-solutions.

        Note:
            Decomposition is not supported for this problem type.
        
        Args:
            k (int): The number of sub-solutions requested.
        
        Raises:
            NotImplementedError: Always raised, as decomposition is unsupported.
        """
        raise NotImplementedError("Decomposition is not supported for this problem.")

    def merge_solutions(self, solutions: List["AlwabpSolution"]) -> "AlwabpSolution":
        """
        Merges multiple solutions into a single solution.

        Note:
            Merging is not supported for this problem type.
        
        Args:
            solutions (List[AlwabpSolution]): List of solutions to merge.
        
        Raises:
            NotImplementedError: Always raised, as merging is unsupported.
        """
        raise NotImplementedError("Merging is not supported for this problem.")

    @property
    def solution_hash(self) -> int:
        """
        Computes a hash value representing the current solution.

        The hash is based on the assignments of tasks and workers to stations along with the graph orientation.
        
        Returns:
            int: The computed hash value.
        """
        if not self._hash_memo:
            self._hash_memo = hash(
                (
                    frozenset(
                        (
                            station,
                            frozenset(tasks),
                            self.station_worker_assignment[station],
                        )
                        for station, tasks in self.station_tasks_assignment.items()
                    ),
                    self.default_graph_orientation,
                )
            )

        return self._hash_memo

    def __str__(self) -> str:
        """
        Returns a structured string representation of the solution.

        Includes solution ID, counts of tasks/workers/stations, maximum cycle time,
        and detailed task allocations per station.
        
        Returns:
            str: A human-readable representation of the solution.
        """
        from oahf.Utils.Util import Util

        result = [Util.line()]
        result.append("ALWABP Solution:")
        result.append(f"ID: {self.id}")
        result.append(f"Number of Tasks: {self._number_of_tasks}")
        result.append(f"Number of Workers: {self._number_of_workers}")
        result.append(f"Number of Stations: {self._number_of_stations}")
        result.append(f"Max Cycle Time: {str(int(self.get_max_cycle_time()))}")
        result.append("Task Allocations (per station):")

        for station in self.stations:
            result.append(f"  Station {station}:")
            worker = self.station_worker_assignment.get(station, None)
            if worker is not None:
                tasks_str = ", ".join(map(str, self.station_tasks_assignment[station]))
                result.append(f"    Worker {worker}: Tasks -> [{tasks_str}]")

        unassigned_tasks = (
            ", ".join(map(str, self.unassigned_tasks)) if self.unassigned_tasks else "[]"
        )
        result.append(f"Unassigned Tasks: {unassigned_tasks}")
        result.append(Util.line())
        return "\n".join(result)

    def to_dict(self) -> dict:
        """
        Converts the solution into a dictionary representation.

        Includes basic properties and the detailed task allocation per station.
        
        Returns:
            dict: Dictionary containing solution details.
        """
        solution_dict = super().to_dict()

        solution_dict.update(
            {
                "number_of_tasks": self._number_of_tasks,
                "number_of_workers": self._number_of_workers,
                "number_of_stations": self._number_of_stations,
                "max_cycle_time": int(self.get_max_cycle_time()),
                "task_allocations_per_station": [],
                "unassigned_tasks": self.unassigned_tasks if self.unassigned_tasks else [],
            }
        )

        for station in self.stations:
            worker = self.station_worker_assignment.get(station, None)
            station_data = {"station": station, "worker": worker, "tasks": []}
            if worker is not None:
                station_data["tasks"] = self.station_tasks_assignment.get(station, [])
            solution_dict["task_allocations_per_station"].append(station_data)

        return solution_dict

    @classmethod
    def from_dict(cls, data: dict, base_solution: "AlwabpSolution") -> "AlwabpSolution":
        """
        Reconstructs an ALWABP solution from a dictionary.

        Uses an existing solution instance to provide necessary parameters and
        rebuilds worker and task assignments, followed by cycle time recalculations.
        
        Args:
            data (dict): Serialized solution data.
            base_solution (AlwabpSolution): An instance with base parameters.
        
        Returns:
            AlwabpSolution: The reconstructed solution.
        """
        solution = base_solution.copy()
        solution.default_graph_orientation = GraphOrientation.FORWARD
        solution.reset()

        for allocation in data.get("task_allocations_per_station", []):
            station = allocation["station"]
            worker = allocation.get("worker")
            tasks = allocation.get("tasks", [])

            if worker is not None:
                solution.add_worker_to_station(worker, station, recalculate_cycle_time=False)

            for task in tasks:
                solution.add_task_to_station(task, station)

        unassigned_tasks = data.get("unassigned_tasks", [])
        solution._unassigned_tasks = unassigned_tasks

        for station in solution.stations:
            solution.calculate_cycle_time(station, force_calculate=True)

        solution._cycle_time_limit = solution.get_max_cycle_time()
        return solution

    def calculate_cycle_time(self, station: int, force_calculate: bool = False) -> float:
        """
        Calculates the cycle time for a specified station.

        If force_calculate is True, the cycle time is recomputed from the sum of execution times
        of tasks assigned to the station. Otherwise, a cached value is returned.
        
        Args:
            station (int): The station identifier.
            force_calculate (bool): Whether to recalculate the cycle time.
        
        Returns:
            float: The total cycle time for the station.
        """
        total_time = 0
        worker = self.station_worker_assignment.get(station, None)
        if force_calculate:
            total_time += sum(
                self.get_task_execution_time(task, worker)
                for task in self.station_tasks_assignment[station]
            )
            self.station_cycle_time_memo[station] = total_time

        return self.station_cycle_time_memo[station]

    def get_max_cycle_time(self) -> float:
        """
        Finds the maximum cycle time across all stations.
        
        Returns:
            float: The maximum cycle time.
        """
        return max(self.station_cycle_time_memo.values())

    def get_min_cycle_time(self) -> float:
        """
        Finds the minimum cycle time across all stations.
        
        Returns:
            float: The minimum cycle time.
        """
        return min(self.station_cycle_time_memo.values())

    def get_idle_time(self) -> float:
        """
        Calculates the idle time as the difference between the maximum and minimum cycle times.
        
        Returns:
            float: The idle time.
        """
        return self.get_max_cycle_time() - self.get_min_cycle_time()

    def solution_diff(self, other: "Solution") -> float:
        """
        Computes the difference in idle time between this solution and another.

        Args:
            other (ALWABP): The other solution for comparison.
        
        Returns:
            float: The idle time difference (self - other).
        """
        if not isinstance(other, AlwabpSolution):
            raise TypeError("The other solution must be of type ALWABP.")

        idle_time_self = self.get_idle_time()
        idle_time_other = other.get_idle_time()

        return idle_time_self - idle_time_other

    def add_precedence(
        self,
        task_u: int,
        task_v: int,
        graph_orientation: Optional[GraphOrientation] = None,
    ) -> bool:
        """
        Adds a precedence relation between two tasks.

        Indicates that task_u must precede task_v. If no graph orientation is provided,
        the relation is added for both FORWARD and BACKWARD orientations.
        
        Args:
            task_u (int): The preceding task.
            task_v (int): The succeeding task.
            graph_orientation (Optional[GraphOrientation]): Specific orientation if desired.
        
        Returns:
            bool: True if the precedence was added successfully, False if it already exists.
        """
        task_1: int = task_u
        task_2: int = task_v
        orientations: List[GraphOrientation] = []
        success: bool = False

        if graph_orientation is None:
            orientations = EnumUtil.get_values(GraphOrientation) # type: ignore
        else:
            orientations.append(graph_orientation)

        for orientation in orientations:
            if graph_orientation is None:
                if orientation is GraphOrientation.FORWARD:
                    task_1 = task_u
                    task_2 = task_v
                else:
                    task_1 = task_v
                    task_2 = task_u
            try:
                if task_2 not in self.immediate_task_precedences[orientation]:
                    self.immediate_task_precedences[orientation][task_2] = []

                if task_1 not in self.immediate_task_precedences[orientation][task_2]:
                    self.immediate_task_precedences[orientation][task_2].append(task_1)
                    success = True
                else:
                    LogManager.invalid_action(
                        "add duplicated precedence between tasks {task_1} and {task_2}",
                        self.name,
                    )
            except Exception as e:
                LogManager.invalid_action(
                    "add precedence between tasks {task_1} and {task_2}", self.name, e
                )

        return success

    def _calculate_all_precedences(
        self, task: int, graph_orientation: GraphOrientation = GraphOrientation.FORWARD
    ) -> List[int]:
        """
        Recursively calculates all transitive precedences for a given task.

        Traverses the precedence graph (using DFS) to collect all tasks that must be completed before the given task.
        
        Args:
            task (int): The task identifier.
            graph_orientation (GraphOrientation): The orientation to consider (default is FORWARD).
        
        Returns:
            List[int]: A sorted list of all tasks that precede the given task.
        """
        visited = set()
        precedences = []

        def dfs(current_task):
            if current_task in self.immediate_task_precedences[graph_orientation]:
                for preceding_task in self.immediate_task_precedences[graph_orientation][current_task]:
                    if preceding_task not in visited:
                        visited.add(preceding_task)
                        precedences.append(preceding_task)
                        dfs(preceding_task)

        dfs(task)
        return sorted(precedences)

    def _fill_all_task_precedences(self) -> None:
        """
        Fills the complete precedence dictionary with transitive precedences for all tasks.

        For both FORWARD and BACKWARD orientations, computes all precedences and updates the internal structure.
        Finally, it calls order_solution_tasks to re-order tasks within stations.
        """
        for graph_orientation in EnumUtil.get_values(GraphOrientation):
            if isinstance(graph_orientation, GraphOrientation):
                for task in self.tasks:
                    all_precedences = self._calculate_all_precedences(task, graph_orientation)
                    self.all_task_precedences[graph_orientation][task] = all_precedences

        self.order_solution_tasks()

    def __get_tasks_executed_by_worker(self, worker: int) -> Tuple[int, ...]:
        """
        Retrieves the list of tasks that a specific worker can execute.

        Excludes tasks where the execution time is infinite.
        
        Args:
            worker (int): The worker identifier.
        
        Returns:
            Tuple[int, ...]: A tuple of task identifiers executable by the worker.
        """
        if worker not in self.workers:
            raise ValueError(f"Worker ID {worker} is invalid.")

        tasks_executed = []
        for task, execution_times in self._task_execution_times.items():
            if execution_times[worker - 1] != float("inf"):
                tasks_executed.append(task)

        return tuple(tasks_executed)

    def order_solution_tasks(self) -> None:
        """
        Orders the tasks for each station based on precedence constraints.

        Iterates over all stations and ensures that within each station, tasks are ordered so that 
        all precedence relationships are respected.
        """
        for station in self.stations:
            self.order_tasks_according_to_precedence(station)

    def order_tasks_according_to_precedence(self, station: int) -> None:
        """
        Orders tasks within a given station according to their precedence relationships.

        For tasks within the same station, if one task must precede another, the order is adjusted accordingly.
        
        Args:
            station (int): The station identifier whose tasks need ordering.
        """
        tasks = self.station_tasks_assignment[station]
        precedence_map: Dict[int, Set[int]] = {task: set() for task in tasks}

        for task in tasks:
            for predecessor in self.all_task_precedences[self.default_graph_orientation].get(task, []):
                if predecessor in tasks:
                    precedence_map[task].add(predecessor)

        ordered_tasks = self.topological_sort(precedence_map)
        self.station_tasks_assignment[station] = ordered_tasks

    def topological_sort(self, precedence_map: Dict[int, Set[int]]) -> List[int]:
        """
        Performs a topological sort on the tasks based on their precedence constraints.

        Args:
            precedence_map (Dict[int, Set[int]]): A dictionary where each key is a task and its value is a set of tasks that must precede it.
        
        Returns:
            List[int]: An ordered list of tasks that respects all precedence constraints.
        
        Raises:
            ValueError: If a cycle is detected in the precedence graph.
        """
        no_precedence = [task for task, precedents in precedence_map.items() if not precedents]
        ordered_tasks = []

        while no_precedence:
            task = no_precedence.pop()
            ordered_tasks.append(task)
            for dependent_task in precedence_map:
                if task in precedence_map[dependent_task]:
                    precedence_map[dependent_task].remove(task)
                    if not precedence_map[dependent_task]:
                        no_precedence.append(dependent_task)

        if len(ordered_tasks) == len(precedence_map):
            return ordered_tasks
        else:
            raise ValueError("Cycle detected in task precedence graph")

    def add_worker_to_station(
        self, worker: int, station: int, recalculate_cycle_time: bool = True
    ) -> bool:
        """
        Assigns a worker to a station if not already assigned.

        Updates the assignment, removes the worker from the unassigned list,
        recalculates the station's cycle time if requested, and updates the solution hash.
        
        Args:
            worker (int): The worker identifier.
            station (int): The station identifier.
            recalculate_cycle_time (bool): Whether to recalculate the cycle time after assignment.
        
        Returns:
            bool: True if the assignment was successful, False otherwise.
        """
        try:
            if self.station_worker_assignment.get(station) != worker:
                sol_hash = hash(self)
                self.station_worker_assignment[station] = worker
                self.worker_station_assignment[worker] = station
                self.unassigned_workers.remove(worker)

                if recalculate_cycle_time:
                    self.calculate_cycle_time(station, True)

                key = (sol_hash, station, worker)
                if (new_hash := AlwabpSolution._hash_worker_insertion_map.get(key)):
                    self._hash_memo = new_hash
                else:
                    self._hash_memo = None
                    new_hash = hash(self)
                    reverse_key = (new_hash, station, worker)
                    AlwabpSolution._hash_worker_insertion_map[key] = new_hash
                    AlwabpSolution._hash_worker_removal_map[reverse_key] = sol_hash

                return True
            else:
                LogManager.invalid_action("add worker to station, it was already assigned to it", self.name)
                return False
        except Exception as e:
            LogManager.invalid_action("add worker to station", self.name, e)
            return False

    def remove_worker_from_station(
        self, worker: int, station: int, recalculate_cycle_time: bool = True
    ) -> bool:
        """
        Removes a worker from a specified station.

        Updates the assignment mappings, adds the worker back to the unassigned list,
        recalculates the station's cycle time if requested, and updates the solution hash.
        
        Args:
            worker (int): The worker identifier.
            station (int): The station identifier.
            recalculate_cycle_time (bool): Whether to recalculate the cycle time after removal.
        
        Returns:
            bool: True if removal was successful, False otherwise.
        """
        try:
            if self.station_worker_assignment.get(station) == worker:
                sol_hash = hash(self)
                self.station_worker_assignment[station] = None
                self.worker_station_assignment[worker] = None
                self.unassigned_workers.append(worker)

                if recalculate_cycle_time:
                    self.calculate_cycle_time(station, True)

                key = (sol_hash, station, worker)
                if (new_hash := AlwabpSolution._hash_worker_removal_map.get(key)):
                    self._hash_memo = new_hash
                else:
                    self._hash_memo = None
                    new_hash = hash(self)
                    reverse_key = (new_hash, station, worker)
                    AlwabpSolution._hash_worker_removal_map[key] = new_hash
                    AlwabpSolution._hash_worker_insertion_map[reverse_key] = sol_hash

                return True
            else:
                LogManager.invalid_action("remove worker from station, it wasn't assigned to it", self.name)
                return False
        except Exception as e:
            LogManager.invalid_action("remove worker from station", self.name, e)
            return False

    def add_task_to_station(self, task: int, station: int) -> bool:
        """
        Adds a task to a station.

        If the task is not already assigned to the station, updates task-station mapping,
        removes the task from the unassigned list, updates cycle time, and refreshes the solution hash.
        
        Args:
            task (int): The task identifier.
            station (int): The station identifier.
        
        Returns:
            bool: True if the task was added successfully, False otherwise.
        """
        try:
            if task not in self.station_tasks_assignment.get(station, []):
                sol_hash = hash(self)
                self.station_tasks_assignment[station].append(task)
                self.task_station_assignment[task] = station
                self._unassigned_tasks.remove(task)

                worker = self.station_worker_assignment[station]
                self.station_cycle_time_memo[station] += self.get_task_execution_time(task, worker)

                if self._first_unassigned_station == station:
                    self._first_unassigned_station = None if station >= self._number_of_stations else station + 1

                key = (sol_hash, station, task)
                if (new_hash := AlwabpSolution._hash_task_insertion_map.get(key)):
                    self._hash_memo = new_hash
                else:
                    self._hash_memo = None
                    new_hash = hash(self)
                    reverse_key = (new_hash, station, task)
                    AlwabpSolution._hash_task_insertion_map[key] = new_hash
                    AlwabpSolution._hash_task_removal_map[reverse_key] = sol_hash

                return True
            else:
                LogManager.invalid_action("add task to station, it was already assigned to it", self.name)
                return False
        except Exception as e:
            LogManager.invalid_action("add task to station", self.name, e)
            return False

    def remove_task_from_station(self, task: int, station: int) -> bool:
        """
        Removes a task from a station.

        Updates the task-station mapping, adds the task back to the unassigned list, recalculates cycle time,
        and updates the solution hash.
        
        Args:
            task (int): The task identifier.
            station (int): The station identifier.
        
        Returns:
            bool: True if the removal was successful, False otherwise.
        """
        try:
            if task in self.station_tasks_assignment.get(station, []):
                sol_hash = hash(self)
                self.station_tasks_assignment[station].remove(task)
                self.task_station_assignment[task] = None
                self._unassigned_tasks.append(task)

                worker = self.station_worker_assignment[station]
                self.station_cycle_time_memo[station] -= self.get_task_execution_time(task, worker)

                if not self.station_tasks_assignment[station] and (
                    self._first_unassigned_station is None or station < self._first_unassigned_station
                ):
                    self._first_unassigned_station = station

                key = (sol_hash, station, task)
                if (new_hash := AlwabpSolution._hash_task_removal_map.get(key)):
                    self._hash_memo = new_hash
                else:
                    self._hash_memo = None
                    new_hash = hash(self)
                    reverse_key = (new_hash, station, task)
                    AlwabpSolution._hash_task_removal_map[key] = new_hash
                    AlwabpSolution._hash_task_insertion_map[reverse_key] = sol_hash

                return True
            else:
                LogManager.invalid_action("remove task from station, it wasn't assigned to it", self.name)
                return False
        except Exception as e:
            LogManager.invalid_action("remove task from station", self.name, e)
            return False

    def find_station_for_task(self, task: int) -> Optional[int]:
        """
        Finds the station where a given task is assigned.
        
        Args:
            task (int): The task identifier.
        
        Returns:
            Optional[int]: The station number if the task is assigned; otherwise, None.
        """
        return self.task_station_assignment[task]

    def find_station_for_worker(self, worker: int) -> Optional[int]:
        """
        Finds the station where a given worker is assigned.
        
        Args:
            worker (int): The worker identifier.
        
        Returns:
            Optional[int]: The station number if the worker is assigned; otherwise, None.
        """
        return self.worker_station_assignment[worker]

    def can_task_be_assigned_to(self, task: int, station: int, worker: Optional[int] = None) -> bool:
        """
        Checks whether a task can be assigned to a station with the specified worker.

        Validates whether the worker can execute the task, if the cycle time limit is not exceeded,
        and if the precedence constraints (both forward and reversed) are maintained.
        
        Args:
            task (int): The task identifier.
            station (int): The station identifier.
            worker (Optional[int]): The worker identifier; if None, uses the station's current worker.
        
        Returns:
            bool: True if the task can be assigned, False otherwise.
        """
        worker = worker or self.station_worker_assignment[station]

        if worker and task not in self.tasks_executed_by_worker[worker]:
            return False

        if (worker and self.cycle_time_limit and
            (self.station_cycle_time_memo[station] + self.get_task_execution_time(task, worker)) > self.cycle_time_limit):
            return False

        for preceding_task in self.all_task_precedences[self.default_graph_orientation][task]:
            another_station = self.find_station_for_task(preceding_task)
            if not another_station or another_station > station:
                return False

        reversed_graph = GraphOrientation.reverse(self.default_graph_orientation)
        for sucessor_task in self.all_task_precedences[reversed_graph][task]:
            another_station = self.find_station_for_task(sucessor_task)
            if another_station and another_station < station:
                return False

        return True

    def get_task_execution_time(self, task: int, worker: Optional[int] = None, custom_dict: Optional[Dict[int, List[int]]] = None) -> float:
        """
        Retrieves the execution time for a task.

        If a worker is specified and can execute the task, returns the worker-specific execution time.
        Otherwise, returns the maximum execution time (or uses a custom dictionary if provided).
        
        Args:
            task (int): The task identifier.
            worker (Optional[int]): The worker identifier.
            custom_dict (Optional[Dict[int, List[int]]]): A custom execution time matrix.
        
        Returns:
            float: The execution time.
        """
        if not custom_dict:
            if worker and task in self.tasks_executed_by_worker[worker]:
                return self._task_execution_times[task][worker - 1]
            else:
                return max(self._bounded_task_execution_times[task])
        else:
            if worker:
                return custom_dict[task][worker - 1]
            else:
                return max(custom_dict[task])

    def get_best_worker_for_task(self, task: int) -> int:
        """
        Returns the worker with the best (minimum) execution time for the specified task.
        
        Args:
            task (int): The task identifier.
        
        Returns:
            int: The best worker's identifier.
        """
        return self._best_worker_for_task[task]

    def max_task_execution_time(self, task: int, worker: Optional[int] = None, custom_dict: Optional[Dict[int, List[int]]] = None, workers: Optional[List[int]] = None) -> float:
        """
        Calculates the maximum execution time for a task considering a subset of workers.

        If workers is provided, only considers execution times for those workers.
        
        Args:
            task (int): The task identifier.
            worker (Optional[int]): Ignored in this function.
            custom_dict (Optional[Dict[int, List[int]]]): Custom execution time data.
            workers (Optional[List[int]]): List of worker identifiers to consider.
        
        Returns:
            float: The maximum execution time among the considered workers.
        """
        task_times = custom_dict[task] if custom_dict else self._bounded_task_execution_times[task]
        if workers:
            return max(task_times[worker - 1] for worker in workers)
        return max(task_times)

    def min_task_execution_time(self, task: int, worker: Optional[int] = None, custom_dict: Optional[Dict[int, List[int]]] = None, workers: Optional[List[int]] = None) -> float:
        """
        Calculates the minimum execution time for a task considering a subset of workers.

        Args:
            task (int): The task identifier.
            worker (Optional[int]): Ignored in this function.
            custom_dict (Optional[Dict[int, List[int]]]): Custom execution time data.
            workers (Optional[List[int]]): List of worker identifiers to consider.
        
        Returns:
            float: The minimum execution time among the considered workers.
        """
        task_times = custom_dict[task] if custom_dict else self._bounded_task_execution_times[task]
        if workers:
            return min(task_times[worker - 1] for worker in workers)
        return min(task_times)

    def average_task_execution_time(self, task: int, worker: Optional[int] = None, custom_dict: Optional[Dict[int, List[int]]] = None, workers: Optional[List[int]] = None) -> float:
        """
        Calculates the average execution time for a task over the considered workers.

        Args:
            task (int): The task identifier.
            worker (Optional[int]): Ignored in this function.
            custom_dict (Optional[Dict[int, List[int]]]): Custom execution time data.
            workers (Optional[List[int]]): List of worker identifiers to consider.
        
        Returns:
            float: The average execution time.
        """
        task_times = custom_dict[task] if custom_dict else self._bounded_task_execution_times[task]
        if workers:
            total_time = sum(task_times[worker - 1] for worker in workers)
            number_of_workers = len(workers)
        else:
            total_time = sum(task_times)
            number_of_workers = self._number_of_workers

        return total_time / max(1, number_of_workers)

    def number_all_task_precedences(self, task: int, custom_dict: Optional[Dict[int, List[int]]]) -> int:
        """
        Returns the count of all (immediate and transitive) precedence constraints for a task.
        
        Args:
            task (int): The task identifier.
            custom_dict (Optional[Dict[int, List[int]]]): Custom precedence data.
        
        Returns:
            int: The count of all precedences.
        """
        result = custom_dict or self.all_task_precedences[self.default_graph_orientation]
        return len(result[task])

    def number_immediate_task_precedences(self, task: int, custom_dict: Optional[Dict[int, List[int]]]) -> int:
        """
        Returns the count of immediate precedence constraints for the given task.
        
        Args:
            task (int): The task identifier.
            custom_dict (Optional[Dict[int, List[int]]]): Custom precedence data.
        
        Returns:
            int: The count of immediate precedences.
        """
        result = custom_dict or self.immediate_task_precedences[self.default_graph_orientation]
        return len(result[task])

    def decreasing_number_all_task_precedences(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> int:
        """
        Returns the negative count of all precedences for a task.
        
        Useful for ordering tasks where fewer precedences are preferred.
        """
        return -self.number_all_task_precedences(task, custom_dict)

    def decreasing_number_immediate_task_precedences(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> int:
        """
        Returns the negative count of immediate precedences for a task.
        """
        return -self.number_immediate_task_precedences(task, custom_dict)

    def decreasing_min_task_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Returns the negative minimum execution time for a task.
        
        Used in ordering tasks where lower times are more favorable.
        """
        return -self.min_task_execution_time(task, custom_dict=custom_dict)

    def decreasing_max_task_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Returns the negative maximum execution time for a task.
        """
        return -self.max_task_execution_time(task, custom_dict=custom_dict)

    def decreasing_average_task_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Returns the negative average execution time for a task.
        """
        return -self.average_task_execution_time(task, custom_dict=custom_dict)

    def __calculate_over_task_and_precedences(self, func: Callable[[int, Optional[int], Optional[Dict[int, List[int]]]], float], task: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Applies the given function to the specified task and all its transitive precedences, summing the results.
        
        Args:
            func (Callable): The function to apply to each task.
            task (int): The task identifier.
            custom_dict (Optional[Dict[int, List[int]]]): Custom data to pass to the function.
        
        Returns:
            float: The summed value.
        """
        precedences = self.all_task_precedences[self.default_graph_orientation][task]
        return func(task, None, custom_dict) + sum(func(precedence, None, custom_dict) for precedence in precedences)

    def max_positional_weight_minus(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Computes the positional weight of a task as the sum of minimum execution times over the task and its precedences.
        """
        return self.__calculate_over_task_and_precedences(self.min_task_execution_time, task, custom_dict)

    def max_positional_weight_plus(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Computes the positional weight of a task as the sum of maximum execution times over the task and its precedences.
        """
        return self.__calculate_over_task_and_precedences(self.max_task_execution_time, task, custom_dict)

    def max_positional_weight_average(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Computes the positional weight of a task as the sum of average execution times over the task and its precedences.
        """
        return self.__calculate_over_task_and_precedences(self.average_task_execution_time, task, custom_dict)

    def difference_to_best_worker(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Calculates the difference in execution time between the given worker and the best worker for a task.
        """
        best_worker = self.get_best_worker_for_task(task)
        return self.get_task_execution_time(task, worker, custom_dict) - self.get_task_execution_time(task, best_worker, custom_dict)

    def ratio_to_best_worker(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Calculates the ratio of the execution time of a given worker to that of the best worker for the task.
        """
        best_worker = self.get_best_worker_for_task(task)
        return self.get_task_execution_time(task, worker, custom_dict) / (self.get_task_execution_time(task, best_worker, custom_dict) or 1)

    def ratio_of_number_all_task_precedences_over_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Computes the ratio of the total number of precedences for a task to its execution time.
        """
        return self.number_all_task_precedences(task, custom_dict) / (self.get_task_execution_time(task, worker, custom_dict) or 1)

    def ratio_of_number_immediate_task_precedences_over_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Computes the ratio of the immediate precedences count for a task to its execution time.
        """
        return self.number_immediate_task_precedences(task, custom_dict) / (self.get_task_execution_time(task, worker, custom_dict) or 1)

    def decreasing_ratio_of_number_all_task_precedences_over_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Returns the negative ratio of the total number of precedences to the task's execution time.
        """
        return -self.ratio_of_number_all_task_precedences_over_time(task, worker, custom_dict)

    def decreasing_ratio_of_number_immediate_task_precedences_over_time(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Returns the negative ratio of the immediate precedences count to the task's execution time.
        """
        return -self.ratio_of_number_immediate_task_precedences_over_time(task, worker, custom_dict)

    def get_rank(self, task: int, worker: int, custom_dict: Optional[Dict[int, List[int]]]) -> float:
        """
        Retrieves the rank of the worker for a specific task based on execution times.
        
        Args:
            task (int): The task identifier.
            worker (int): The worker identifier.
            custom_dict (Optional[Dict[int, List[int]]]): Custom execution time data.
        
        Returns:
            float: The rank of the worker.
        """
        if not custom_dict:
            return self._workers_ranks[task][worker]
        else:
            return self._compute_workers_ranks(custom_dict, task, worker)[task][worker]

    def __get_func_for_task_ordering_rules(self, task_ordering_rule: TaskOrderingRule) -> Callable[[int, int, Optional[Dict[int, List[int]]]], float]:
        """
        Retrieves the function used to calculate the task ordering rule based on the specified type.
        
        Args:
            task_ordering_rule (TaskOrderingRule): The ordering rule type.
        
        Returns:
            Callable: A function that computes the ordering weight for a task.
        
        Raises:
            ValueError: If the ordering rule is not recognized.
        """
        if task_ordering_rule == TaskOrderingRule.MAX_F:
            return self.decreasing_number_all_task_precedences
        elif task_ordering_rule == TaskOrderingRule.MAX_IF:
            return self.decreasing_number_immediate_task_precedences
        elif task_ordering_rule == TaskOrderingRule.MAX_TIME_MINUS:
            return self.decreasing_min_task_time
        elif task_ordering_rule == TaskOrderingRule.MAX_TIME_PLUS:
            return self.decreasing_max_task_time
        elif task_ordering_rule == TaskOrderingRule.MAX_TIME_AVERAGE:
            return self.decreasing_average_task_time
        elif task_ordering_rule == TaskOrderingRule.MIN_TIME_MINUS:
            return self.min_task_execution_time
        elif task_ordering_rule == TaskOrderingRule.MIN_TIME_PLUS:
            return self.max_task_execution_time
        elif task_ordering_rule == TaskOrderingRule.MIN_TIME_AVERAGE:
            return self.average_task_execution_time
        elif task_ordering_rule == TaskOrderingRule.MAX_PW_MINUS:
            return self.max_positional_weight_minus
        elif task_ordering_rule == TaskOrderingRule.MAX_PW_PLUS:
            return self.max_positional_weight_plus
        elif task_ordering_rule == TaskOrderingRule.MAX_PW_AVERAGE:
            return self.max_positional_weight_average
        elif task_ordering_rule == TaskOrderingRule.MIN_D:
            return self.difference_to_best_worker
        elif task_ordering_rule == TaskOrderingRule.MIN_R:
            return self.ratio_to_best_worker
        elif task_ordering_rule == TaskOrderingRule.MAX_F_TIME:
            return self.decreasing_ratio_of_number_all_task_precedences_over_time
        elif task_ordering_rule == TaskOrderingRule.MAX_IF_TIME:
            return self.decreasing_ratio_of_number_immediate_task_precedences_over_time
        elif task_ordering_rule == TaskOrderingRule.MIN_RANK:
            return self.get_rank
        else:
            raise ValueError("Task Ordering Rule must be one of the listed possibilities.")

    def _calculate_task_ordering_rules(self, priority_matrix: Optional[Dict[int, List[int]]] = None) -> Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]]:
        """
        Calculates and stores task ordering weights for each task based on various criteria.

        For each task and each task ordering rule, computes a weight (e.g., based on execution times,
        precedence counts, etc.) and stores the results in the task_ordering_rules attribute.
        
        Args:
            priority_matrix (Optional[Dict[int, List[int]]]): Custom data for calculating ordering weights.
        
        Returns:
            Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]]: Updated ordering rules for all tasks.
        """
        if not priority_matrix:
            result_storage = self.task_ordering_rules
        else:
            result_storage: Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]] = { # type: ignore
                weight_type: {task: (-1.0,) * self._number_of_workers for task in self.tasks}
                for weight_type in EnumUtil.get_values(TaskOrderingRule)
            }

        for task in self.tasks:
            for task_ordering_rule in EnumUtil.get_values(TaskOrderingRule):
                if isinstance(task_ordering_rule, TaskOrderingRule):
                    weight_function = self.__get_func_for_task_ordering_rules(task_ordering_rule)
                    task_rule_dict = result_storage[task_ordering_rule]
                    task_rule_dict[task] = tuple(map(lambda worker: weight_function(task, worker, priority_matrix), self.workers))

        return result_storage

    def get_task_ordering_rules_value(self, task: int, worker: int, variation: TaskOrderingRule) -> float:
        """
        Retrieves the task ordering weight for a given task, worker, and ordering variation.
        
        Args:
            task (int): The task identifier.
            worker (int): The worker identifier.
            variation (TaskOrderingRule): The ordering rule variation.
        
        Returns:
            float: The ordering weight value.
        """
        return self.task_ordering_rules[variation][task][worker]

    def get_task_ordering_rules_dict(self, priority_matrix: Optional[Dict[int, List[int]]] = None) -> Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]]:
        """
        Retrieves the dictionary of task ordering rules.
        
        If a priority_matrix is provided, the ordering rules are recalculated using it.
        
        Args:
            priority_matrix (Optional[Dict[int, List[int]]]): Custom data for recalculation.
        
        Returns:
            Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]]: The task ordering rules.
        """
        if not priority_matrix:
            return self.task_ordering_rules
        else:
            return self._calculate_task_ordering_rules(priority_matrix)

    def get_min_restricted_lower_bound(self) -> List[int]:
        """
        Orders unassigned workers based on their minimum restricted lower bound (RLB).

        The RLB for a worker is the sum of minimum execution times for tasks that can be assigned,
        divided among the remaining unassigned workers.
        
        Returns:
            List[int]: A sorted list of worker IDs based on their RLB.
        """
        return sorted(self.unassigned_workers, key=lambda worker: self.get_worker_min_rlb(worker))

    def get_worker_min_rlb(self, worker: int, override_unassigned_tasks: List[int] = []) -> int:
        """
        Calculates the minimum restricted lower bound (RLB) for a worker.

        The RLB is computed as the total minimum execution time of tasks (that the worker can perform and are unassigned)
        divided by the number of other unassigned workers.
        
        Args:
            worker (int): The worker identifier.
            override_unassigned_tasks (List[int]): Optional list of tasks to use instead of the current unassigned list.
        
        Returns:
            int: The computed minimum RLB.
        """
        unassigned_tasks = override_unassigned_tasks.copy() if override_unassigned_tasks else self._unassigned_tasks

        if len(self.unassigned_workers) == 1:
            return 0

        pending_assignable_tasks = [task for task in self.tasks_executed_by_worker[worker] if task in unassigned_tasks]
        unassigned_workers = self.unassigned_workers.copy()
        unassigned_workers.remove(worker)

        amount_of_time = 0
        for task in pending_assignable_tasks:
            amount_of_time += int(self.min_task_execution_time(task, workers=unassigned_workers))

        return amount_of_time // (len(unassigned_workers) or 1)

    def get_first_unassigned_station(self) -> Optional[int]:
        """
        Retrieves the first station that has no task assigned.

        Returns:
            Optional[int]: The station number, or None if all stations have assignments.
        """
        return self._first_unassigned_station

    def station_would_be_feasible(self, station: int, worker: int) -> bool:
        """
        Checks if a station's task list is feasible for a given worker.

        Verifies that the worker can execute all tasks in the station and, if a cycle time limit is set,
        that the total execution time does not exceed the limit.
        
        Args:
            station (int): The station identifier.
            worker (int): The worker identifier.
        
        Returns:
            bool: True if feasible, False otherwise.
        """
        tasks = self.station_tasks_assignment[station]
        executable_tasks = self.tasks_executed_by_worker[worker]

        for task in tasks:
            if task not in executable_tasks:
                return False

        if self.cycle_time_limit is not None:
            total_execution_time = sum(self.get_task_execution_time(task, worker) for task in tasks)
            if total_execution_time > self.cycle_time_limit:
                return False

        return True

    def simulate_worker_tasks_allocation(self, worker: int, movements: List[AlwabpInsertionMovement]) -> List[AlwabpInsertionMovement]:
        """
        Simulates task allocation for a given worker based on provided movements.

        Filters the movements to include only those tasks that the worker can execute and,
        if a cycle time limit is set, ensures the cumulative execution time does not exceed the limit.
        
        Args:
            worker (int): The worker identifier.
            movements (List[AlwabpInsertionMovement]): A list of potential task insertion movements.
        
        Returns:
            List[AlwabpInsertionMovement]: The subset of movements that are feasible.
        """
        available_moves = [move for move in movements if move.task in self.tasks_executed_by_worker[worker]]

        if self.cycle_time_limit:
            selected_moves = []
            total_time = 0.0

            for move in available_moves:
                if move.task:
                    task_time = self.get_task_execution_time(move.task, worker)
                    if total_time + task_time <= self.cycle_time_limit:
                        selected_moves.append(move)
                        total_time += task_time
                    if total_time == self.cycle_time_limit:
                        break

            return selected_moves
        else:
            return available_moves

    def get_critical_workstations(self) -> List[int]:
        """
        Identifies the critical workstations.

        A critical workstation is defined as one whose cycle time equals the maximum cycle time,
        except when all stations are critical.
        
        Returns:
            List[int]: A list of station identifiers that are critical.
        """
        max_cycle_time = self.get_max_cycle_time()
        critical_stations = []

        for station in self.stations:
            cycle_time = self.calculate_cycle_time(station)
            if cycle_time == max_cycle_time:
                critical_stations.append(station)

        if len(critical_stations) == self._number_of_stations:
            return []
        return critical_stations

    def get_number_of_critical_workstations(self) -> int:
        """
        Calculates the number of critical workstations.
        
        Returns:
            int: The count of critical workstations.
        """
        return len(self.get_critical_workstations())

    @staticmethod
    def get_related_tasks_from_movement(movement: Movement) -> Set[int]:
        """
        Retrieves the set of tasks related to a given movement.

        For composite movements (MultipleMovement), recursively gathers tasks from all sub-movements.
        For insertion or removal movements, returns the associated task if present.
        
        Args:
            movement (Movement): The movement instance.
        
        Returns:
            Set[int]: A set of related task identifiers.
        """
        from oahf.Base.MultipleMovement import MultipleMovement
        from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
        from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement

        related_tasks: List[int] = []
        if isinstance(movement, MultipleMovement):
            [related_tasks.extend(AlwabpSolution.get_related_tasks_from_movement(m)) for m in movement.movements]
        elif (isinstance(movement, AlwabpInsertionMovement) or isinstance(movement, AlwabpRemovalMovement)) and movement.task:
            related_tasks.append(movement.task)

        return set(related_tasks)

    @classmethod
    def update_task_station_frequencies(cls, solution: "AlwabpSolution", task_station_frequency: Dict[int, Dict[int, int]]) -> None:
        """
        Updates the frequency counts of task assignments to stations across solutions.

        Iterates over each station in the solution and increments the frequency for each task
        assigned to that station.
        
        Args:
            solution (AlwabpSolution): The solution instance.
            task_station_frequency (Dict[int, Dict[int, int]]): A nested dictionary for frequency counts.
        """
        for station, tasks in solution.station_tasks_assignment.items():
            for task in tasks:
                if task not in task_station_frequency:
                    task_station_frequency[task] = {}
                if station not in task_station_frequency[task]:
                    task_station_frequency[task][station] = 0
                task_station_frequency[task][station] += 1

    @classmethod
    def update_worker_station_frequencies(cls, solution: "AlwabpSolution", worker_station_frequency: Dict[int, Dict[int, int]]) -> None:
        """
        Updates the frequency counts of worker assignments to stations across solutions.

        Iterates over each station and updates the frequency of the worker assigned.
        
        Args:
            solution (AlwabpSolution): The solution instance.
            worker_station_frequency (Dict[int, Dict[int, int]]): A nested dictionary for frequency counts.
        """
        for station, worker in solution.station_worker_assignment.items():
            if worker is not None:
                if worker not in worker_station_frequency:
                    worker_station_frequency[worker] = {}
                if station not in worker_station_frequency[worker]:
                    worker_station_frequency[worker][station] = 0
                worker_station_frequency[worker][station] += 1

    @classmethod
    def get_station_with_highest_frequency(cls, frequency_data: Dict[int, Dict[int, int]], entity: int) -> Optional[int]:
        """
        Determines the station where a given task or worker appears most frequently.

        In the case of ties, the station with the smallest index is chosen.
        
        Args:
            frequency_data (Dict[int, Dict[int, int]]): Frequency data mapping entity IDs to station counts.
            entity (int): The task or worker identifier.
        
        Returns:
            Optional[int]: The station with the highest frequency, or None if not found.
        """
        if entity not in frequency_data:
            return None
        station_frequencies = frequency_data[entity]
        max_station = min(station_frequencies.items(), key=lambda x: (-x[1], x[0]))
        return max_station[0]

    @classmethod
    def get_station_with_lowest_frequency(cls, frequency_data: Dict[int, Dict[int, int]], entity: int) -> Optional[int]:
        """
        Determines the station where a given task or worker appears least frequently.

        In the case of ties, the station with the smallest index is chosen.
        
        Args:
            frequency_data (Dict[int, Dict[int, int]]): Frequency data mapping entity IDs to station counts.
            entity (int): The task or worker identifier.
        
        Returns:
            Optional[int]: The station with the lowest frequency, or None if not found.
        """
        if entity not in frequency_data:
            return None
        station_frequencies = frequency_data[entity]
        min_station = min(station_frequencies.items(), key=lambda x: (x[1], x[0]))
        return min_station[0]

    @classmethod
    def get_station_with_highest_frequency_to_task(cls, task: int) -> Optional[int]:
        """
        Retrieves the station where a given task appears most frequently.
        
        Args:
            task (int): The task identifier.
        
        Returns:
            Optional[int]: The station identifier, or None if not found.
        """
        return cls.get_station_with_highest_frequency(cls._task_station_frequency, task)

    @classmethod
    def get_station_with_lowest_frequency_to_task(cls, task: int) -> Optional[int]:
        """
        Retrieves the station where a given task appears least frequently.
        
        Args:
            task (int): The task identifier.
        
        Returns:
            Optional[int]: The station identifier, or None if not found.
        """
        return cls.get_station_with_lowest_frequency(cls._task_station_frequency, task)

    @classmethod
    def get_station_with_highest_frequency_to_worker(cls, worker: int) -> Optional[int]:
        """
        Retrieves the station where a given worker appears most frequently.
        
        Args:
            worker (int): The worker identifier.
        
        Returns:
            Optional[int]: The station identifier, or None if not found.
        """
        return cls.get_station_with_highest_frequency(cls._worker_station_frequency, worker)

    @classmethod
    def get_station_with_lowest_frequency_to_worker(cls, worker: int) -> Optional[int]:
        """
        Retrieves the station where a given worker appears least frequently.
        
        Args:
            worker (int): The worker identifier.
        
        Returns:
            Optional[int]: The station identifier, or None if not found.
        """
        return cls.get_station_with_lowest_frequency(cls._worker_station_frequency, worker)

    @classmethod
    def update_intensification_diversification_structures(cls, solution: "AlwabpSolution") -> None:
        """
        Updates frequency structures for both tasks and workers based on the solution.

        This assists in diversification and intensification strategies by tracking assignment frequencies.
        
        Args:
            solution (AlwabpSolution): The solution instance.
        """
        cls.update_task_station_frequencies(solution, cls._task_station_frequency)
        cls.update_worker_station_frequencies(solution, cls._worker_station_frequency)

    @classmethod
    def reset_intensification_diversification_structures(cls) -> None:
        """
        Resets the frequency tracking structures for tasks and workers.
        """
        cls._task_station_frequency = {}
        cls._worker_station_frequency = {}

    def find_move_to(self, other_solution: "AlwabpSolution") -> Movement:
        """
        Identifies the set of movements required to transform this solution into another solution.

        Compares task and worker assignments between solutions and generates corresponding removal and insertion movements.
        The resulting movement is a composite movement (MultipleMovement) that encapsulates all individual moves.
        
        Args:
            other_solution (AlwabpSolution): The target solution.
        
        Returns:
            Movement: A MultipleMovement instance containing all necessary movements.
        """
        other_solution.default_graph_orientation = self.default_graph_orientation
        moves = []

        for task, s1 in self.task_station_assignment.items():
            s2 = other_solution.task_station_assignment.get(task)
            if s1 != s2:
                moves.extend([
                    AlwabpRemovalMovement(task, None, s1, self),
                    AlwabpInsertionMovement(task, None, s2, self),
                ])

        for worker, s1 in self.worker_station_assignment.items():
            s2 = other_solution.worker_station_assignment.get(worker)
            if s1 != s2:
                moves.extend([
                    AlwabpRemovalMovement(None, worker, s1, self),
                    AlwabpInsertionMovement(None, worker, s2, self),
                ])

        return MultipleMovement(self, moves)
