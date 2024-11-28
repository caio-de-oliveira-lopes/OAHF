from typing import Iterator, Optional

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation
from oahf.Logger.LogManager import LogManager
from oahf.Utils.PairStore import PairStore


class TaskSwapNS(Neighborhood):
    """
    TaskSwapNS implements a neighborhood search for task swapping in ALWABP solutions.

    This class focuses on swapping tasks between workstations to explore the solution space
    and improve the overall assignment. Each task swap involves removing a task from one
    station and inserting it into another, while maintaining feasibility regarding task
    dependencies and station constraints.
    """

    def __init__(
        self,
        graph_orientation: GraphOrientation,
        stop_criteria: Optional[StopCriteria] = None,
    ):
        """
        Initializes the neighborhood search for task swapping.

        Args:
            graph_orientation (GraphOrientation): Defines the dependency relationships between tasks.
            stop_criteria (Optional[StopCriteria]): Optional criteria to terminate the neighborhood search.
        """
        super().__init__(stop_criteria, False)
        self.enumerator: Optional[Iterator[Movement]] = (
            None  # Stores the current movement iterator.
        )
        self.solution: Optional[AlwabpSolution] = (
            None  # Holds the current solution being explored.
        )
        self.thread_id: int = 0  # Thread identifier for parallel execution.
        self.cost_function = None  # Optional cost function for evaluating movements.
        self.graph_orientation = graph_orientation  # Dependency orientation (e.g., precedence relationships).

    def build_neighborhood(self, thread_id: int, solution: AlwabpSolution) -> bool:
        """
        Prepares the neighborhood by initializing the solution and movement iterator.

        Args:
            thread_id (int): Identifier for the current execution thread.
            solution (AlwabpSolution): The solution to build the neighborhood for.

        Returns:
            bool: Always returns True, indicating successful initialization.
        """
        self.solution = solution
        self.thread_id = thread_id
        self.enumerator = self.all_moves()
        return True

    def get_move(self) -> Optional[Movement]:
        """
        Retrieves the next available movement in the neighborhood.

        Returns:
            Optional[Movement]: The next movement, or None if all movements are exhausted.
        """
        if not self.enumerator:
            return None
        try:
            return next(self.enumerator)
        except StopIteration:
            return None

    def all_moves(self) -> Iterator[Movement]:
        """
        Generates all possible task swaps between workstations in the solution.

        Yields:
            Movement: A composed movement representing a task swap.
        """
        pairs_already_created = (
            PairStore()
        )  # Tracks processed workstation pairs to avoid redundant swaps.
        if self.solution:
            for ws1 in self.solution.stations:
                tasks_on_ws1 = self.solution.station_tasks_assignment[ws1]

                # Filter stations to exclude ws1 and ensure unique pairs are processed.
                other_stations = [
                    s
                    for s in self.solution.stations
                    if s != ws1 and not pairs_already_created.has_pair(ws1, s)
                ]

                for ws2 in other_stations:
                    pairs_already_created.add_pair(ws1, ws2)
                    tasks_on_ws2 = self.solution.station_tasks_assignment[ws2]

                    # Identify tasks that can be swapped between ws1 and ws2.
                    available_tasks_from_ws1_to_ws2 = (
                        self.solution.get_available_tasks_to_assign_to_station(
                            ws2, self.graph_orientation, tasks_on_ws1
                        )
                    )
                    available_tasks_from_ws2_to_ws1 = (
                        self.solution.get_available_tasks_to_assign_to_station(
                            ws1, self.graph_orientation, tasks_on_ws2
                        )
                    )

                    # Generate all possible swaps between available tasks.
                    for task_ws1 in available_tasks_from_ws1_to_ws2:
                        for task_ws2 in available_tasks_from_ws2_to_ws1:
                            # Define removal and insertion movements for the swap.
                            removal_move_1 = AlwabpRemovalMovement(
                                task_ws1, None, ws1, self.solution, self.report
                            )
                            removal_move_2 = AlwabpRemovalMovement(
                                task_ws2, None, ws2, self.solution, self.report
                            )
                            insertion_move_1 = AlwabpInsertionMovement(
                                task_ws1, None, ws2, self.solution, self.report
                            )
                            insertion_move_2 = AlwabpInsertionMovement(
                                task_ws2, None, ws1, self.solution, self.report
                            )

                            # Combine the movements into a single swap operation.
                            swap_composition = [
                                removal_move_1,
                                removal_move_2,
                                insertion_move_1,
                                insertion_move_2,
                            ]

                            move = MultipleMovement(
                                self.solution, self.report, swap_composition
                            )

                            yield move  # Return the composed movement.
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "TaskSwapNS":
        """
        Creates a copy of the TaskSwapNS instance with the same settings.

        Returns:
            TaskSwapNS: A new instance with identical parameters.
        """
        return TaskSwapNS(
            self.graph_orientation,
            self.stop_criteria.copy() if self.stop_criteria else None,
        )
