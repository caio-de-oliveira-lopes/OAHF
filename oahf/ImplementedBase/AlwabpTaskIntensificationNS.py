from typing import Iterator, Optional

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.Logger.LogManager import LogManager


class AlwabpTaskIntensificationNS(Neighborhood):
    """
    Represents a specialized neighborhood structure for the ALWABP (Assembly Line Worker Assignment
    and Balancing Problem) that focuses on task intensification. This class generates movements
    to iteratively refine solutions by removing and reassigning tasks within the assembly line.

    Attributes:
        enumerator (Optional[Iterator[Movement]]): Iterator over the available movements in the neighborhood.
        solution (Optional[AlwabpSolution]): The current solution being explored.
        thread_id (int): Identifier for parallel execution threads.
        cost_function: Optional cost function for movement evaluation.
    """

    def __init__(self, stop_criteria: Optional[StopCriteria] = None):
        """
        Initializes the neighborhood with optional stopping criteria.

        Args:
            stop_criteria (Optional[StopCriteria]): Criteria to determine when to stop exploration.
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
        Generates all possible movements for the current solution by creating a sequence of
        task removals followed by task reassignments. This intensifies the search process
        by focusing on refining task allocations.

        Yields:
            Movement: A combined movement representing cleaning and reassignment actions.
        """
        if self.solution:
            solution_copy = self.solution  # The solution to be explored.
            cleaning_moves = []

            # Generate task removal movements for all stations.
            for station in solution_copy.stations:
                for task in solution_copy.station_tasks_assignment[station]:
                    cleaning_moves.append(
                        AlwabpRemovalMovement(
                            task, None, station, solution_copy, self.report
                        )
                    )

            cleaning_move = MultipleMovement(solution_copy, self.report, cleaning_moves)

            assign_moves = []
            # Generate task reassignment movements based on task frequency.
            for task in solution_copy.tasks:
                station = AlwabpSolution.get_station_with_highest_frequency_to_task(
                    task
                )
                if station:
                    assign_moves.append(
                        AlwabpInsertionMovement(
                            task, None, station, solution_copy, self.report
                        )
                    )

            assign_move = MultipleMovement(solution_copy, self.report, assign_moves)

            # Combine removal and reassignment movements into a single move.
            move = MultipleMovement(
                solution_copy, self.report, [cleaning_move, assign_move]
            )

            yield move
        else:
            # Log an invalid action if the solution is not properly initialized.
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "AlwabpTaskIntensificationNS":
        """
        Creates a copy of the AlwabpTaskIntensificationNS instance with the same settings.

        Returns:
            AlwabpTaskIntensificationNS: A new instance with identical parameters.
        """
        return AlwabpTaskIntensificationNS(
            self.stop_criteria.copy() if self.stop_criteria else None,
        )
