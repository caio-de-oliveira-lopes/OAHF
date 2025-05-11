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
        # Initial solution copies
        best_sol = sol
        curr_sol = best_sol.copy()

        # Cache frequently used attributes
        evaluator = self.evaluator
        acceptance = self.acceptance_criteria
        stop_criteria = self.stop_criteria
        neighborhood_selection = self.neighborhood_selection
        thread_id = self.thread_id

        best_eval = evaluator.evaluate(best_sol)
        stop_criteria.reset()
        acceptance.reset()
        if self.neighborhood_selection:
            self.neighborhood_selection.reset(self.thread_id)

        while (ns := neighborhood_selection.get_next(thread_id)) and not self.stop_on_evaluations([best_eval]):  # type: ignore
            try:
                if ns is None:
                    break

                if ns.build_neighborhood_operation(thread_id, curr_sol):
                    while (
                        move := ns.get_move()
                    ) is not None and not self.stop_on_evaluations([best_eval]):
                        if move.apply():
                            curr_eval = evaluator.evaluate(curr_sol)
                            if acceptance.accept(best_eval, curr_eval, curr_sol):
                                best_sol = curr_sol.copy()
                                best_eval = curr_eval
                            move.unapply()
                        stop_criteria.increment_counter()
            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                curr_sol = best_sol.copy()

        return best_sol
