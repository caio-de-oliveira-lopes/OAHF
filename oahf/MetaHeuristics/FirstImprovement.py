from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager


class FirstImprovement(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection,
    ):
        """
        Initializes the FirstImprovement metaheuristic.
        :param thread_id: Identifier for the thread.
        :param stop: Stopping criteria for the metaheuristic.
        :param evaluator: Evaluator to assess solutions.
        :param ns: Neighborhood selection strategy.
        :param criteria: Acceptance criteria for new solutions.
        """
        super().__init__(thread_id, stop_criteria, evaluator, acceptance_criteria, ns)

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current FirstImprovement instance."""
        return FirstImprovement(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the first improvement strategy on the given solution."""
        best_sol = sol  # No need to copy here
        curr_sol = best_sol
        best_eval = self.evaluator.evaluate(best_sol)

        self.evaluator.save_evaluation_state(curr_sol)

        ns: Optional[Neighborhood] = self.neighborhood_selection.get_next(self.thread_id)  # type: ignore

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while ns and not self.stop_on_evaluations([best_eval]):
            try:
                if ns is None:
                    ns = self.neighborhood_selection.get_next(self.thread_id)  # type: ignore
            except Exception as ex:
                LogManager.unable_to_get_neighborhood()

            try:
                # Warning: circular selections with no time StopCriteria may get in an infinite loop
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
                            if self.acceptance_criteria.accept(
                                best_eval, curr_eval, curr_sol
                            ):
                                move.report_apply_improvement(curr_eval, best_eval)
                                best_sol = curr_sol  # No need to copy here
                                ns.accept_movement()
                                self.evaluator.save_evaluation_state(best_sol)
                                return best_sol
                            else:
                                move.unapply_operation(curr_eval)

                        move = ns.get_move_operation()
                        self.stop_criteria.increment_counter()
            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                curr_sol = best_sol.copy()

        self.evaluator.save_evaluation_state(best_sol)
        return best_sol

    def set_neighborhood(self, neighborhood):
        """Sets the neighborhood for the FirstImprovement instance."""
        self.neighborhood = neighborhood
