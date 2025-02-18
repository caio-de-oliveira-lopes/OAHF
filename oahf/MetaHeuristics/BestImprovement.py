from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager


class BestImprovement(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection,
    ):
        """
        Initializes the BestImprovement metaheuristic.
        :param thread_id: Identifier for the thread.
        :param stop: Stopping criteria for the metaheuristic.
        :param evaluator: Evaluator to assess solutions.
        :param ns: Neighborhood selection strategy.
        :param criteria: Acceptance criteria for new solutions.
        """
        super().__init__(
            thread_id, stop_criteria, evaluator, acceptance_criteria, ns.copy()
        )

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current BestImprovement instance."""
        return BestImprovement(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the best improvement strategy on the given solution."""
        best_sol = sol.copy()
        curr_sol = sol.copy()
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while (ns := self.neighborhood_selection.get_next(self.thread_id)) and not self.stop_on_evaluations([best_eval]):  # type: ignore
            try:
                # Warning: circular selections with no time StopCriteria may get in an infinite loop
                if ns is None:
                    break

                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)

                if build:
                    while (
                        move := ns.get_move_operation()
                    ) is not None and not self.stop_on_evaluations([best_eval]):
                        worked = move.apply()
                        if worked:
                            curr_eval = self.evaluator.evaluate(curr_sol)

                            if self.acceptance_criteria.accept(
                                best_eval, curr_eval, curr_sol
                            ):
                                best_sol = curr_sol.copy()
                                best_eval = curr_eval

                            move.unapply()

                        self.stop_criteria.increment_counter()

            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                curr_sol = best_sol.copy()

        return best_sol
