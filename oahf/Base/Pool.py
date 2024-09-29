from abc import ABC, abstractmethod
from typing import Iterator, List, Optional, Tuple

from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Entity import Entity
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Solution import Solution
from oahf.Base.ThreadManager import ThreadManager


class PoolEventReport:
    def __init__(
        self,
        accepted: bool,
        objective_function: float,
        diversity: float,
        constraints: List[ConstraintEvaluation],
    ):
        self.accepted = accepted
        self.constraints = constraints
        self.objective_function = objective_function
        self.diversity = diversity


class PoolReport:
    def __init__(self):
        self.events: List[Tuple[int, PoolEventReport]] = []
        self.name: str = ""
        self.id: int = 0


class Pool(Entity, ABC):
    def __init__(self):
        super().__init__()
        self.report = PoolReport()

    @abstractmethod
    def get_solution_at(self, index: int) -> Solution:
        """Get a solution at the specified index."""
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[Solution]:
        """Return an iterator for the pool."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Get the number of solutions in the pool."""
        pass

    @abstractmethod
    def any(self) -> bool:
        """Check if there are any solutions in the pool."""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all solutions from the pool."""
        pass

    @abstractmethod
    def copy(self) -> "Pool":
        """Create a copy of the pool."""
        pass

    def add(self, solution: Solution, evaluator: Evaluator) -> bool:
        """Add a solution to the pool and evaluate it."""
        accepted = self.add_solution(solution)
        eval = evaluator.evaluate(solution)
        diversity = 0.0  # Assuming diversity calculation logic will be added
        self.report.events.append(
            (
                ThreadManager.watch.elapsed_milliseconds,
                PoolEventReport(
                    accepted,
                    eval.get_objective_function(),
                    diversity,
                    eval.get_infeasible_constraints(),
                ),
            )
        )
        return accepted

    def get_report(self) -> PoolReport:
        """Get the report of the pool."""
        self.report.name = self.__class__.__name__
        return self.report

    @abstractmethod
    def add_solution(self, solution: Solution) -> bool:
        """Add a solution to the pool (to be implemented by subclasses)."""
        pass

    @abstractmethod
    def get_list(self) -> List[Solution]:
        """Get a list of solutions in the pool."""
        pass

    def get_best(self, evaluator: Evaluator) -> Optional[Solution]:
        """Get the best solution from the pool based on evaluation."""
        if self.any():
            best = self.get_solution_at(0)
            best_eval = evaluator.evaluate(best)
            for x in self:
                new_eval = evaluator.evaluate(x)
                if new_eval.better_than(best_eval):
                    best = x
                    best_eval = new_eval
            return best
        return None
