from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class GRASP(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        constructions: MetaHeuristic,
        local_search: MetaHeuristic,
        criteria: AcceptanceCriteria,
    ) -> None:
        """Initialize the GRASP meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            constructions (MetaHeuristic): The construction meta-heuristic.
            local_search (MetaHeuristic): The local search meta-heuristic.
            criteria (AcceptanceCriteria): The acceptance criteria for solutions.
        """
        super().__init__(
            thread_id, stop, evaluator, criteria, constructions, local_search
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
        )

    def run(self, sol: Optional[Solution]) -> Optional[Solution]:
        """Executes the GRASP meta-heuristic.

        Args:
            sol (Optional[Solution]): The initial solution, which can be None.

        Returns:
            Optional[Solution]: The best solution found during execution.
        """
        construction = self.meta_heuristics_used[0]
        local_search = self.meta_heuristics_used[1]

        best_sol = sol.copy() if sol is not None else None
        best_eval = self.evaluator.evaluate(sol) if sol is not None else None

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while not self.stop_on_evaluations(best_eval):
            self.stop_criteria.increment_counter()
            curr_sol = construction.run_operation(
                sol.copy() if sol is not None else None, self
            )
            curr_sol = local_search.run_operation(curr_sol, self)
            curr_eval = self.evaluator.evaluate(curr_sol)

            if best_eval is not None and self.acceptance_criteria.accept(
                best_eval, curr_eval, curr_sol
            ):
                best_eval = curr_eval
                best_sol = curr_sol
                # Optionally log the best evaluation
                # print(best_eval)

        return best_sol
