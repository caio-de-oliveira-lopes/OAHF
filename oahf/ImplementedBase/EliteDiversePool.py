from typing import Callable, Iterator, List, Optional

from oahf.Base.Evaluator import Evaluator
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution


class EliteDiversePool(Pool):
    def __init__(
        self,
        limit_size: int,
        diversity_weight: float,
        evaluator: Evaluator,
        action_on_add: Optional[Callable[[Solution], None]] = None,
    ):
        """
        Initializes an EliteDiversePool with specified limit size, diversity weight, and evaluator.

        :param limit_size: Maximum number of solutions in the pool.
        :param diversity_weight: Weight to apply for diversity in evaluations.
        :param evaluator: Evaluator used to evaluate solutions.
        :param action_on_add: Optional action to perform when a solution is added.
        """
        super().__init__()
        self._list: List[Solution] = []
        self.limit = limit_size
        self.evaluator = evaluator
        self.diversity_weight = diversity_weight
        self.best_objective_function = float("inf")
        self.eval_and_diversity = [0.0] * limit_size
        self.action_on_add = action_on_add
        self.worst_sol_index = 0

    def any(self) -> bool:
        """Returns True if there are any solutions in the pool, False otherwise."""
        return bool(self._list)

    def copy(self) -> "EliteDiversePool":
        """Creates a copy of the current pool."""
        new_pool = EliteDiversePool(self.limit, self.diversity_weight, self.evaluator)
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

    def update_eval_diversity_values(self) -> None:
        """Updates evaluation and diversity values for the pool."""
        worst_eval = float("-inf")
        worst_index = 0
        for i in range(len(self._list)):
            summed_diversity = 0.0
            eval2 = self.evaluator.evaluate(self._list[i])
            for j in range(len(self._list)):
                if i != j:
                    summed_diversity += self._list[i].solution_diff(self._list[j])
            self.eval_and_diversity[i] = (
                eval2.get_objective_function() / self.best_objective_function
                - 1
                - summed_diversity / (len(self._list) - 1) * self.diversity_weight
            )
            if (
                self.eval_and_diversity[i] > worst_eval
                and abs(self.best_objective_function - eval2.get_objective_function())
                > 1e-4
            ):
                worst_eval = self.eval_and_diversity[i]
                worst_index = i
        self.worst_sol_index = worst_index

    def calculate_expected_eval_diversity(self, sol: Solution) -> float:
        """Calculates the expected evaluation and diversity for a given solution."""
        summed_diversity = 0.0
        eval2 = self.evaluator.evaluate(sol)
        if eval2.get_objective_function() < self.best_objective_function:
            return float("-inf")
        count_sum = 0
        for j in range(len(self._list)):
            if sol.solution_hash() == self._list[j].solution_hash():
                return float("inf")
            if len(self._list) != self.limit or j != self.worst_sol_index:
                summed_diversity += sol.solution_diff(self._list[j])
                count_sum += 1
        value = (
            eval2.get_objective_function() / self.best_objective_function
            - 1
            - summed_diversity / count_sum * self.diversity_weight
        )
        return value

    def update_when_add(self, sol: Solution) -> None:
        """Updates the pool state when a solution is added."""
        eval_value = self.evaluator.evaluate(sol).get_objective_function()
        print(eval_value)
        if eval_value < self.best_objective_function:
            if self.action_on_add:
                self.action_on_add(sol)
                eval_value = self.evaluator.evaluate(sol).get_objective_function()
            self.best_objective_function = eval_value
        if len(self._list) == self.limit:
            self.update_eval_diversity_values()

    def add_solution(self, sol: Solution) -> bool:
        """Attempts to add a solution to the pool."""
        added = False
        if len(self._list) < self.limit:
            self._list.append(sol)
            added = True
        else:
            value = self.calculate_expected_eval_diversity(sol)
            if value < self.eval_and_diversity[self.worst_sol_index]:
                self._list.pop(self.worst_sol_index)
                self._list.append(sol)
                added = True
        if added:
            self.update_when_add(sol)
        return added

    def clear(self) -> bool:
        """Clears the pool."""
        self._list.clear()
        return True

    def get_list(self) -> List[Solution]:
        """Returns a list of solutions in the pool."""
        return self._list.copy()
