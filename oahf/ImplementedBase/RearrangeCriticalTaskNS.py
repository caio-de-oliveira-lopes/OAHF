from typing import Iterator, Optional

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation
from oahf.Logger.LogManager import LogManager


class RearrangeCriticalTaskNS(Neighborhood):
    """
    Implements a neighborhood search strategy for the ALWABP problem.
    This class explores movements that rearrange tasks between stations,
    aiming to improve the solution by balancing critical and non-critical stations.
    """

    def __init__(
        self,
        graph_orientation: GraphOrientation
    ):
        """
        Initializes the RearrangeCriticalTaskNS instance.

        Parameters:
            graph_orientation (GraphOrientation): The direction of the task precedence graph.
        """
        super().__init__(False)
        self.enumerator: Optional[Iterator[Movement]] = None
        self.solution: Optional[AlwabpSolution] = None
        self.thread_id: int = 0
        self.cost_function = None
        self.graph_orientation: GraphOrientation = graph_orientation

    def build_neighborhood(self, thread_id: int, solution: AlwabpSolution) -> bool:
        """
        Prepares the neighborhood for exploration.

        This includes initializing the solution, identifying critical and
        non-critical workstations, and setting up an iterator for movements.

        Parameters:
            thread_id (int): The ID of the thread executing this neighborhood.
            solution (AlwabpSolution): The solution to base the neighborhood search on.

        Returns:
            bool: True if the neighborhood was successfully built.
        """

        solution.default_graph_orientation = self.graph_orientation

        self.solution = solution
        self.critical_workstations = self.solution.get_critical_workstations()
        self.non_critical_workstations = [
            station
            for station in self.solution.stations
            if station not in self.critical_workstations
        ]
        self.thread_id = thread_id
        self.enumerator = self.all_moves()
        return True

    def get_move(self) -> Optional[Movement]:
        """
        Retrieves the next available movement from the neighborhood.

        Returns:
            Optional[Movement]: The next movement, or None if no more movements are available.
        """
        if not self.enumerator:
            return None
        try:
            return next(self.enumerator)
        except StopIteration:
            return None

    def all_moves(self) -> Iterator[Movement]:
        """
        Generates all possible task rearrange movements in the neighborhood.

        This involves:
        - Identifying tasks in critical workstations.
        - Checking if tasks can be moved to non-critical workstations while
          respecting precedence constraints.
        - Creating a composite movement (task removal + insertion) for each valid rearrangement.

        Yields:
            Movement: A valid task rearrange movement.
        """
        if self.solution and len(self.critical_workstations) > 0:
            # First approach uses only the first critical workstation
            critical_workstations = [self.critical_workstations[0]]

            # Second approach uses all critical workstations
            # critical_workstations = self.critical_workstations

            for critical_workstation in critical_workstations:
                tasks_on_critical_station = list(
                    self.solution.station_tasks_assignment[critical_workstation]
                )
                # Iterate over non-critical workstations
                for ncw in self.non_critical_workstations:
                    if self.allow_infeasible_movements:
                        available_tasks_to_rearrange = tasks_on_critical_station
                    else:
                        # Retrieve tasks that can be rearranged while maintaining precedence constraints
                        available_tasks_to_rearrange = [
                            task
                            for task in tasks_on_critical_station
                            if self.solution.can_task_be_assigned_to(task, ncw)
                        ]

                    for task in available_tasks_to_rearrange:
                        # Define the removal and insertion movements
                        removal_move = AlwabpRemovalMovement(
                            task, None, critical_workstation, self.solution
                        )
                        insertion_move = AlwabpInsertionMovement(
                            task, None, ncw, self.solution
                        )

                        # Combine the movements into a rearrange operation
                        rearrange_composition = [removal_move, insertion_move]

                        move = MultipleMovement(self.solution, rearrange_composition)

                        yield move
        elif not self.solution:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "RearrangeCriticalTaskNS":
        """
        Creates a deep copy of the RearrangeCriticalTaskNS instance.

        Returns:
            RearrangeCriticalTaskNS: A new instance with the same configuration as the original.
        """
        return RearrangeCriticalTaskNS(self.graph_orientation)
