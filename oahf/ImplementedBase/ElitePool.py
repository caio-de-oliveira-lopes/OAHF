from typing import Iterator, List

from oahf.Base.Evaluation import Evaluation
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution


class ElitePool(Pool):
    def __init__(self, limit_size: int, evaluator: Evaluator):
        """
        Initializes an ElitePool with a specified limit size and evaluator.

        :param limit_size: Maximum number of solutions in the pool.
        :param evaluator: Evaluator used to evaluate solutions.
        """
        super().__init__()
        self._list: List[Solution] = []
        self.limit = limit_size
        self.worst_evaluation: Evaluation = None
        self.worst_sol_index: int = 0
        self.evaluator = evaluator

    def any(self) -> bool:
        """Returns True if there are any solutions in the pool, False otherwise."""
        return bool(self._list)

    def copy(self) -> "ElitePool":
        """Creates a copy of the current pool."""
        new_pool = ElitePool(self.limit, self.evaluator)
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
        """Attempts to add a solution to the pool."""
        if len(self._list) < self.limit:
            self._list.append(sol)
            return True
        else:
            if self.worst_evaluation is None:
                self.worst_evaluation = self.evaluator.evaluate(self._list[0])
                self.worst_sol_index = 0
                for i in range(1, self.limit):
                    eval2 = self.evaluator.evaluate(self._list[i])
                    if self.worst_evaluation.better_than(eval2):
                        self.worst_evaluation = eval2
                        self.worst_sol_index = i

            eval_sol = self.evaluator.evaluate(sol)
            if eval_sol.better_than(self.worst_evaluation):
                hash_sol = sol.solution_hash()
                if any(l.solution_hash() == hash_sol for l in self._list):
                    return False

                print(eval_sol)
                self._list.pop(self.worst_sol_index)
                self.worst_evaluation = None
                self._list.append(sol)
                return True
            return False

    def clear(self) -> bool:
        """Clears the pool."""
        self._list.clear()
        return True

    def get_list(self) -> List[Solution]:
        """Returns a list of solutions in the pool."""
        return self._list.copy()
