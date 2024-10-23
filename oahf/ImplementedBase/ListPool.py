from typing import Iterator, List

from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution


class ListPool(Pool):
    def get_solution_at(self, index: int) -> Solution:
        """Get the solution at the specified index."""
        return self.solutions[index]

    def __iter__(self) -> Iterator[Solution]:
        """Return an iterator over the solutions in the pool."""
        return iter(self.solutions)

    def count(self) -> int:
        """Get the number of solutions in the pool."""
        return len(self.solutions)

    def any(self) -> bool:
        """Check if there are any solutions in the pool."""
        return bool(self.solutions)

    def clear(self) -> bool:
        """Clear all solutions from the pool."""
        self.solutions.clear()
        return True

    def copy(self) -> "ListPool":
        """Create a copy of the pool."""
        new_pool = ListPool()
        new_pool.solutions = [sol.copy() for sol in self.solutions]
        return new_pool

    def add_solution(self, solution: Solution) -> bool:
        """Add a solution to the pool."""
        if solution not in self.solutions:
            self.solutions.append(solution)
            return True
        return False

    def get_list(self) -> List[Solution]:
        """Get a list of solutions in the pool."""
        return self.solutions
