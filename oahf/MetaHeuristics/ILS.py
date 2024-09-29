from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.MetaHeuristics.Pertubation import Pertubation


class ILS(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        pertubation: Pertubation,
        local_search: MetaHeuristic,
        number_pertubations: int,
        solution_pool: Pool,
        change_solution: StopCriteria,
        criteria: AcceptanceCriteria,
    ) -> None:
        """Initialize the Iterated Local Search (ILS) meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            pertubation (Pertubation): The perturbation method.
            local_search (MetaHeuristic): The local search meta-heuristic.
            number_pertubations (int): Number of perturbations to apply.
            solution_pool (Pool): Pool of solutions.
            change_solution (StopCriteria): Criteria for changing solutions.
            criteria (AcceptanceCriteria): The acceptance criteria for solutions.
        """
        super().__init__(
            thread_id, stop, evaluator, criteria, pertubation, local_search
        )
        self.number_pertubations = number_pertubations
        self.solutions = solution_pool
        self.change_solution_criteria = change_solution

    def copy(self, thread: int) -> "ILS":
        """Creates a copy of the ILS instance.

        Args:
            thread (int): The ID of the thread for the copied instance.

        Returns:
            ILS: A new instance of ILS that is a copy of this instance.
        """
        return ILS
        (
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.meta_heuristics_used[0].copy(thread),
            self.meta_heuristics_used[1].copy(thread),
            self.number_pertubations,
            self.solutions.copy(),
            self.change_solution_criteria.copy(),
            self.acceptance_criteria.copy(),
        )

    def run(self, sol: Optional[Solution]) -> Optional[Solution]:
        """Executes the Iterated Local Search meta-heuristic.

        Args:
            sol (Optional[Solution]): The initial solution, which can be None.

        Returns:
            Optional[Solution]: The best solution found during execution.
        """
        perturbation = self.meta_heuristics_used[0]  # Perturbation method
        local_search = self.meta_heuristics_used[1]  # Local search method

        self.solutions.clear()
        self.stop_criteria.reset()

        curr_sol = sol.copy() if sol is not None else None
        while not self.stop_on_evaluations(
            self.evaluator.evaluate(self.solutions.get_best(self.evaluator))
        ):
            self.change_solution_criteria.increment_counter()

            self.stop_criteria.increment_counter()
            for _ in range(self.number_pertubations):
                curr_sol = perturbation.run_operation(curr_sol, self)

            curr_sol = local_search.run_operation(curr_sol, self)

            self.solutions.add(
                curr_sol.copy() if curr_sol is not None else None, self.evaluator
            )
            if self.change_solution_criteria.stop():
                curr_sol = self.solutions.get_solution_at(
                    ThreadManager.get_next(self.thread_id, 0, self.solutions.count())
                )
                if curr_sol is not None:
                    curr_sol = curr_sol.copy()

                self.change_solution_criteria.reset()

            if self.log_solutions:
                self.log_current_solution(self.evaluator.evaluate(curr_sol))
                self.log_best_solution(
                    self.evaluator.evaluate(self.solutions.get_best(self.evaluator))
                )

        self.solutions.add(
            curr_sol.copy() if curr_sol is not None else None, self.evaluator
        )
        self.solutions.add(sol.copy() if sol is not None else None, self.evaluator)

        return self.solutions.get_best(self.evaluator)
