from typing import List, Optional

from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class JobRotationAlwabpSolution(Solution):
    def __init__(self, number_of_periods: int):
        super().__init__()
        self.number_of_periods = number_of_periods
        self.period_solutions: List[Optional[AlwabpSolution]] = [
            None
        ] * number_of_periods  # List to hold solutions for each period

    def assign_solution_to_period(self, period: int, solution: AlwabpSolution):
        """
        Assigns an AlwabpSolution to a specific period.

        Args:
            period (int): The period index.
            solution (AlwabpSolution): The solution to assign.
        """
        if 0 <= period < self.number_of_periods:
            self.period_solutions[period] = solution

    def copy(self) -> "JobRotationAlwabpSolution":
        """Creates a copy of the current JobRotationAlwabpSolution."""
        copy_solution = JobRotationAlwabpSolution(self.number_of_periods)
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

    def narrow_bounds(self) -> None:
        """Not implemented for JobRotationAlwabpSolution."""
        pass

    def fix_solution(self) -> None:
        """Not implemented for JobRotationAlwabpSolution."""
        pass

    def __str__(self) -> str:
        """Gets a string representation of the solution."""
        result = ["JobRotationAlwabpSolution:"]
        for i, sol in enumerate(self.period_solutions):
            result.append(f"Period {i + 1}: {sol}")
        return "\n".join(result)
