from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class GRASP(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        constructions: MetaHeuristic,
        local_search: MetaHeuristic,
        acceptance_criteria: AcceptanceCriteria,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ) -> None:
        """Initialize the GRASP meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            constructions (MetaHeuristic): The construction meta-heuristic.
            local_search (MetaHeuristic): The local search meta-heuristic.
            acceptance_criteria (AcceptanceCriteria): The acceptance criteria for solutions.
            acceptance_criteria (Pool): Pool Type to be used as default (solutions will not be kept)
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            None,
            [constructions, local_search],
            origin_pool,
            destination_pool,
        )

    def copy(self, thread: int) -> "GRASP":
        """Creates a copy of the GRASP instance.

        Args:
            thread (int): The ID of the thread for the copied instance.

        Returns:
            GRASP: A new instance of GRASP that is a copy of this instance.
        """
        return GRASP(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.meta_heuristics_used[0].copy(thread),
            self.meta_heuristics_used[1].copy(thread),
            self.acceptance_criteria.copy(),
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the GRASP meta-heuristic.

        Args:
            solution (Solution): The initial solution.

        Returns:
            Solution: The best solution found during execution.
        """
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(self, origin_pool: Pool, destination_pool: Pool) -> Pool:
        """Executes the GRASP meta-heuristic.

        Args:
            origin_pool (Pool): The initial solution pool, which can be empty.
            destination_pool (Pool): The output solution pool, which can be empty and even the same pool as the input pool.

        Returns:
            Pool: The output_pool of solutions found during execution.
        """
        construction = self.meta_heuristics_used[0]
        local_search = self.meta_heuristics_used[1]

        curr_pool = origin_pool.copy()
        best_sol = curr_pool.get_best(self.evaluator)
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while not self.stop_on_evaluations([best_eval]):
            curr_pool = construction.run_operation(
                curr_pool, None, self
            )

            curr_sol = curr_pool.get_best(self.evaluator)
            if not curr_sol or not curr_sol.validade_aspects():
                continue

            curr_pool = local_search.run_operation(
                curr_pool, None, self
            )
            curr_sol = curr_pool.get_best(self.evaluator)

            if curr_sol:
                curr_eval = self.evaluator.evaluate(curr_sol)

                if best_eval is not None and self.acceptance_criteria.accept(
                    best_eval, curr_eval, curr_pool
                ):
                    best_eval = curr_eval
                    best_sol = curr_sol
                    destination_pool.add_solution(best_sol)
                    # Optionally log the best evaluation
                    # print(best_eval)

            self.stop_criteria.increment_counter()

        return destination_pool
