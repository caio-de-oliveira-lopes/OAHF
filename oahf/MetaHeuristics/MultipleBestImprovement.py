from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase import ListPool
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.BestImprovement import BestImprovement
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.ImplementedBase.ListSelection import ListSelection


class MultipleBestImprovement(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection
    ):
        """
        Initializes the MultipleBestImprovement metaheuristic.
        :param thread_id: Identifier for the thread.
        :param stop: Stopping criteria for the metaheuristic.
        :param evaluator: Evaluator to assess solutions.
        :param ns: Neighborhood selection strategy.
        :param criteria: Acceptance criteria for new solutions.
        """
        super().__init__(thread_id, stop_criteria, evaluator, acceptance_criteria, ns)
        self.num_selections = ns.num_neighborhoods()

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current MultipleBestImprovement instance."""
        return MultipleBestImprovement(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the best improvement strategy on the given solution."""
        best_sol = sol.copy()
        curr_sol = best_sol
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()
        
        if self.neighborhood_selection:
            while not self.stop_on_evaluations([best_eval]):
                
                self.stop_criteria.increment_counter()
                best_pool = ListPool()
            
                for _, ns in zip(range(self.num_selections), iter(lambda: self.neighborhood_selection.get_next(self.thread_id), None)): # type: ignore
                    try:
                        # Warning: circular selections with no time StopCriteria may get in an infinite loop
                        if ns is None:
                            break

                        best_improv = BestImprovement(self.thread_id, NoStopCriteria(), self.evaluator, 
                                                      self.acceptance_criteria, ListSelection(False, ns))
                        
                        best_pool.add_solution(best_improv.run(best_sol))
                    
                    except Exception as ex:
                        LogManager.something_went_wrong(self.__class__.__name__, ex)
                        curr_sol = best_sol.copy()
            
                curr_sol = best_pool.get_best(self.evaluator)
            
                if curr_sol is None: 
                    continue

                curr_eval = self.evaluator.evaluate(curr_sol)
            
                if self.acceptance_criteria.accept(
                    best_eval, curr_eval, curr_sol
                ):
                    best_sol = curr_sol.copy()
                    best_eval = curr_eval
                    self.neighborhood_selection.reset(self.thread_id)
                else:
                    break

        return best_sol
