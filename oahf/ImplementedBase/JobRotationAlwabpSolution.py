from typing import List, Optional

from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.ImplementedBase.LpExecutionData import LpExecutionData
from oahf.Utils.Util import Util


class JobRotationAlwabpSolution(Solution):
    def __init__(self, number_of_periods: int, lp_execution_data: LpExecutionData):
        super().__init__()
        self.number_of_periods = number_of_periods
        self.period_solutions: List[Optional[AlwabpSolution]] = [
            None
        ] * number_of_periods  # List to hold solutions for each period
        self._distinct_tasks_memo = {}  # Memorization for distinct tasks per worker
        self.lp_execution_data = lp_execution_data
        self.name = "JobRotationAlwabpSolution"

    def assign_solution_to_period(self, period: int, solution: AlwabpSolution):
        """
        Assigns an AlwabpSolution to a specific period.

        Args:
            period (int): The period index.
            solution (AlwabpSolution): The solution to assign.
        """
        if 0 <= period < self.number_of_periods:
            self.period_solutions[period] = solution
        self._distinct_tasks_memo.clear()  # Reset memoization on new assignment

    def calculate_worker_distinct_tasks(self, worker: int) -> int:
        """
        Calculates the number of distinct tasks executed by a worker across all periods.
        Uses memoization to avoid redundant calculations.

        Args:
            worker (int): The worker ID.

        Returns:
            int: The number of distinct tasks executed by the worker.
        """
        if worker not in self._distinct_tasks_memo:
            distinct_tasks = set()
            for solution in self.period_solutions:
                if solution is not None:
                    station: int = solution.find_station_for_worker(worker)  # type: ignore
                    tasks_for_worker: List[int] = solution.station_tasks_assignment.get(
                        station, []
                    )
                    distinct_tasks.update(tasks_for_worker)

            self._distinct_tasks_memo[worker] = len(distinct_tasks)

        return self._distinct_tasks_memo[worker]

    def calculate_total_distinct_tasks(self) -> int:
        """
        Calculates the total number of distinct tasks executed by all workers.

        Returns:
            int: The total number of distinct tasks executed.
        """
        total_tasks = sum(
            self.calculate_worker_distinct_tasks(worker)
            for worker in self.period_solutions[0].workers  # type: ignore
            if self.period_solutions[0] is not None
        )
        return total_tasks

    def get_average_cycle_time(self) -> float:
        """
        Calculates the average cycle time across all periods.

        Returns:
            float: The average cycle time of the solutions in all periods.
        """
        total_cycle_time = 0.0
        count = 0

        for solution in self.period_solutions:
            if solution is not None:
                total_cycle_time += solution.get_max_cycle_time()
                count += 1

        return total_cycle_time / count if count > 0 else 0.0

    def copy(self) -> "JobRotationAlwabpSolution":
        """Creates a copy of the current JobRotationAlwabpSolution."""
        copy_solution = JobRotationAlwabpSolution(
            self.number_of_periods, self.lp_execution_data
        )
        copy_solution.period_solutions = [
            solution.copy() if solution else None for solution in self.period_solutions
        ]
        return copy_solution

    def decompose_solution(self, k: int):
        """Not implemented for JobRotationAlwabpSolution."""
        raise NotImplementedError("Decomposition is not supported.")

    def merge_solutions(self, solutions):
        """Not implemented for JobRotationAlwabpSolution."""
        raise NotImplementedError("Merging is not supported.")

    def solution_hash(self) -> int:
        """Generates a hash for the solution based on period assignments."""
        return hash(tuple(self.period_solutions))

    def solution_diff(self, other: "Solution") -> float:
        """Not implemented for JobRotationAlwabpSolution."""
        raise NotImplementedError("Solution diff is not supported.")

    def validade_aspects(self) -> bool:
        """Validates specific aspects of the solution."""
        return all(self.period_solutions)

    def reset(self) -> None:
        """Resets the solution to its initial state."""
        self.period_solutions = [None] * self.number_of_periods
        self._distinct_tasks_memo.clear()

    def narrow_bounds(self) -> None:
        """Not implemented for JobRotationAlwabpSolution."""
        pass

    def fix_solution(self) -> None:
        """Not implemented for JobRotationAlwabpSolution."""
        pass

    def __str__(self) -> str:
        """Gets a string representation of the solution."""

        result = [Util.line()]
        result.append("Job Rotation ALWABP Solution:")
        result.append(f"ID: {self.id}")
        result.append(f"{self.lp_execution_data}")
        result.append(f"Number of Distinct Tasks:")

        workers = self.period_solutions[0].workers if self.period_solutions[0] else []
        for w in workers:
            result.append(f"    Worker {w}: {self.calculate_worker_distinct_tasks(w)}")
        result.append(f"    Total: {self.calculate_total_distinct_tasks()}")

        result.append(f"Average Cycle Time: {str(int(self.get_average_cycle_time()))}")
        result.append(Util.line())
        for i, sol in enumerate(self.period_solutions):
            result.append(f"Period {i + 1}:\n{sol}")
        return "\n".join(result)

    def to_dict(self) -> dict:
        """
        Converts the solution data into a dictionary format.

        Returns:
            dict: A structured dictionary representing the Job Rotation ALWABP solution.
        """

        solution_dict = super().to_dict()

        solution_dict.update(
            {
                "lp_execution_data": self.lp_execution_data.to_dict(),
                "distinct_tasks_per_worker": {
                    worker: self.calculate_worker_distinct_tasks(worker)
                    for worker in (
                        self.period_solutions[0].workers
                        if self.period_solutions[0]
                        else []
                    )
                },
                "total_distinct_tasks": self.calculate_total_distinct_tasks(),
                "average_cycle_time": self.get_average_cycle_time(),
                "period_solutions": [
                    solution.to_dict() if solution is not None else None
                    for solution in self.period_solutions
                ],
            }
        )

        return solution_dict
