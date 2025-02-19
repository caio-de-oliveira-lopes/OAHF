from typing import Iterator, Optional

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.Logger.LogManager import LogManager
from oahf.Utils.PairStore import PairStore


class WorkerSwapNS(Neighborhood):
    """
    WorkerSwapNS implements a neighborhood search for swapping workers between stations in ALWABP solutions.

    This class generates movements that swap workers assigned to different stations while ensuring feasibility
    of the solution. Each swap consists of removing workers from their respective stations and reassigning them
    to the opposite stations.
    """

    def __init__(self):
        """
        Initializes the neighborhood search for worker swapping.
        """
        super().__init__(False)
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
        Generates all possible worker swaps between workstations in the solution.

        Yields:
            Movement: A composed movement representing a worker swap.
        """
        pairs_already_created = (
            PairStore()
        )  # Tracks processed workstation pairs to avoid redundant swaps.
        if self.solution:
            for ws1 in self.solution.stations:
                # Filter stations to exclude ws1 and ensure unique pairs are processed.
                other_stations = [
                    s
                    for s in self.solution.stations
                    if s != ws1 and not pairs_already_created.has_pair(ws1, s)
                ]

                for ws2 in other_stations:
                    pairs_already_created.add_pair(ws1, ws2)

                    # Define removal and insertion movements for the swap.
                    removal_move_1 = AlwabpRemovalMovement(
                        None,
                        self.solution.station_worker_assignment[ws1],
                        ws1,
                        self.solution,
                    )
                    removal_move_2 = AlwabpRemovalMovement(
                        None,
                        self.solution.station_worker_assignment[ws2],
                        ws2,
                        self.solution,
                    )
                    insertion_move_1 = AlwabpInsertionMovement(
                        None,
                        self.solution.station_worker_assignment[ws1],
                        ws2,
                        self.solution,
                    )
                    insertion_move_2 = AlwabpInsertionMovement(
                        None,
                        self.solution.station_worker_assignment[ws2],
                        ws1,
                        self.solution,
                    )

                    # Combine the movements into a single swap operation.
                    swap_composition = [
                        removal_move_1,
                        removal_move_2,
                        insertion_move_1,
                        insertion_move_2,
                    ]

                    move = MultipleMovement(self.solution, swap_composition)

                    yield move  # Return the composed movement.
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "WorkerSwapNS":
        """
        Creates a copy of the WorkerSwapNS instance with the same settings.

        Returns:
            WorkerSwapNS: A new instance with identical parameters.
        """
        return WorkerSwapNS()
