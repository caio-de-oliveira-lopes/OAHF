from typing import List, Optional
import gc
import time

from oahf.Base import Solution
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.ImplementedBase.ListPool import ListPool
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Utils.Util import Util


class RetryingMetaheuristic(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator,
        main_metaheuristic: MetaHeuristic,
        local_searches: List[MetaHeuristic],
        acceptance_criteria: AcceptanceCriteria,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
        """
        A metaheuristic that repeatedly runs a main MH until its best solution
        is accepted; otherwise cycles through a list of local-search MHs to improve
        and retries.
        """

        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            neighborhood_selection=None,
            meta_heuristics_used=[main_metaheuristic] + local_searches,
            origin_pool=origin_pool,
            destination_pool=destination_pool,
        )

        self.main_mh = main_metaheuristic
        self.local_search_list = local_searches
        self._ls_index = 0

    def copy(self, thread: int) -> "RetryingMetaheuristic":
        return RetryingMetaheuristic(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.main_mh.copy(thread),
            [mh.copy(thread) for mh in self.local_search_list],
            self.acceptance_criteria.copy(),
            self.origin_pool.copy() if self.origin_pool else None,
            self.destination_pool.copy() if self.destination_pool else None,
        )

    def run(self, sol: Solution) -> Solution:
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(
        self,
        origin_pool: Pool,
        destination_pool: Optional[Pool] = None,
        parent: Optional[MetaHeuristic] = None,
    ) -> Pool:
        if destination_pool is None:
            raise Exception("Missing destination pool")

        # Set up
        best_sol = destination_pool.get_best(self.evaluator)
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        # Loop: try main, then if not accepted, apply LS and retry
        while not self.stop_on_evaluations([]):
            # Run main metaheuristic
            Util.logger().info(f"Running main Metaheuristic {self.main_mh.name}...")
            self.main_mh.run_operation(origin_pool, destination_pool)

            curr_sol = destination_pool.get_best(self.evaluator)
            curr_eval = self.evaluator.evaluate(curr_sol)
            # Check acceptance
            if self.acceptance_criteria.accept(best_eval, curr_eval, curr_sol): # type: ignore
                destination_pool.add_solution(curr_sol, self)
                best_sol = curr_sol
                break

            # Otherwise apply next local search
            ls_mh = self.local_search_list[self._ls_index]
            self._ls_index = (self._ls_index + 1) % len(self.local_search_list)
            Util.logger().info(f"Acceptance Criteria not met, applying local search {ls_mh.name}...")
            ls_mh.named_parent = self.main_mh
            ls_mh.run_operation(ls_mh.origin_pool if ls_mh.origin_pool is not None else origin_pool, ls_mh.destination_pool)

            self.stop_criteria.increment_counter()

        return destination_pool
