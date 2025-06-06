from typing import Any, Dict, List, Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import ListPool, MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class IterativeConstruction(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        constructions: MetaHeuristic,
        acceptance_criteria: AcceptanceCriteria,
        override_construction_ns: List[NeighborhoodSelection],
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ) -> None:
        """Initialize the IterativeConstruction meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            constructions (MetaHeuristic): The construction meta-heuristic.
            local_search (MetaHeuristic): The local search meta-heuristic.
            acceptance_criteria (AcceptanceCriteria): The acceptance criteria for solutions.
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            None,
            [constructions],
            origin_pool,
            destination_pool,
        )
        # list of neighborhood selection to iterate over and override the construction mh ns
        self._override_construction_ns = override_construction_ns

    def copy(self, thread: int) -> "IterativeConstruction":
        """Creates a copy of the IterativeConstruction instance.

        Args:
            thread (int): The ID of the thread for the copied instance.

        Returns:
            IterativeConstruction: A new instance of IterativeConstruction that is a copy of this instance.
        """
        return IterativeConstruction(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.meta_heuristics_used[0].copy(thread),
            self.acceptance_criteria.copy(),
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the IterativeConstruction meta-heuristic.

        Args:
            solution (Solution): The initial solution.

        Returns:
            Solution: The best solution found during execution.
        """
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(self, origin_pool: Pool, destination_pool: Pool, parent: Optional["MetaHeuristic"] = None) -> Pool:
        """Executes the IterativeConstruction meta-heuristic.

        Args:
            origin_pool (Pool): The initial solution pool, which can be empty.
            destination_pool (Pool): The output solution pool, which can be empty and even the same pool as the input pool.

        Returns:
            Pool: The output_pool of solutions found during execution.
        """
        self.parent_metaheuristic = parent
        construction = self.meta_heuristics_used[0]
        best_sol = origin_pool.solutions[0].copy()
        best_sol.reset(complete_reset=True)
        best_eval = self.evaluator.evaluate(best_sol)

        all_ns = self._override_construction_ns or [construction.get_neighborhood_selection()]
        for ns in all_ns:
            curr_pool = ListPool([best_sol])
            construction.set_neighborhood_selection(ns)
            
            self.stop_criteria.reset()
            self.acceptance_criteria.reset()

            while not self.stop_on_evaluations([best_eval]):
                curr_pool = construction.run_operation(curr_pool, None, self)

                curr_sol = curr_pool.get_best(self.evaluator)
                if not curr_sol or not curr_sol.validate_aspects():
                    curr_eval = self.evaluator.evaluate(curr_sol)
                    if self.stop_on_evaluations([curr_eval]):
                        break
                    else:
                        continue

                if curr_sol:
                    curr_eval = self.evaluator.evaluate(curr_sol)
                    if not (curr_eval.infeasible() or curr_eval.has_penalty()):
                        destination_pool.add_solution(curr_sol, self)

                self.stop_criteria.increment_counter()

        return destination_pool
