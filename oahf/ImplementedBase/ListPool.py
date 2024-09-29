from typing import Iterator, List

from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution


class ListPool(Pool):
    def __init__(self):
        """Initializes a ListPool with an empty list of solutions."""
        super().__init__()
        self._list: List[Solution] = []

    def any(self) -> bool:
        """Returns True if there are any solutions in the pool, False otherwise."""
        return bool(self._list)

    def copy(self) -> "ListPool":
        """Creates a copy of the current pool."""
        new_pool = ListPool()
        new_pool._list = [sol.copy() for sol in self._list]
        return new_pool

    def count(self) -> int:
        """Returns the number of solutions in the pool."""
        return len(self._list)

    def __iter__(self) -> Iterator[Solution]:
        """Returns an iterator over the solutions in the pool."""
        return iter(self._list)

    def get_solution_at(self, index: int) -> Solution:
        """Returns the solution at the specified index."""
        return self._list[index]

    def add_solution(self, sol: Solution) -> bool:
        """Adds a solution to the pool."""
        self._list.append(sol)
        return True

    def clear(self) -> bool:
        """Clears the pool."""
        self._list.clear()
        return True

    def get_list(self) -> List[Solution]:
        """Returns a list of solutions in the pool."""
        return self._list.copy()
