import copy
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from oahf.Base.Movement import Movement
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.Logger.LogManager import LogManager
from oahf.Utils import EnumUtil


class GraphOrientation(Enum):
    FORWARD = auto()
    BACKWARD = auto()

    @classmethod
    def reverse(cls, graph_orientation: "GraphOrientation") -> "GraphOrientation":
        if graph_orientation == GraphOrientation.FORWARD:
            return GraphOrientation.BACKWARD
        else:
            return GraphOrientation.FORWARD


class MaxPositionalWeightType(Enum):
    MAX = auto()
    MIN = auto()
    AVERAGE = auto()


class AlwabpSolution(Solution):
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
        "max_positional_weight",
        "station_cycle_time_memo",
        "_cycle_time_limit",
        "_default_graph_orientation",
        "print_solution_updates",
        "name",
    )

    def __init__(
        self, number_of_tasks: int, number_of_workers: int, number_of_stations: int
    ) -> None:
        super().__init__()  # Calls Entity.__init__ via Solution
        self.name = "AlwabpSolution"

        # You may consider converting these to tuples if they are never mutated:
        self.tasks: Tuple[int, ...] = tuple(range(1, number_of_tasks + 1))
        self.workers: Tuple[int, ...] = tuple(range(1, number_of_workers + 1))
        self.stations: Tuple[int, ...] = tuple(range(1, number_of_stations + 1))

        # Create dictionaries with lists that may be mutated.
        self._task_execution_times: Dict[int, List[float]] = {
            task: [float("inf")] * number_of_workers for task in self.tasks
        }
        self._bounded_task_execution_times: Dict[int, List[float]] = {
            task: times.copy() for task, times in self._task_execution_times.items()
        }

        self.station_worker_assignment: Dict[int, Optional[int]] = {
            station: None for station in self.stations
        }
        self.worker_station_assignment: Dict[int, Optional[int]] = {
            worker: None for worker in self.workers
        }
        self.station_tasks_assignment: Dict[int, List[int]] = {
            station: [] for station in self.stations
        }
        self.task_station_assignment: Dict[int, Optional[int]] = {
            task: None for task in self.tasks
        }

        self._unassigned_workers: List[int] = list(self.workers)
        self._unassigned_tasks: List[int] = list(self.tasks)

        self.immediate_task_precedences: Dict[  # type: ignore
            GraphOrientation, Dict[int, List[int]]
        ] = {
            graph_orientation: {task: [] for task in self.tasks}
            for graph_orientation in EnumUtil.get_values(GraphOrientation)
        }
        self.tasks_executed_by_worker: Dict[int, Tuple[int, ...]] = {
            worker: tuple() for worker in self.workers
        }
        self._cycle_time_limit: Optional[float] = None

        self.all_task_precedences: Dict[GraphOrientation, Dict[int, List[int]]] = {  # type: ignore
            graph_orientation: {task: [] for task in self.tasks}
            for graph_orientation in EnumUtil.get_values(GraphOrientation)
        }

        self.max_positional_weight: Dict[MaxPositionalWeightType, Dict[int, float]] = {  # type: ignore
            weight_type: {task: -1 for task in self.tasks}
            for weight_type in EnumUtil.get_values(MaxPositionalWeightType)
        }

        self.station_cycle_time_memo: Dict[int, float] = {
            station: 0.0 for station in self.stations
        }
        self._default_graph_orientation: GraphOrientation = GraphOrientation.FORWARD

        self.print_solution_updates: bool = False

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        # --- Copy parent's private attributes ---
        # Since __slots__ bypasses __dict__, check if they exist via __dict__ fallback
        for attr in ("_Entity__id", "_Entity__name"):
            if attr in self.__dict__:
                setattr(result, attr, self.__dict__[attr])

        result.get_new_id()

        # --- Copy attributes from Solution and AlwabpSolution ---
        # For immutable or "safe" objects, we can assign directly.
        result.print_solution_updates = self.print_solution_updates
        result.name = self.name
        result.tasks = self.tasks
        result.workers = self.workers
        result.stations = self.stations

        # For dictionaries whose values are mutable lists, use shallow copies.
        result._task_execution_times = {
            k: v.copy() for k, v in self._task_execution_times.items()
        }
        result._bounded_task_execution_times = {
            k: v.copy() for k, v in self._bounded_task_execution_times.items()
        }

        result.station_worker_assignment = self.station_worker_assignment.copy()
        result.worker_station_assignment = self.worker_station_assignment.copy()
        result.station_tasks_assignment = {
            k: v.copy() for k, v in self.station_tasks_assignment.items()
        }
        result.task_station_assignment = self.task_station_assignment.copy()
        result._unassigned_workers = self._unassigned_workers.copy()
        result._unassigned_tasks = self._unassigned_tasks.copy()

        # For nested dictionaries, perform a shallow copy of the inner lists.
        result.immediate_task_precedences = {
            orientation: {task: lst.copy() for task, lst in inner.items()}
            for orientation, inner in self.immediate_task_precedences.items()
        }
        result.tasks_executed_by_worker = self.tasks_executed_by_worker
        result.all_task_precedences = {
            orientation: {task: lst.copy() for task, lst in inner.items()}
            for orientation, inner in self.all_task_precedences.items()
        }
        result.max_positional_weight = {
            k: v.copy() for k, v in self.max_positional_weight.items()
        }
        result.station_cycle_time_memo = self.station_cycle_time_memo.copy()

        result._cycle_time_limit = self._cycle_time_limit
        result._default_graph_orientation = self._default_graph_orientation

        return result

    def copy(self) -> "AlwabpSolution":
        """
        Creates a deep copy of the current solution using the custom __deepcopy__ method.
        """
        return copy.deepcopy(self)

    def validate_aspects(self) -> bool:
        if self.cycle_time_limit and (
            len(self.unassigned_tasks) > 0 or len(self._unassigned_workers) > 0
        ):
            self.cycle_time_limit = self.cycle_time_limit + 1
            self.reset()
            return False
        # else:
        # self.narrow_bounds()
        return super().validate_aspects()

    def narrow_bounds(self) -> None:
        self.cycle_time_limit = self.get_max_cycle_time()

    def reset(self) -> None:
        self.station_worker_assignment: Dict[int, Optional[int]] = {
            station: None for station in self.stations
        }
        self.worker_station_assignment: Dict[int, Optional[int]] = {
            worker: None for worker in self.workers
        }
        self.station_tasks_assignment: Dict[int, List[int]] = {
            station: [] for station in self.stations
        }
        self.task_station_assignment: Dict[int, Optional[int]] = {
            task: None for task in self.tasks
        }
        self._unassigned_workers: List[int] = list(self.workers)
        self._unassigned_tasks: List[int] = list(self.tasks)
        self.station_cycle_time_memo: Dict[int, float] = {
            station: 0.0 for station in self.stations
        }

    def process_graph_data(self) -> None:
        self._update_tasks_executed_by_worker()
        self._fill_all_task_precedences()
        self._update_bounded_task_execution_times(499)
        self._calculate_max_positional_weights()

    def _update_tasks_executed_by_worker(self) -> None:
        self.tasks_executed_by_worker = {
            worker: self.__get_tasks_executed_by_worker(worker)
            for worker in self.workers
        }

    @property
    def unassigned_workers(self):
        return self._unassigned_workers

    @property
    def cycle_time_limit(self) -> Optional[float]:
        return self._cycle_time_limit

    @cycle_time_limit.setter
    def cycle_time_limit(self, value: float) -> None:
        if self._cycle_time_limit:
            self.print_update(f"Updated cycle time limit to {str(value)}.")
        else:
            print(f"Starting with cycle time limit as {str(value)}.")
        self._cycle_time_limit = value
        # self._update_bounded_task_execution_times()
        # self._calculate_max_positional_weights()

    @property
    def default_graph_orientation(self) -> GraphOrientation:
        return self._default_graph_orientation

    @default_graph_orientation.setter
    def default_graph_orientation(self, graph_orientation: GraphOrientation) -> None:
        if self._default_graph_orientation == graph_orientation:
            return

        self._default_graph_orientation = graph_orientation
        self._reverse_solution()

    def _reverse_solution(self) -> None:
        """
        Reverses the assignments of tasks and cycle times between stations in the solution.
        """
        num_stations: int = len(self.stations)

        for i in range(1, int(num_stations / 2) + 1):
            # Swap tasks between station i and its mirror counterpart
            (
                self.station_tasks_assignment[i],
                self.station_tasks_assignment[num_stations - i + 1],
            ) = (
                self.station_tasks_assignment[num_stations - i + 1],
                self.station_tasks_assignment[i],
            )

            # Swap workers between station i and its mirror counterpart
            (
                self.station_worker_assignment[i],
                self.station_worker_assignment[num_stations - i + 1],
            ) = (
                self.station_worker_assignment[num_stations - i + 1],
                self.station_worker_assignment[i],
            )

            # Swap cycle times between station i and its mirror counterpart
            (
                self.station_cycle_time_memo[i],
                self.station_cycle_time_memo[num_stations - i + 1],
            ) = (
                self.station_cycle_time_memo[num_stations - i + 1],
                self.station_cycle_time_memo[i],
            )

        for station in self.stations:
            worker = self.station_worker_assignment[station]
            if worker is not None:
                self.worker_station_assignment[worker] = station

    def fix_solution(self) -> None:
        self.default_graph_orientation = GraphOrientation.FORWARD
        self.order_solution_tasks()
        self.narrow_bounds()

    def _update_bounded_task_execution_times(self, cycle_time: Optional[float]) -> None:
        self._bounded_task_execution_times = copy.deepcopy(self._task_execution_times)

        if cycle_time:
            for task in self.tasks:
                float_array = np.array(
                    self._bounded_task_execution_times[task]
                )  # Convert the list to a NumPy array for vectorized operations
                float_array[float_array == np.inf] = (
                    cycle_time + 1
                )  # Replace float('inf')
                self._bounded_task_execution_times[task] = float_array.tolist()

    @property
    def unassigned_tasks(self):
        return self._unassigned_tasks

    def set_task_execution_times(
        self, task_number: int, execution_times: List[float]
    ) -> None:
        """
        Sets the list of execution times for a specific task.

        Args:
            task_number (int): The task number for which to set the execution times.
            execution_times (List[int]): A list of execution times for each worker.

        Raises:
            ValueError: If the task number is invalid or
            if the length of execution times does not match the number of workers.
        """
        if task_number not in self.tasks:
            raise ValueError(
                f"Task number {task_number} is invalid. It must be between 1 and {len(self.tasks)}."
            )

        if len(execution_times) != len(self.workers):
            raise ValueError(
                f"Execution times must be provided for all {len(self.workers)} workers."
            )

        # Set the execution times for the task
        self._task_execution_times[task_number] = execution_times

    def decompose_solution(self, k: int) -> Optional[List["AlwabpSolution"]]:
        raise NotImplementedError("Decomposition is not supported for this problem.")

    def merge_solutions(self, solutions: List["AlwabpSolution"]) -> "AlwabpSolution":
        raise NotImplementedError("Merging is not supported for this problem.")

    def solution_hash(self) -> int:
        """
        Generates a hash for the solution based on assignments.

        Returns:
            int: The hash value of the solution.
        """
        return hash(
            (
                frozenset(
                    (station, tuple(tasks))
                    for station, tasks in self.station_tasks_assignment.items()
                ),
                frozenset(
                    (station, worker)
                    for station, worker in self.station_worker_assignment.items()
                ),
            )
        )

    def __str__(self) -> str:
        """
        Gets a string representation of the solution.

        Returns:
            str: A structured string representing the task allocations per station.
        """

        from oahf.Utils.Util import Util

        result = [Util.line()]
        result.append("ALWABP Solution:")
        result.append(f"ID: {self.id}")
        result.append(f"Number of Tasks: {len(self.tasks)}")
        result.append(f"Number of Workers: {len(self.workers)}")
        result.append(f"Number of Stations: {len(self.stations)}")
        result.append(f"Max Cycle Time: {str(int(self.get_max_cycle_time()))}")
        result.append("Task Allocations (per station):")

        for station in self.stations:
            result.append(f"  Station {station}:")
            worker = self.station_worker_assignment.get(station, None)
            if worker is not None:
                tasks_str = ", ".join(map(str, self.station_tasks_assignment[station]))
                result.append(f"    Worker {worker}: Tasks -> [{tasks_str}]")

        unassigned_tasks = (
            ", ".join(map(str, self.unassigned_tasks))
            if len(self.unassigned_tasks) > 0
            else "[]"
        )
        result.append(f"Unassigned Tasks: {unassigned_tasks}")
        result.append(Util.line())
        return "\n".join(result)

    def to_dict(self) -> dict:
        """
        Converts the solution data into a dictionary format.

        Returns:
            dict: A structured dictionary representing the task allocations per station.
        """

        solution_dict = super().to_dict()

        solution_dict.update(
            {
                "number_of_tasks": len(self.tasks),
                "number_of_workers": len(self.workers),
                "number_of_stations": len(self.stations),
                "max_cycle_time": int(self.get_max_cycle_time()),
                "task_allocations_per_station": [],
                "unassigned_tasks": (
                    self.unassigned_tasks if len(self.unassigned_tasks) > 0 else []
                ),
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
        Reconstructs an ALWABP solution from a dictionary while respecting the problem's precedences
        and rules. Uses an existing solution instance to set up the necessary parameters.

        Args:
            data (dict): A dictionary representing the serialized solution.
            base_solution (AlwabpSolution): An existing ALWABP solution instance that provides
                                            problem-specific parameters such as precedences.

        Returns:
            AlwabpSolution: A reconstructed ALWABP solution instance.
        """
        # Start by creating a copy of the base solution
        solution = base_solution.copy()

        # Ensure the solution's default orientation is set to FORWARD
        solution.default_graph_orientation = GraphOrientation.FORWARD
        solution.reset()  # Reset the solution state before populating it

        # Set the basic properties
        # solution.id = data.get("id", solution.id)
        # solution._cycle_time_limit = data.get("cycle_time_limit", solution._cycle_time_limit)

        # Assign workers and tasks to stations
        for allocation in data.get("task_allocations_per_station", []):
            station = allocation["station"]
            worker = allocation.get("worker")
            tasks = allocation.get("tasks", [])

            # Assign the worker to the station if present
            if worker is not None:
                solution.add_worker_to_station(
                    worker, station, recalculate_cycle_time=False
                )

            # Assign the tasks to the station
            for task in tasks:
                solution.add_task_to_station(task, station)

        # Update unassigned tasks
        unassigned_tasks = data.get("unassigned_tasks", [])
        solution._unassigned_tasks = unassigned_tasks

        # Recalculate cycle times after all assignments
        for station in solution.stations:
            solution.calculate_cycle_time(station, force_calculate=True)

        solution._cycle_time_limit = solution.get_max_cycle_time()

        # Return the reconstructed solution
        return solution

    def calculate_cycle_time(
        self, station: int, force_calculate: bool = False
    ) -> float:
        """
        Calculates the cycle time for a given station.

        Args:
            station (int): The station ID to calculate cycle time for.

        Returns:
            int: The total cycle time for the specified station.
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
            float: The maximum cycle time among all stations.
        """
        return max(self.calculate_cycle_time(station) for station in self.stations)

    def get_min_cycle_time(self) -> float:
        """
        Finds the minimum cycle time across all stations.

        Returns:
            float: The minimum cycle time among all stations.
        """
        return min(self.calculate_cycle_time(station) for station in self.stations)

    def get_idle_time(self) -> float:
        """
        Calculates the idle time,
        which is the difference between the maximum and minimum cycle times across stations.

        Returns:
            float: The idle time (max cycle time - min cycle time).
        """
        return self.get_max_cycle_time() - self.get_min_cycle_time()

    def solution_diff(self, other: "AlwabpSolution") -> float:
        """
        Calculates the difference between this solution and another based on idle time.

        Args:
            other (ALWABP): The other solution to compare against.

        Returns:
            float: The difference in idle time between the two solutions.
        """
        if not isinstance(other, AlwabpSolution):
            raise TypeError("The other solution must be of type ALWABP.")

        idle_time_self = self.get_idle_time()
        idle_time_other = other.get_idle_time()

        return idle_time_self - idle_time_other

    def _update_unassigned_workers(self) -> None:
        """
        Retrieves a list of workers that have not been assigned any tasks.

        Returns:
            List[int]: A list of worker IDs who are currently unassigned.
        """
        unassigned_workers = []
        for worker in self.workers:
            if not self.station_worker_assignment.values():
                unassigned_workers.append(worker)

        self._unassigned_workers = unassigned_workers

    def _update_unassigned_tasks(self) -> None:
        """
        Retrieves a list of tasks that have not been assigned to any worker.

        Returns:
            List[int]: A list of task IDs that are currently unassigned.
        """
        assigned_tasks = set(
            task
            for station_tasks in self.station_tasks_assignment.values()
            for task in station_tasks
        )

        self._unassigned_tasks = [
            task for task in self.tasks if task not in assigned_tasks
        ]

    def add_precedence(
        self,
        task_u: int,
        task_v: int,
        graph_orientation: Optional[GraphOrientation] = None,
    ) -> bool:
        """
        Adds a precedence relation indicating that task_u must be allocated before task_v.

        Args:
            task_u (int): The task that must precede.
            task_v (int): The task that must come after.
            graph_orientation (Optional[GraphOrientation]):
            Optional value to set graph orientation, if not set, both ways will be set.
            The parameters will be set as FORWARD and reversed to set BACKWARD.

        Returns:
            bool: True if the precedence relation was successfully added, False if it already exists.
        """
        task_1: int = task_u
        task_2: int = task_v
        orientations: List[GraphOrientation] = []
        success: bool = False

        if graph_orientation is None:
            orientations = EnumUtil.get_values(GraphOrientation)  # type: ignore
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

                # Add task_2 to the list of tasks that must come after task_1
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
        Calculates all precedences for the given task, including both immediate and transitive precedences.

        This method traverses the precedence graph recursively to find all tasks that must be completed
        before the given task, including indirect precedences.

        Args:
            task (int): The task for which to calculate all precedences.
            graph_orientation (GraphOrientation): The direction of the precedence graph (default is FORWARD).

        Returns:
            List[int]: A list of all tasks that precede the given task, including transitive precedences.
        """
        visited = set()  # Keep track of visited tasks to avoid cycles
        precedences = []

        def dfs(current_task):
            # Recursively explore all tasks that precede the current task
            if current_task in self.immediate_task_precedences[graph_orientation]:
                for preceding_task in self.immediate_task_precedences[
                    graph_orientation
                ][current_task]:
                    if preceding_task not in visited:
                        visited.add(preceding_task)
                        precedences.append(preceding_task)
                        dfs(
                            preceding_task
                        )  # Recursively explore precedences of the preceding task

        # Start DFS from the given task
        dfs(task)

        return sorted(precedences)

    def _fill_all_task_precedences(self) -> None:
        """
        Fills the `all_task_precedences` dictionary with all precedences (both immediate and transitive)
        for every task in both forward and backward graph orientations.
        """
        for graph_orientation in EnumUtil.get_values(GraphOrientation):
            if isinstance(graph_orientation, GraphOrientation):
                for task in self.tasks:
                    # Calculate all precedences for the current task and graph orientation
                    all_precedences = self._calculate_all_precedences(
                        task, graph_orientation
                    )
                    # Fill the dictionary with the result
                    self.all_task_precedences[graph_orientation][task] = all_precedences

        self.order_solution_tasks()

    def __get_tasks_executed_by_worker(self, worker: int) -> Tuple[int, ...]:
        """
        Gets the list of tasks that a specific worker can execute, based on execution times.

        If the worker cannot execute a task (execution time is 'inf'), the task is excluded from the list.

        Args:
            worker (int): The worker ID for which to retrieve tasks.

        Returns:
            List[int]: A list of task IDs that the worker can execute, based on execution times.
        """
        if worker not in self.workers:
            raise ValueError(f"Worker ID {worker} is invalid.")

        tasks_executed = []

        # Iterate through all tasks to check if the worker can execute them
        for task, execution_times in self._task_execution_times.items():
            # Check if the worker has a valid execution time for the task
            if execution_times[worker - 1] != float(
                "inf"
            ):  # worker - 1 for index adjustment
                tasks_executed.append(task)

        return tuple(tasks_executed)

    def order_solution_tasks(self) -> None:
        """
        Orders the tasks for each station in the solution.
        """
        for station in self.stations:
            # Orders the tasks of the current station according to precedence constraints.
            self.order_tasks_according_to_precedence(station)

    def order_tasks_according_to_precedence(self, station: int) -> None:
        """
        Orders the tasks in a specific station according to their precedence relationships.

        This method ensures that tasks assigned to a station respect the precedence
        constraints defined in the task precedence graph. If task A precedes task B
        and both are in the same station, task A will appear before task B in the list.

        Parameters:
            station (int): The index of the station whose task list needs to be ordered.
        """
        # Get the tasks assigned to the station
        tasks = self.station_tasks_assignment[station]

        # Create a dictionary to store task precedence (tasks that must come before each task)
        precedence_map: Dict[int, Set[int]] = {task: set() for task in tasks}

        # Build precedence relationships among tasks
        for task in tasks:
            # Check the precedence constraints for the current task
            for predecessor in self.all_task_precedences[
                self.default_graph_orientation
            ].get(task, []):
                if predecessor in tasks:  # Only consider tasks within the same station
                    precedence_map[task].add(predecessor)

        # Perform a topological sort to order tasks based on precedence
        ordered_tasks = self.topological_sort(precedence_map)

        # Update the station's task list with the ordered tasks
        self.station_tasks_assignment[station] = ordered_tasks

    def topological_sort(self, precedence_map):
        """
        Topological sort implementation to order tasks respecting precedence constraints.

        Parameters:
            precedence_map (dict): A dictionary where keys are tasks and values are sets of tasks
                                    that must come before the key task.

        Returns:
            List of tasks ordered by precedence.
        """
        # Start with tasks that have no precedence (no task before them)
        no_precedence = [
            task for task, precedents in precedence_map.items() if not precedents
        ]
        ordered_tasks = []

        while no_precedence:
            task = no_precedence.pop()
            ordered_tasks.append(task)

            # Remove this task from all tasks that depend on it
            for dependent_task in precedence_map:
                if task in precedence_map[dependent_task]:
                    precedence_map[dependent_task].remove(task)
                    # If this dependent task now has no more precedence, add it to the list
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
        Adds a worker from a specific station, if the worker is not assigned to that station.

        Args:
            worker (int): The worker to be added.
            station (int): The station from which the worker will be added.

        Returns:
            bool: True if the worker was successfully added, False otherwise.
        """
        try:
            if self.station_worker_assignment.get(station) != worker:
                self.station_worker_assignment[station] = worker
                self.worker_station_assignment[worker] = station
                self.unassigned_workers.remove(worker)

                if recalculate_cycle_time:
                    self.calculate_cycle_time(station, True)

                return True
            else:
                LogManager.invalid_action(
                    "add worker to station, it was already assigned to it", self.name
                )
                return False
        except Exception as e:
            LogManager.invalid_action("add worker to station", self.name, e)
            return False

    def remove_worker_from_station(
        self, worker: int, station: int, recalculate_cycle_time: bool = True
    ) -> bool:
        """
        Removes a worker from a specific station by setting the station.

        Args:
            worker (int): The worker to be removed.
            station (int): The station from which the worker will be removed.

        Returns:
            bool: True if the worker was successfully removed, False otherwise.
        """
        try:
            if self.station_worker_assignment.get(station) == worker:
                self.station_worker_assignment[station] = None
                self.worker_station_assignment[worker] = None
                self.unassigned_workers.append(worker)

                if recalculate_cycle_time:
                    self.calculate_cycle_time(station, True)

                return True
            else:
                LogManager.invalid_action(
                    "remove worker from station, it wasn't assigned to it", self.name
                )
                return False
        except Exception as e:
            LogManager.invalid_action("remove worker from station", self.name, e)
            return False

    def add_task_to_station(self, task: int, station: int) -> bool:
        """
        Add a task to a specific station, if not already assigned to it.

        Args:
            task (int): The task to be added.
            station (int): The station from which the task will be added.

        Returns:
            bool: True if the task was successfully added, False otherwise.
        """
        try:
            if task not in self.station_tasks_assignment.get(station, []):
                self.station_tasks_assignment[station].append(task)
                self.task_station_assignment[task] = station
                self._unassigned_tasks.remove(task)

                worker = self.station_worker_assignment[station]
                self.station_cycle_time_memo[station] += self.get_task_execution_time(
                    task, worker
                )

                return True
            else:
                LogManager.invalid_action(
                    "add task to station, it was already assigned to it", self.name
                )
                return False
        except Exception as e:
            LogManager.invalid_action("add task to station", self.name, e)
            return False

    def remove_task_from_station(self, task: int, station: int) -> bool:
        """
        Removes a task from a specific station by removing the task from their assignment.

        Args:
            task (int): The task to be removed.
            station (int): The station from which the task will be removed.

        Returns:
            bool: True if the task was successfully removed, False otherwise.
        """
        try:
            if task in self.station_tasks_assignment.get(station, []):
                self.station_tasks_assignment[station].remove(
                    task
                )  # Remove the task from the station's list
                self.task_station_assignment[task] = None
                self._unassigned_tasks.append(task)

                worker = self.station_worker_assignment[station]
                self.station_cycle_time_memo[station] -= self.get_task_execution_time(
                    task, worker
                )

                return True
            else:
                LogManager.invalid_action(
                    "remove task from station, it wasn't assigned to it", self.name
                )
                return False
        except Exception as e:
            LogManager.invalid_action("remove task from station", self.name, e)
            return False

    def find_station_for_task(self, task: int) -> Optional[int]:
        """
        Finds the station where a specific task is assigned, based on worker assignments.

        Args:
            task (int): The task ID to find the station for.

        Returns:
            Optional[int]: The station ID where the task is assigned,
            or None if the task is not assigned to any station.
        """
        return self.task_station_assignment[task]

    def find_station_for_worker(self, worker: int) -> Optional[int]:
        """
        Finds the station where a specific worker is allocated.

        Args:
            worker (int): The ID of the worker whose station is to be found.

        Returns:
            Optional[int]: The station ID where the worker is allocated,
            or None if the worker is not allocated to any station.
        """
        return self.worker_station_assignment[worker]

    def get_available_tasks_to_assign_to_worker(self, worker: int) -> List[int]:
        station = self.find_station_for_worker(worker)
        return self.get_available_tasks_to_assign_to_station(station) if station else []

    def get_available_tasks_to_assign_to_station(
        self,
        station: int,
        override_unassigned_tasks: List[int] = [],
    ) -> List[int]:
        """
        Finds the available tasks that can be assigned to the given station, considering task precedences.

        Args:
            station (int): The upper station ID to which precence tasks are could have been assigned.
            graph_orientation (GraphOrientation): represent the state of the precedence graph.
            override_unassigned_tasks (List[int]): list of unassigned tasks to be used for simulations.

        Returns:
            List[int]: A list of available tasks that can be assigned to the specified station.
        """
        available_tasks_to_assign: List[int] = []
        unassigned_tasks = set(
            override_unassigned_tasks
            if override_unassigned_tasks
            else self._unassigned_tasks
        )

        for unassigned_task in unassigned_tasks:
            task_precendes = self.all_task_precedences[self.default_graph_orientation][
                unassigned_task
            ]
            can_allocate = True
            for preceding_task in task_precendes:
                if preceding_task in unassigned_tasks or (
                    (another_station := self.find_station_for_task(preceding_task))
                    and another_station > station
                ):
                    can_allocate = False
                    break
            if can_allocate:
                available_tasks_to_assign.append(unassigned_task)

        return available_tasks_to_assign

    def can_task_be_assigned_to(
        self, task: int, station: int, worker: Optional[int] = None
    ) -> bool:
        worker = worker or self.station_worker_assignment[station]

        if worker and task not in self.tasks_executed_by_worker[worker]:
            return False

        if (
            worker
            and self.cycle_time_limit
            and (
                (
                    self.station_cycle_time_memo[station]
                    + self.get_task_execution_time(task, worker)
                )
                > self.cycle_time_limit
            )
        ):
            return False

        for preceding_task in self.all_task_precedences[self.default_graph_orientation][
            task
        ]:
            another_station = self.find_station_for_task(preceding_task)
            if not another_station or another_station > station:
                return False

        for sucessor_task in self.all_task_precedences[
            GraphOrientation.reverse(self.default_graph_orientation)
        ][task]:
            another_station = self.find_station_for_task(sucessor_task)
            if another_station and another_station < station:
                return False

        return True

    def get_task_execution_time(self, task: int, worker: Optional[int] = None) -> float:
        if worker and task in self.tasks_executed_by_worker[worker]:
            return self._task_execution_times[task][worker - 1]
        else:
            return max(self._bounded_task_execution_times[task])

    def max_task_execution_time(
        self, task: int, workers: Optional[List[int]] = None
    ) -> float:
        """
        Calculates the maximum execution time for a task, considering only the workers specified.

        Args:
            task (int): The task ID for which to calculate the maximum task execution time.
            workers (Optional[List[int]]): A list of worker indices to consider.
            If None, consider all workers.

        Returns:
            float: The maximum task execution time among the specified workers.
        """
        task_times = self._bounded_task_execution_times[task]

        if workers:
            # Consider only task times for the specified workers' indices
            task_times = [task_times[worker - 1] for worker in sorted(workers)]

        return max(task_times)

    def min_task_execution_time(
        self, task: int, workers: Optional[List[int]] = None
    ) -> float:
        """
        Calculates the minimum execution time for a task, considering only the workers specified.

        Args:
            task (int): The task ID for which to calculate the minimum task execution time.
            workers (Optional[List[int]]): A list of worker indices to consider.
            If None, consider all workers.

        Returns:
            float: The minimum task execution time among the specified workers.
        """
        task_times = self._bounded_task_execution_times[task]

        if workers:
            # Consider only task times for the specified workers' indices
            task_times = [task_times[worker - 1] for worker in sorted(workers)]

        return min(task_times)

    def average_task_execution_time(
        self, task: int, workers: Optional[List[int]] = None
    ) -> float:
        """
        Calculates the average execution time for a task, considering only the workers specified.

        Args:
            task (int): The task ID for which to calculate the average task execution time.
            workers (Optional[List[int]]): A list of worker indices to consider.
            If None, consider all workers.

        Returns:
            float: The average task execution time among the specified workers.
        """
        task_times = self._bounded_task_execution_times[task]

        if workers:
            # Consider only task times for the specified workers' indices
            task_times = [task_times[worker - 1] for worker in sorted(workers)]

        number_of_workers = max(1, len(task_times))
        return sum(task_times) / number_of_workers

    def __get_func_for_max_positional_weight(
        self, positional_weight_type: MaxPositionalWeightType
    ) -> Callable[[int], float]:
        """
        Retrieve the appropriate function for calculating the maximum positional weight
        based on the specified type.

        Args:
            positional_weight_type (MaxPositionalWeightType):
            The type of positional weight to determine the appropriate function.

        Returns:
            Callable[[int], float]: A function that takes an integer (task) as input and
            returns a float representing the corresponding positional weight.
        """
        if positional_weight_type == MaxPositionalWeightType.MAX:
            return self.max_task_execution_time
        elif positional_weight_type == MaxPositionalWeightType.MIN:
            return self.min_task_execution_time
        else:
            return self.average_task_execution_time

    def _calculate_max_positional_weights(self) -> None:
        """
        Calculate and store the maximum positional weights for each task based on
        the different types of positional weights (MAX, MIN, AVERAGE).

        This method iterates over all tasks and retrieves the appropriate function
        for calculating positional weights. It then applies this function to each task
        and stores the result in the `max_positional_weight` attribute.

        Returns:
            None: This method does not return a value but modifies the state of the
            object by updating the `max_positional_weight` attribute.
        """
        for task in self.tasks:
            for positional_weight_type in EnumUtil.get_values(MaxPositionalWeightType):
                # Check if positional_weight_type is of the right type
                if isinstance(positional_weight_type, MaxPositionalWeightType):
                    # Get the function for the current positional weight type
                    weight_function = self.__get_func_for_max_positional_weight(
                        positional_weight_type
                    )
                    # Call the returned function with `task` as the argument
                    self.max_positional_weight[positional_weight_type][task] = (
                        weight_function(task)
                    )

    def get_max_positional_weight_value(
        self, task: int, variation: MaxPositionalWeightType
    ) -> float:
        """
        Retrieve the maximum positional weight for a given task and variation.

        Args:
            task (int): The identifier of the task for which the positional weight is to be retrieved.
            variation (MaxPositionalWeightType): The type of positional weight variation
            (e.g., MAX, MIN, AVERAGE) to be used in the lookup.

        Returns:
            float: The maximum positional weight associated with the specified task and variation.
            Returns -1 if no positional weight is correctly found or set for the given task
            and variation.
        """
        # Attempt to retrieve the positional weight from the max_positional_weight dictionary.
        # If the weight is not set, it is assumed to be -1 (indicating an error or absence of value).
        return self.max_positional_weight[variation][task]

    def get_max_positional_weight_dict(
        self, variation: MaxPositionalWeightType
    ) -> Dict[int, float]:
        """
        Retrieve the maximum positional weight for a given variation.

        Args:
            variation (MaxPositionalWeightType): The type of positional weight variation
            (e.g., MAX, MIN, AVERAGE) to be used in the lookup.

        Returns:
            List[float]: The list of maximum positional weights associated with the specified variation.
        """
        # Attempt to retrieve the positional weight from the max_positional_weight dictionary.
        # If the weight is not set, it is assumed to be -1 (indicating an error or absence of value).
        return self.max_positional_weight[variation]

    def get_min_restricted_lower_bound(self) -> List[int]:
        """
        Orders the list of unassigned workers based on their minimum restricted lower bound (RLB).
        This function returns a new list and does not modify the original unassigned_workers list.

        Returns:
            List[int]: A new list of unassigned worker IDs sorted by their minimum RLB.
        """
        return sorted(
            self.unassigned_workers, key=lambda worker: self.get_worker_min_rlb(worker)
        )

    def get_worker_min_rlb(
        self, worker: int, override_unassigned_tasks: List[int] = []
    ) -> int:
        """
        Calculates the minimum restricted lower bound (RLB) for a worker. This RLB is the total minimum
        execution time of all tasks that the worker could be assigned, divided among other unassigned workers.

        Args:
            worker (int): The worker ID for whom to calculate the minimum RLB.
            override_unassigned_tasks (List[int]): list of unassigned tasks to be used for simulations.

        Returns:
            int: The minimum restricted lower bound for the worker.
        """

        unassigned_tasks = (
            override_unassigned_tasks.copy()
            if len(override_unassigned_tasks) > 0
            else self._unassigned_tasks
        )
        # If there's only one unassigned worker, return 0 as there's no other worker to assign tasks to
        if len(self.unassigned_workers) == 1:
            return 0

        # Get the tasks that the worker can still be assigned (i.e., tasks that are unassigned)
        pending_assignable_tasks = [
            task
            for task in self.tasks_executed_by_worker[worker]
            if task in unassigned_tasks
        ]

        # Copy the unassigned workers list and remove the current worker from it

        unassigned_workers = self.unassigned_workers.copy()
        unassigned_workers.remove(worker)

        amount_of_time: int = 0

        # For each task that can be assigned to the worker, add the minimum task execution time
        # for that task considering the other unassigned workers
        for task in pending_assignable_tasks:
            amount_of_time += int(
                self.min_task_execution_time(task, unassigned_workers)
            )

        # Return the total amount of time divided by the number of remaining unassigned workers
        return amount_of_time // (len(unassigned_workers) or 1)

    def get_first_unassigned_station(self) -> Optional[int]:
        """
        Returns the first station key where no task is assigned.

        Returns:
            Optional[int]: The station key where no task is assigned (None)
            or None if all are assigned.
        """
        for station, tasks in self.station_tasks_assignment.items():
            if len(tasks) == 0:
                return station
        return None  # Return None if no unassigned station is found

    def station_would_be_feasible(self, station: int, worker: int) -> bool:
        """
        Checks if a worker can feasibly execute all tasks assigned to a given station.

        The function first verifies if the worker can execute all the tasks assigned to the specified station.
        If a cycle time limit is set, it also checks if the total execution time of the tasks
        falls within the cycle time limit.

        Parameters:
        station (int): The index of the station being checked.
        worker (int): The index of the worker being evaluated.

        Returns:
        bool: True if the worker can execute all tasks and the total execution time is within the cycle time limit (if set),
              False otherwise.
        """
        tasks = self.station_tasks_assignment[station]
        executable_tasks = self.tasks_executed_by_worker[worker]

        for task in tasks:
            if task not in executable_tasks:
                return False

        if self.cycle_time_limit is not None:
            total_execution_time = sum(
                self.get_task_execution_time(task, worker) for task in tasks
            )
            if total_execution_time > self.cycle_time_limit:
                return False

        return True

    def simulate_worker_tasks_allocation(
        self, worker: int, movements: List[AlwabpInsertionMovement]
    ) -> List[AlwabpInsertionMovement]:
        """
        Simulates the allocation of tasks to a given worker based on possible movements. It filters the list of movements
        to determine which tasks can be executed by the worker and further checks the cumulative task execution time
        against the cycle time limit.

        The method does not modify the solution itself but returns a list of possible movements that can be performed
        by the worker without exceeding the cycle time limit.

        Parameters:
        - worker (int): The worker identifier to simulate task allocation for.
        - movements (List[AlwabpInsertOrderMove]): A list of possible movements (task allocations) to simulate.

        Returns:
        - List[AlwabpInsertOrderMove]: A list of movements (tasks) that the worker can execute within the cycle time limit.
        """
        # Filter moves by tasks executable by the worker
        available_moves = [
            move
            for move in movements
            if move.task in self.tasks_executed_by_worker[worker]
        ]

        # available_moves = [move for move in available_moves if self.can_task_be_assigned_to(move.task, move.station, worker)] # type: ignore

        if self.cycle_time_limit:
            selected_moves = []
            total_time = 0.0

            # Check available moves and ensure cumulative task time stays within the cycle time limit
            for move in available_moves:
                if move.task:
                    task_time = self.get_task_execution_time(move.task, worker)

                    # Add task if it does not exceed the cycle time limit
                    if total_time + task_time <= self.cycle_time_limit:
                        selected_moves.append(move)
                        total_time += task_time

                    # Stop if the total time reaches exactly the cycle time limit
                    if total_time == self.cycle_time_limit:
                        break

            return selected_moves
        else:
            # If no cycle time limit is set, return all available moves
            return available_moves

    def get_critical_workstations(self) -> List[int]:
        """
        Identifies and returns the list of critical workstations.

        A critical workstation is one where the cycle time equals the maximum cycle time.

        Returns:
            List[int]: A list of station IDs that are critical workstations.
        """
        # Compute the maximum cycle time once
        max_cycle_time = self.get_max_cycle_time()

        critical_stations = []

        for station in self.stations:
            # Calculate the cycle time for the station
            cycle_time = self.calculate_cycle_time(station)

            # Check if the station is critical
            if cycle_time == max_cycle_time:
                critical_stations.append(station)

        if len(critical_stations) == len(self.stations):
            return []

        return critical_stations

    def get_number_of_critical_workstations(self) -> int:
        """
        Calculates the number of critical workstations.

        A critical workstation is defined as a station where the cycle time equals the cycle time limit.
        This method uses `get_critical_workstations` to identify all critical workstations and
        returns the total count.

        Returns:
            int: The number of critical workstations.
        """
        return len(self.get_critical_workstations())

    @staticmethod
    def get_related_tasks_from_movement(movement: Movement) -> set[int]:
        from oahf.Base.MultipleMovement import MultipleMovement
        from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
        from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement

        related_tasks: List[int] = []
        if isinstance(movement, MultipleMovement):
            [
                related_tasks.extend(AlwabpSolution.get_related_tasks_from_movement(m))
                for m in movement.movements
            ]
        elif (
            isinstance(movement, AlwabpInsertionMovement)
            or isinstance(movement, AlwabpRemovalMovement)
        ) and movement.task:
            related_tasks.append(movement.task)

        return set(related_tasks)

    @classmethod
    def update_task_station_frequencies(
        cls,
        solution: "AlwabpSolution",
        task_station_frequency: Dict[int, Dict[int, int]],
    ) -> None:
        """
        Updates a global frequency dictionary to count how many times each task
        has been allocated to specific stations across multiple solutions.

        Args:
            solution (AlwabpSolution): The ALWABP solution to process.
            task_station_frequency (Dict[int, Dict[int, int]]): A nested dictionary where:
                - Key is the task ID.
                - Value is another dictionary where:
                    - Key is the station ID.
                    - Value is the count of times the task has been allocated to that station.
        """
        # Iterate over all stations and their tasks in the solution
        for station, tasks in solution.station_tasks_assignment.items():
            for task in tasks:
                # Ensure the task exists in the task_station_frequency dictionary
                if task not in task_station_frequency:
                    task_station_frequency[task] = {}

                # Increment the count for the station where the task is allocated
                if station not in task_station_frequency[task]:
                    task_station_frequency[task][station] = 0
                task_station_frequency[task][station] += 1

    @classmethod
    def update_worker_station_frequencies(
        cls,
        solution: "AlwabpSolution",
        worker_station_frequency: Dict[int, Dict[int, int]],
    ) -> None:
        """
        Updates a global frequency dictionary to count how many times each worker
        has been allocated to specific stations across multiple solutions.

        Args:
            solution (AlwabpSolution): The ALWABP solution to process.
            worker_station_frequency (Dict[int, Dict[int, int]]): A nested dictionary where:
                - Key is the worker ID.
                - Value is another dictionary where:
                    - Key is the station ID.
                    - Value is the count of times the worker has been assigned to that station.
        """
        # Iterate over all stations and their assigned workers
        for station, worker in solution.station_worker_assignment.items():
            if worker is not None:
                # Ensure the worker exists in the worker_station_frequency dictionary
                if worker not in worker_station_frequency:
                    worker_station_frequency[worker] = {}

                # Increment the count for the station where the worker is assigned
                if station not in worker_station_frequency[worker]:
                    worker_station_frequency[worker][station] = 0
                worker_station_frequency[worker][station] += 1

    @classmethod
    def get_station_with_highest_frequency(
        cls, frequency_data: Dict[int, Dict[int, int]], entity: int
    ) -> Optional[int]:
        """
        Finds the station where a given task or worker appeared most frequently.
        In case of ties, prioritizes the station with the smallest index.

        Args:
            frequency_data (Dict[int, Dict[int, int]]): Frequency dictionary where:
                - Key: Task or Worker ID.
                - Value: Another dictionary with:
                    - Key: Station ID.
                    - Value: Count of times the entity (task/worker) appeared in the station.
            entity (int): The task or worker ID to check.

        Returns:
            Optional[int]: The station ID where the entity appeared most frequently.
                           Returns None if the entity was not found in the frequency data.
        """
        if entity not in frequency_data:
            return None

        # Get the frequency data for the given entity
        station_frequencies = frequency_data[entity]

        # Find the station with the highest frequency, breaking ties by station ID (ascending)
        max_station = min(station_frequencies.items(), key=lambda x: (-x[1], x[0]))

        return max_station[0]

    @classmethod
    def get_station_with_lowest_frequency(
        cls, frequency_data: Dict[int, Dict[int, int]], entity: int
    ) -> Optional[int]:
        """
        Finds the station where a given task or worker appeared least frequently.
        In case of ties, prioritizes the station with the smallest index.

        Args:
            frequency_data (Dict[int, Dict[int, int]]): Frequency dictionary where:
                - Key: Task or Worker ID.
                - Value: Another dictionary with:
                    - Key: Station ID.
                    - Value: Count of times the entity (task/worker) appeared in the station.
            entity (int): The task or worker ID to check.

        Returns:
            Optional[int]: The station ID where the entity appeared least frequently.
                           Returns None if the entity was not found in the frequency data.
        """
        if entity not in frequency_data:
            return None

        # Get the frequency data for the given entity
        station_frequencies = frequency_data[entity]

        # Find the station with the lowest frequency, breaking ties by station ID (ascending)
        min_station = min(station_frequencies.items(), key=lambda x: (x[1], x[0]))

        return min_station[0]

    @classmethod
    def get_station_with_highest_frequency_to_task(cls, task: int) -> Optional[int]:
        """
        Finds the station where a given task appeared most frequently,
        prioritizing the station with the smallest index in case of ties.

        Args:
            task (int): The task ID to check.

        Returns:
            Optional[int]: The station ID where the task appeared most frequently,
                           or None if the task was not found.
        """
        return cls.get_station_with_highest_frequency(cls._task_station_frequency, task)

    @classmethod
    def get_station_with_lowest_frequency_to_task(cls, task: int) -> Optional[int]:
        """
        Finds the station where a given task appeared least frequently,
        prioritizing the station with the smallest index in case of ties.

        Args:
            task (int): The task ID to check.

        Returns:
            Optional[int]: The station ID where the task appeared least frequently,
                           or None if the task was not found.
        """
        return cls.get_station_with_lowest_frequency(cls._task_station_frequency, task)

    @classmethod
    def get_station_with_highest_frequency_to_worker(cls, worker: int) -> Optional[int]:
        """
        Finds the station where a given worker appeared most frequently,
        prioritizing the station with the smallest index in case of ties.

        Args:
            worker (int): The worker ID to check.

        Returns:
            Optional[int]: The station ID where the worker appeared most frequently,
                           or None if the worker was not found.
        """
        return cls.get_station_with_highest_frequency(
            cls._worker_station_frequency, worker
        )

    @classmethod
    def get_station_with_lowest_frequency_to_worker(cls, worker: int) -> Optional[int]:
        """
        Finds the station where a given worker appeared least frequently,
        prioritizing the station with the smallest index in case of ties.

        Args:
            worker (int): The worker ID to check.

        Returns:
            Optional[int]: The station ID where the worker appeared least frequently,
                           or None if the worker was not found.
        """
        return cls.get_station_with_lowest_frequency(
            cls._worker_station_frequency, worker
        )

    @classmethod
    def update_intensification_diversification_structures(
        cls, solution: "AlwabpSolution"
    ) -> None:
        cls.update_task_station_frequencies(solution, cls._task_station_frequency)
        cls.update_worker_station_frequencies(solution, cls._worker_station_frequency)

    @classmethod
    def reset_intensification_diversification_structures(cls) -> None:
        cls._task_station_frequency = {}
        cls._worker_station_frequency = {}
