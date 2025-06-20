from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase import ListPool
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.BestImprovement import BestImprovement


class MultipleBestImprovement(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection,
        destination_pool: Optional[Pool] = None,
    ):
        """
        Initializes the MultipleBestImprovement metaheuristic.
        :param thread_id: Identifier for the thread.
        :param stop: Stopping criteria for the metaheuristic.
        :param evaluator: Evaluator to assess solutions.
        :param ns: Neighborhood selection strategy.
        :param criteria: Acceptance criteria for new solutions.
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            ns.copy(),
            destination_pool=destination_pool,
        )
        self.num_selections = ns.num_neighborhoods()

    def copy(self, thread: int) -> "MultipleBestImprovement":
        """Creates a copy of the current MultipleBestImprovement instance."""
        return MultipleBestImprovement(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
            destination_pool=(
                self.destination_pool.copy() if self.destination_pool else None
            ),
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the best improvement strategy on the given solution."""
        best_sol = sol.copy()
        curr_sol = best_sol
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        if self.neighborhood_selection:
            self.neighborhood_selection.reset(self.thread_id)

            while not self.stop_on_evaluations([best_eval]):

                self.stop_criteria.increment_counter()
                best_pool = ListPool([best_sol])

                for _, ns in zip(range(self.num_selections), iter(lambda: self.neighborhood_selection.get_next(self.thread_id), None)):  # type: ignore
                    try:
                        # Warning: circular selections with no time StopCriteria may get in an infinite loop
                        if ns is None:
                            break

                        best_improv = BestImprovement(
                            self.thread_id,
                            NoStopCriteria(),
                            self.evaluator,
                            self.acceptance_criteria,
                            ListSelection(False, ns),
                        )

                        improved_sol = best_improv.run(best_sol)
                        curr_eval = self.evaluator.evaluate(improved_sol)
                        if not (curr_eval.infeasible() or curr_eval.has_penalty()):
                            best_pool.add_solution(improved_sol, self)

                            if self.destination_pool:
                                self.destination_pool.add_solution(improved_sol, self)

                    except Exception as ex:
                        LogManager.something_went_wrong(self.__class__.__name__, ex)
                        curr_sol = best_sol.copy()

                curr_sol = best_pool.get_best(self.evaluator)

                if curr_sol is None:
                    continue

                curr_eval = self.evaluator.evaluate(curr_sol)

                if self.acceptance_criteria.accept(best_eval, curr_eval, curr_sol):
                    if not (curr_eval.infeasible() or curr_eval.has_penalty()):
                        best_sol = curr_sol.copy()
                        best_eval = curr_eval
                        self.neighborhood_selection.reset(self.thread_id)

        return best_sol
