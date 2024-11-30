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

        The function explores potential task swaps between pairs of workstations.
        Instead of creating a fresh copy of the solution for every new movement,
        it applies and unapplies movements directly to a single copy. This approach
        minimizes memory overhead by avoiding excessive use of `.copy()`.

        Key changes:
        - A single `solution_copy` is created at the start of the outer loop for a given
          pair of workstations (`ws1` and `ws2`).
        - Movements (`reinsertion_test_1` and `reinsertion_test_2`) are unapplied after
          being tested. This reverts the solution to its prior state, making it reusable.
        - This strategy ensures memory efficiency while still exploring the full
          neighborhood of task swaps.
        """
        pairs_already_created = PairStore()  # Tracks processed workstation pairs.
        if self.solution:
            for ws1 in self.solution.stations:
                tasks_on_ws1 = list(self.solution.station_tasks_assignment[ws1])

                # Avoid redundant swaps by skipping already processed station pairs.
                other_stations = [
                    s
                    for s in self.solution.stations
                    if s != ws1 and not pairs_already_created.has_pair(ws1, s)
                ]

                for ws2 in other_stations:
                    pairs_already_created.add_pair(ws1, ws2)
                    tasks_on_ws2 = list(self.solution.station_tasks_assignment[ws2])

                    # Create a single reusable copy of the solution for this pair.
                    solution_copy = self.solution.copy()

                    for task_ws1 in tasks_on_ws1:
                        # Removal and insertion movement for the first task swap.
                        test_move_1 = AlwabpRemovalMovement(
                            task_ws1, None, ws1, solution_copy, self.report
                        )
                        test_move_2 = AlwabpInsertionMovement(
                            task_ws1, None, ws2, solution_copy, self.report
                        )

                        # Combine the two movements into a single operation.
                        reinsertion_test_1 = MultipleMovement(
                            solution_copy, self.report, [test_move_1, test_move_2]
                        )

                        # Apply the movement to modify `solution_copy`.
                        if reinsertion_test_1.apply():
                            for task_ws2 in tasks_on_ws2:
                                # Removal and insertion movement for the second task swap.
                                test_move_3 = AlwabpRemovalMovement(
                                    task_ws2, None, ws2, solution_copy, self.report
                                )
                                test_move_4 = AlwabpInsertionMovement(
                                    task_ws2, None, ws1, solution_copy, self.report
                                )

                                # Combine the movements for the reverse swap.
                                reinsertion_test_2 = MultipleMovement(
                                    solution_copy,
                                    self.report,
                                    [test_move_3, test_move_4],
                                )

                                # Apply the second movement and check feasibility.
                                if (
                                    reinsertion_test_2.apply()
                                    and solution_copy.can_task_be_assigned_to(
                                        task_ws1, ws2, None, self.graph_orientation
                                    )
                                    and solution_copy.can_task_be_assigned_to(
                                        task_ws2, ws1, None, self.graph_orientation
                                    )
                                ):
                                    # Movements are copied to operate on the original solution.
                                    reinsertion_move_1 = reinsertion_test_1.copy(
                                        self.solution
                                    )
                                    reinsertion_move_2 = reinsertion_test_2.copy(
                                        self.solution
                                    )

                                    # Combine into a complete swap movement.
                                    swap_composition = [
                                        reinsertion_move_1,
                                        reinsertion_move_2,
                                    ]

                                    # Yield the movement for external use.
                                    move = MultipleMovement(
                                        self.solution, self.report, swap_composition
                                    )
                                    yield move

                                # Revert the second movement to restore the solution state.
                                reinsertion_test_2.unapply()

                        # Revert the first movement to prepare for the next iteration.
                        reinsertion_test_1.unapply()
        else:
            # Log an invalid action if the solution is not properly initialized.
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
