import time
from typing import List

from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.Utils.Util import Util


class GenericMultipleMetaheuristic(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        meta_heuristics,
        pool: Pool,
        num_threads: int,
        repeatable: bool,
        change_solution: StopCriteria,
        criteria,
    ):
        """
        Initializes the GenericMultipleMetaheuristic.
        :param thread_id: Identifier for the thread.
        :param stop: Stopping criteria for the metaheuristic.
        :param evaluator: Evaluator to assess solutions.
        :param meta_heuristics: Array of metaheuristic instances.
        :param pool: Pool for solutions.
        :param num_threads: Number of threads to use.
        :param repeatable: Indicates if the process is repeatable.
        :param change_solution: Criteria to change the solution.
        :param criteria: Acceptance criteria for new solutions.
        """
        super().__init__(thread_id, stop, evaluator, criteria, meta_heuristics)
        self.solution_pool = pool
        self.mhs = [
            [None for _ in range(num_threads)] for _ in range(len(meta_heuristics))
        ]
        self.num_threads = num_threads
        self.repeatable = repeatable
        self.change_solution_criteria = change_solution

    def copy(self, thread: int) -> "MetaHeuristic":
        copied_metaheuristics = [m.copy(thread) for m in self.meta_heuristics_used]
        return GenericMultipleMetaheuristic(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            copied_metaheuristics,
            self.solution_pool.copy(),
            self.num_threads,
            self.repeatable,
            self.change_solution_criteria.copy(),
            self.acceptance_criteria.copy(),
        )

    def main_run(self, thread_id: int, solutions: List, mhs: List) -> None:
        mh = mhs[thread_id]
        curr_sol = solutions[thread_id]
        curr_sol = mh.run_operation(curr_sol, self)
        solutions[thread_id] = curr_sol

    def run(self, sol) -> "Solution":
        solutions_current = (
            [sol.copy() for _ in range(self.num_threads)]
            if sol
            else [None] * self.num_threads
        )
        best_eval = self.evaluator.evaluate(sol)

        self.stop_criteria.set_progress_report(0.1)
        threads_not_finished = set()

        while not self.stop_on_evaluations(best_eval):
            self.change_solution_criteria.reset()

            for m in range(len(self.meta_heuristics_used)):
                change_sol = self.change_solution_criteria.stop()
                if change_sol:
                    for i in range(self.num_threads):
                        if i not in threads_not_finished:
                            solutions_current[i] = self.solution_pool.get_solution_at(
                                ThreadManager.get_next(
                                    self.thread_id, 0, self.solution_pool.count()
                                )
                            ).copy()

                    self.change_solution_criteria.reset()

                self.change_solution_criteria.increment_counter()

                if self.repeatable:
                    tasks = [None] * self.num_threads

                for i in range(self.num_threads):
                    if i not in threads_not_finished:
                        if i == 0:
                            self.stop_criteria.increment_counter()
                        x = i
                        m2 = m
                        threads_not_finished.add(x)
                        tasks[i] = ThreadManager.for_each(
                            x,
                            [x],
                            lambda _: self.main_run(x, solutions_current, self.mhs[m2]),
                        )

                if self.repeatable:
                    # Wait for all threads to finish
                    ThreadManager.main_for_wait_all(
                        self.num_threads,
                        lambda x: self.main_run(x, solutions_current, self.mhs[m]),
                    )
                else:
                    # Wait for any thread to finish
                    ThreadManager.main_for_wait_any(
                        self.num_threads,
                        lambda x: self.main_run(x, solutions_current, self.mhs[m]),
                    )

                for i in range(self.num_threads):
                    if i in threads_not_finished:
                        # Assuming tasks[i] would have some mechanism to check if it is done
                        if tasks[i].done():
                            threads_not_finished.remove(i)
                            if self.log_solutions:
                                Util.logger.error(
                                    f"Current Solution: {self.evaluator.evaluate(solutions_current[i])}"
                                )
                            self.solution_pool.add(solutions_current[i], self.evaluator)
                            best_eval = self.evaluator.evaluate(
                                self.solution_pool.get_best(self.evaluator)
                            )

            # Simulate a small delay
            time.sleep(0.1)

        for i in range(len(self.meta_heuristics_used)):
            self.meta_heuristics_used[i] = self.mhs[i][
                0
            ]  # Update to the first in the array

        return self.solution_pool.get_best(self.evaluator)
