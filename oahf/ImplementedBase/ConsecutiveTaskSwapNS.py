from typing import Iterator, Optional

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation
from oahf.ImplementedBase.TaskSwapNS import TaskSwapNS
from oahf.Logger.LogManager import LogManager
from oahf.Utils.PairStore import PairStore


class ConsecutiveTaskSwapNS(Neighborhood):
    """
    ConsecutiveTaskSwapNS implements a multi-step neighborhood search strategy for ALWABP solutions.

    This class extends the concept of task swapping by performing two consecutive swaps
    in the solution space. It explores a broader neighborhood by allowing the results
    of one swap to influence the feasibility and evaluation of subsequent swaps.
    """

    def __init__(
        self,
        graph_orientation: GraphOrientation,
        stop_criteria: Optional[StopCriteria] = None,
    ):
        """
        Initializes the neighborhood search for consecutive task swapping.

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

        solution.default_graph_orientation = self.graph_orientation

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
        Generates all possible sequences of two consecutive task swaps.

        This method uses nested neighborhoods to explore combinations of two task swaps
        while avoiding redundant or cyclic swaps.

        Yields:
            Movement: A composed movement representing two consecutive swaps.
        """
        # Tracks processed task pairs from the first neighborhood to avoid redundancy.
        first_pairs_already_created = PairStore()

        if self.solution:
            # Create a copy of the solution for manipulation during neighborhood exploration.
            solution_copy = self.solution.copy()

            # Initialize the first neighborhood (TaskSwapNS) for the first swap.
            swap_neighborhood_1 = TaskSwapNS(self.graph_orientation)
            if swap_neighborhood_1.build_neighborhood(self.thread_id, solution_copy):
                while swap_move_1 := swap_neighborhood_1.get_move_operation():

                    # Extract and track the task pair affected by the first movement.
                    first_pair = AlwabpSolution.get_related_tasks_from_movement(
                        swap_move_1
                    )
                    if first_pairs_already_created.has_pair(*first_pair):
                        continue  # Skip if the task pair has already been processed.

                    first_pairs_already_created.add_pair(*first_pair)

                    if (
                        swap_move_1.apply()
                    ):  # Apply the first movement to explore further.

                        # Tracks processed task pairs from the second neighborhood to avoid redundancy.
                        second_pairs_already_created = PairStore()

                        # Initialize the second neighborhood (TaskSwapNS) for the next swap.
                        swap_neighborhood_2 = TaskSwapNS(self.graph_orientation)
                        swap_neighborhood_2.build_neighborhood(
                            self.thread_id, solution_copy
                        )

                        while swap_move_2 := swap_neighborhood_2.get_move_operation():

                            # Extract the task pair affected by the second movement.
                            second_pair = (
                                AlwabpSolution.get_related_tasks_from_movement(
                                    swap_move_2
                                )
                            )

                            if (
                                second_pair == first_pair
                                or second_pairs_already_created.has_pair(*second_pair)
                            ):
                                continue  # Skip if the same task pair is being swapped again.

                            second_pairs_already_created.add_pair(*second_pair)

                            if (
                                swap_move_2.apply()
                            ):  # Apply the second movement to evaluate the combined result.

                                # Combine the first and second movements into a single operation.
                                swap_composition = [
                                    swap_move_1.copy(self.solution),
                                    swap_move_2.copy(self.solution),
                                ]
                                move = MultipleMovement(self.solution, swap_composition)

                                yield move  # Return the composed movement for evaluation.

                            # Undo the second movement after processing.
                            swap_move_2.unapply()
                    # Undo the first movement after processing its combinations.
                    swap_move_1.unapply()
        else:
            # Log an invalid action if the solution is not properly initialized.
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "ConsecutiveTaskSwapNS":
        """
        Creates a copy of the ConsecutiveTaskSwapNS instance with the same settings.

        Returns:
            ConsecutiveTaskSwapNS: A new instance with identical parameters.
        """
        return ConsecutiveTaskSwapNS(
            self.graph_orientation,
            self.stop_criteria.copy() if self.stop_criteria else None,
        )
