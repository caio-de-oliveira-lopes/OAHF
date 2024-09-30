from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.MetaHeuristics.Pertubation import Pertubation


class ParallelILS(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        pertubation: Pertubation,
        local_search: MetaHeuristic,
        number_pertubations: int,
        solution_pool: Pool,
        num_threads: int,
        repeatable: bool,
        change_solution_criteria: StopCriteria,
        criteria: AcceptanceCriteria,
        destination_pool: Optional[Pool] = None,
    ) -> None:
        """Initialize the ParallelILS meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria.
            evaluator (Evaluator): The evaluator to assess solutions.
            pertubation (Pertubation): The pertubation strategy.
            local_search (MetaHeuristic): The local search meta-heuristic.
            number_pertubations (int): The number of pertubations to apply.
            solution_pool (Pool): The initial solution pool.
            num_threads (int): The number of threads to use for parallel execution.
            repeatable (bool): Whether to wait for all tasks to finish before proceeding.
            change_solution_criteria (StopCriteria): The criteria to change solutions.
            criteria (AcceptanceCriteria): The acceptance criteria for solutions.
            destination_pool (Optional[Pool]): Optional destination pool.
        """
        super().__init__(
            thread_id, stop, evaluator, criteria, pertubation, local_search
        )
        self.number_pertubations = number_pertubations
        self.initial_sols = solution_pool
        self.solutions = destination_pool if destination_pool else solution_pool
        self.repeatable = repeatable
        self.num_threads = num_threads
        self.change_solution_criteria = change_solution_criteria
        self.pertubations = []  # To be filled in during run
        self.local_searches = []  # To be filled in during run

    def copy(self, thread: int) -> "ParallelILS":
        """Create a copy of the ParallelILS instance.

        Args:
            thread (int): The thread ID for the copied instance.

        Returns:
            ParallelILS: A new instance of ParallelILS.
        """
        return ParallelILS(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.meta_heuristics_used[0].copy(thread),
            self.meta_heuristics_used[1].copy(thread),
            self.number_pertubations,
            self.initial_sols.copy(),
            self.num_threads,
            self.repeatable,
            self.change_solution_criteria.copy(),
            self.acceptance_criteria.copy(),
            self.solutions.copy(),
        )

    def main_run(self, thread_id: int, solutions: List[Solution]) -> None:
        """Run the perturbation and local search on the solution for a given thread.

        Args:
            thread_id (int): The thread ID.
            solutions (List[Solution]): The list of solutions.
        """
        pertubation = self.pertubations[thread_id]
        local_search = self.local_searches[thread_id]
        curr_sol = solutions[thread_id]

        # Apply perturbations
        for _ in range(self.number_pertubations):
            curr_sol = pertubation.run_operation(curr_sol.copy(), self)

        # Apply local search
        curr_sol = local_search.run_operation(curr_sol, self)

        # Update the solution in the thread's solution list
        solutions[thread_id] = curr_sol

    def run(self, sol: Optional[Solution]) -> Optional[Solution]:
        """Execute the ParallelILS meta-heuristic.

        Args:
            sol (Optional[Solution]): The initial solution, which may be None.

        Returns:
            Optional[Solution]: The best solution found.
        """
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            solutions_current = []
            tasks = []

            # Add the initial solution to the solution pool
            self.solutions.add(sol.copy(), self.evaluator)
            for s in self.initial_sols.get_list():
                self.solutions.add(s.copy(), self.evaluator)

            # Initialize perturbations and local searches for each thread
            self.pertubations = [
                self.meta_heuristics_used[0].copy(i + self.thread_id)
                for i in range(self.num_threads)
            ]
            self.local_searches = [
                self.meta_heuristics_used[1].copy(i + self.thread_id)
                for i in range(self.num_threads)
            ]

            self.stop_criteria.reset()

            while not self.stop_on_evaluations(
                self.evaluator.evaluate(self.solutions.get_best(self.evaluator))
            ):
                self.stop_criteria.increment_counter()

                # Decide if we should change the solution
                change_sol = self.change_solution_criteria.stop()
                self.change_solution_criteria.increment_counter()

                if change_sol:
                    solutions_current.clear()
                    self.change_solution_criteria.reset()

                tasks.clear()

                for i in range(self.num_threads):
                    if len(solutions_current) < self.num_threads:
                        solutions_current.append(
                            self.solutions.get_solution_at(
                                ThreadManager.get_next(i, 0, self.solutions.count())
                            ).copy()
                        )
                    tasks.append(executor.submit(self.main_run, i, solutions_current))

                if self.repeatable:
                    [task.result() for task in tasks]  # Wait for all tasks to complete

                # Log and add new solutions to the pool
                for i in range(self.num_threads):
                    if self.log_solutions:
                        self.log_current_solution(
                            self.evaluator.evaluate(solutions_current[i])
                        )
                    self.solutions.add(solutions_current[i], self.evaluator)

                if self.log_solutions:
                    self.log_best_solution(
                        self.evaluator.evaluate(self.solutions.get_best(self.evaluator))
                    )

            # Update meta-heuristics to their first instances
            self.meta_heuristics_used[0] = self.pertubations[0]
            self.meta_heuristics_used[1] = self.local_searches[0]

            return self.solutions.get_best(self.evaluator)
