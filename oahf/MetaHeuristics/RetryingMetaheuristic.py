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
        retry_on_same_iteration: bool = False,
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
        self.retry_on_same_iteration = retry_on_same_iteration

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
        self.parent_metaheuristic = parent
        if destination_pool is None:
            raise Exception("Missing destination pool")
        
        line = Util.line()
        half = len(line) // 2
        half_line = line[:half]

        # Set up
        best_sol = destination_pool.get_best(self.evaluator)
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        # Loop: try main, then if not accepted, apply LS and retry
        while not self.stop_on_evaluations([]):
            # Run main metaheuristic
            Util.logger().info(f"Running Metaheuristic {self.main_mh.name} at {Util.get_duration_from_start_timestamp()}.")
            self.main_mh.run_operation(origin_pool, destination_pool, self)

            curr_sol = destination_pool.get_best(self.evaluator)
            curr_eval = self.evaluator.evaluate(curr_sol)

            # Check acceptance
            if self.acceptance_criteria.accept(best_eval, curr_eval, curr_sol): # type: ignore
                if not (curr_eval.infeasible() or curr_eval.has_penalty()):
                    destination_pool.add_solution(curr_sol, self.main_mh)
                    best_sol = curr_sol
                    break

            # Stoping check placed here to contemplate the time stop criteria
            if self.stop_on_evaluations([]):
                break

            last_idx = len(self.local_search_list) - 1
            # Otherwise apply local searches
            for idx, ls_mh in enumerate(self.local_search_list):
                # Stoping check placed here to contemplate the time stop criteria
                if self.stop_on_evaluations([]):
                    break

                print(half_line)

                Util.logger().info(f"Applying local search {ls_mh.name} at {Util.get_duration_from_start_timestamp()}.")
                ls_mh.run_operation(ls_mh.origin_pool if ls_mh.origin_pool is not None else origin_pool, ls_mh.destination_pool, self)
                Util.logger().info(f"Finishing local search {ls_mh.name} at {Util.get_duration_from_start_timestamp()}.")

                if idx == last_idx:
                    print(half_line)

            # Stoping check placed here to contemplate the time stop criteria
            if self.stop_on_evaluations([]):
                break

            # Run the main metaheuristic again
            if self.retry_on_same_iteration:
                Util.logger().info(f"Retrying Metaheuristic {self.main_mh.name} at {Util.get_duration_from_start_timestamp()}.")

                self.main_mh.run_operation(origin_pool, destination_pool, self)
                curr_sol = destination_pool.get_best(self.evaluator)
                curr_eval = self.evaluator.evaluate(curr_sol)

                if not (curr_eval.infeasible() or curr_eval.has_penalty()):
                    destination_pool.add_solution(curr_sol, self)
            else:
                Util.logger().info(f"Not Retrying Metaheuristic {self.main_mh.name} due to parameter choice.")

            self.stop_criteria.increment_counter()

        return destination_pool
