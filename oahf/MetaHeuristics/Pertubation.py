from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager


class Pertubation(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        ns: NeighborhoodSelection,
        acceptance_criteria: AcceptanceCriteria,
        accept_infeasible: bool,
    ) -> None:
        """
        Initialize the Perturbation metaheuristic.

        Args:
            thread_id (int): The thread identifier, used to manage thread-specific operations.
            stop (StopCriteria): Criteria that determine when the Perturbation algorithm should stop
                iterating.
            evaluator (Evaluator): An object responsible for evaluating the quality of solutions.
            ns (NeighborhoodSelection): The neighborhood selection strategy used to explore
                the solution space during the algorithm's execution.
            acceptance_criteria (AcceptanceCriteria): Criteria for determining whether a new solution
                should be accepted into the current set of solutions.
            accept_infeasible (bool): A flag indicating whether infeasible solutions can be accepted,
                allowing the algorithm to explore areas outside the feasible region to potentially
                escape local optima.
        """
        super().__init__(thread_id, stop, evaluator, acceptance_criteria, ns.copy())
        self.accept_infeasible = accept_infeasible

    def copy(self, thread: int) -> "Pertubation":
        """Creates a copy of the Pertubation instance.

        Args:
            thread (int): The ID of the thread for the copied instance.

        Returns:
            Pertubation: A new instance of Pertubation that is a copy of this instance.
        """
        return Pertubation(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.neighborhood_selection.copy(),  # type: ignore
            self.acceptance_criteria.copy(),
            self.accept_infeasible,
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the Pertubation meta-heuristic.

        Args:
            sol (Solution): The initial solution.

        Returns:
            Solution: The best solution found during execution.
        """
        best_sol = sol.copy()  # Keep track of the best solution
        curr_sol = sol.copy()
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()

        while not self.stop_on_evaluations([best_eval]):
            ns = None

            try:
                ns = self.neighborhood_selection.get_next(self.thread_id)  # type: ignore
            except Exception as ex:
                LogManager.unable_to_get_neighborhood()

            try:
                if ns is None:
                    break

                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)

                if build:
                    move = ns.get_move_operation()
                    self.stop_criteria.increment_counter()
                    while move is not None and not self.stop_on_evaluations(
                        [best_eval]
                    ):
                        worked = move.apply_operation()
                        if worked:
                            curr_eval = self.evaluator.evaluate(curr_sol)
                            if (
                                self.acceptance_criteria.accept(
                                    best_eval, curr_eval, curr_sol
                                )
                                and self.accept_infeasible
                                or not curr_eval.infeasible()
                            ):
                                best_sol = curr_sol.copy()
                                return best_sol
                            else:
                                move.unapply_operation(curr_eval)

                        move = ns.get_move_operation()
                        self.stop_criteria.increment_counter()
            except Exception as ex:
                LogManager.something_went_wrong(str(ns), ex)

                curr_sol = best_sol.copy()

        return best_sol
