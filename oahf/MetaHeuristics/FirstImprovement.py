from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager
from oahf.Utils.Util import Util


class FirstImprovement(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        ns: NeighborhoodSelection,
        criteria: AcceptanceCriteria,
    ):
        """
        Initializes the FirstImprovement metaheuristic.
        :param thread_id: Identifier for the thread.
        :param stop: Stopping criteria for the metaheuristic.
        :param evaluator: Evaluator to assess solutions.
        :param ns: Neighborhood selection strategy.
        :param criteria: Acceptance criteria for new solutions.
        """
        super().__init__(thread_id, stop, evaluator, ns, criteria)
        self.neighborhood = None

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current FirstImprovement instance."""
        return FirstImprovement(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.neighborhood_selection.copy(),
            self.acceptance_criteria.copy(),
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the first improvement strategy on the given solution."""
        best_sol = sol  # No need to copy here
        curr_sol = best_sol
        best_eval = self.evaluator.evaluate(best_sol)

        self.evaluator.save_evaluation_state(curr_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while not self.stop_on_evaluations(best_eval):
            ns = self.neighborhood

            try:
                if ns is None:
                    ns = self.neighborhood_selection.get_next(self.thread_id)
            except Exception as ex:
                LogManager.unable_to_get_neighborhood()

            try:
                if ns is None:
                    break

                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)

                if build:
                    move = ns.get_move_operation()
                    self.stop_criteria.increment_counter()
                    while move is not None and not self.stop_on_evaluations(best_eval):
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
                LogManager.something_went_wrong(ns, ex)
                curr_sol = best_sol.copy() if best_sol else None

        self.evaluator.save_evaluation_state(best_sol)
        return best_sol

    def set_neighborhood(self, neighborhood):
        """Sets the neighborhood for the FirstImprovement instance."""
        self.neighborhood = neighborhood
