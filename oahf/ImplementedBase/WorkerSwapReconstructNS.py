from typing import Iterator, Optional

from oahf.Base.Evaluator import Evaluator
from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpRemovalMovement import AlwabpRemovalMovement
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.ImplementedBase.WorkerSwapNS import WorkerSwapNS
from oahf.Logger.LogManager import LogManager


class WorkerSwapReconstructNS(Neighborhood):
    """
    WorkerSwapReconstructNS performs a worker swap followed by solution reconstruction
    to generate neighborhood movements in ALWABP solutions.
    """

    def __init__(
        self,
        reconstruction_metaheuristic: "MetaHeuristic",
        evaluator: Evaluator,
        stop_criteria: Optional[StopCriteria],
    ):
        """
        Initializes the neighborhood search with dependencies and reconstruction logic.

        Args:
            graph_orientation (GraphOrientation): Dependency orientation (e.g., precedence relationships).
            reconstruction_metaheuristic (MetaHeuristic): Metaheuristic for solution reconstruction.
            stop_criteria (Optional[StopCriteria]): Optional criteria to terminate the search.
        """
        super().__init__(stop_criteria, False)

        from oahf.Base.MetaHeuristic import MetaHeuristic

        self.enumerator: Optional[Iterator[Movement]] = (
            None  # Stores the current movement iterator.
        )
        self.solution: Optional[AlwabpSolution] = (
            None  # Holds the current solution being explored.
        )
        self.thread_id: int = 0  # Thread identifier for parallel execution.
        self.cost_function = None  # Optional cost function for evaluating movements.
        self.worker_swap_ns = WorkerSwapNS(stop_criteria)
        self.reconstruction_metaheuristic: MetaHeuristic = reconstruction_metaheuristic
        self.evaluator = evaluator

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

        # Build the neighborhood for worker swaps.
        return self.worker_swap_ns.build_neighborhood_operation(
            self.thread_id, self.solution
        )

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
        Generates all possible movements by swapping workers and reconstructing solutions.

        Yields:
            Movement: A composed movement representing a worker swap and reconstruction.
        """
        if self.solution and self.stop_criteria:
            # Generate removal movements for cleaning.
            cleaning_moves = [
                AlwabpRemovalMovement(task, None, station, self.solution, self.report)
                for station in self.solution.stations
                for task in self.solution.station_tasks_assignment[station]
            ]

            cleaning_movement = MultipleMovement(
                self.solution, self.report, cleaning_moves
            )
            solution_copy = self.solution.copy()
            cleaning_movement_copy = cleaning_movement.copy(solution_copy)

            # Apply the cleaning movement to prepare the solution.
            if cleaning_movement_copy.apply():
                # Iterate over all possible worker swap movements.
                while workers_swap_move := self.worker_swap_ns.get_move_operation():
                    workers_swap_move_copy = workers_swap_move.copy(solution_copy)
                    if workers_swap_move_copy.apply():

                        # Run the reconstruction metaheuristic on the modified solution.
                        cycle_time_limit = solution_copy.cycle_time_limit
                        curr_eval = self.evaluator.evaluate(solution_copy)

                        # Store workers allocations to restore in case of failure to build the solution
                        restore_assignment_moves = [
                            AlwabpInsertionMovement(
                                None,
                                solution_copy.station_worker_assignment[s],
                                s,
                                solution_copy,
                                self.report,
                            )
                            for s in solution_copy.stations
                        ]
                        restore_assignment = MultipleMovement(
                            solution_copy, self.report, restore_assignment_moves
                        )

                        while not self.stop_criteria.stop_on_evaluations([curr_eval]):
                            dgo = solution_copy.default_graph_orientation

                            reconstructed_solution = (
                                self.reconstruction_metaheuristic.run(solution_copy)
                            )

                            if isinstance(reconstructed_solution, AlwabpSolution):
                                reconstructed_solution.default_graph_orientation = dgo

                            if (
                                neighborhood_selection := self.reconstruction_metaheuristic.get_neighborhood_selection()
                            ):
                                neighborhood_selection.reset(self.thread_id)

                            # Validate and process the reconstructed solution.
                            if (
                                isinstance(reconstructed_solution, AlwabpSolution)
                                and reconstructed_solution.validade_aspects()
                            ):
                                break

                            # After validade aspects, if solution is not according, it`ll be reset (since reconstructed_solution was rejected)
                            solution_copy.validade_aspects()
                            # This move will restore the workers allocations to it`s previous state
                            restore_assignment.apply()
                            curr_eval = self.evaluator.evaluate(solution_copy)

                        if (
                            isinstance(reconstructed_solution, AlwabpSolution)
                            and reconstructed_solution.validade_aspects()
                        ):
                            # Generate insertion movements for reconstruction.
                            reconstruction_moves = [
                                AlwabpInsertionMovement(
                                    task, None, station, self.solution, self.report
                                )
                                for station in reconstructed_solution.stations
                                for task in reconstructed_solution.station_tasks_assignment[
                                    station
                                ]
                            ]

                            reconstruction_move = MultipleMovement(
                                self.solution, self.report, reconstruction_moves
                            )

                            # Combine all movements into a single composed movement.
                            full_move_composition = [
                                cleaning_movement,
                                workers_swap_move,
                                reconstruction_move,
                            ]

                            move = MultipleMovement(
                                self.solution, self.report, full_move_composition
                            )

                            move.tabu_counter_over_iterations = 0.5

                            yield move  # Return the composed movement.

                        # Revert the worker swap if reconstruction was invalid.
                        workers_swap_move_copy.unapply()

                        if cycle_time_limit:
                            solution_copy.cycle_time_limit = cycle_time_limit
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "WorkerSwapReconstructNS":
        """
        Creates a copy of the WorkerSwapReconstructNS instance with the same settings.

        Returns:
            WorkerSwapReconstructNS: A new instance with identical parameters.
        """
        return WorkerSwapReconstructNS(
            self.reconstruction_metaheuristic,
            self.evaluator,
            self.stop_criteria.copy() if self.stop_criteria else None,
        )
