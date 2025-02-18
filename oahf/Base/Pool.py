import inspect
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional

from oahf.Base.Entity import Entity
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Solution import Solution


class Pool(Entity, ABC):
    def __init__(
        self,
        solutions: List[Solution] = [],
        heuristic_parser_key: Optional[int] = None,
        evaluator: Optional[Evaluator] = None,
    ):
        super().__init__()
        self.solutions: List[Solution] = solutions.copy()
        self.evaluator = evaluator
        self.name = "Pool"
        self.heuristic_parser_key = heuristic_parser_key

        if self.heuristic_parser_key is not None:
            self.output_id = self.heuristic_parser_key

        # key must be the solution ID and value will be composed of keys "metaheuristic" and "execution_time":
        self._solution_info: Dict[int, Dict[str, str]] = {}
        # Use a set to quickly test whether a solution is already present.
        # This assumes that the Solution class correctly implements __hash__ and __eq__.
        self._solution_set: set[Solution] = set(solutions)

    @abstractmethod
    def get_solution_at(self, index: int) -> Solution:
        """Get a solution at the specified index."""
        return self.solutions[index]

    @abstractmethod
    def __iter__(self) -> Iterator[Solution]:
        """Return an iterator for the pool."""
        return iter(self.solutions)

    @abstractmethod
    def count(self) -> int:
        """Get the number of solutions in the pool."""
        return len(self.solutions)

    @abstractmethod
    def any(self) -> bool:
        """Check if there are any solutions in the pool."""
        return bool(self.solutions)

    @abstractmethod
    def clear(self) -> bool:
        """Clear all solutions from the pool."""
        self.solutions.clear()
        return True

    @abstractmethod
    def copy(self) -> "Pool":
        """Create a copy of the pool."""
        new_pool = self.__class__([], self.heuristic_parser_key)
        new_pool.solutions = self.solutions.copy()
        return new_pool

    @abstractmethod
    def get_list(self) -> List[Solution]:
        """Get a list of solutions in the pool."""
        return self.solutions

    @abstractmethod
    def add_solution(self, solution: Optional[Solution]) -> bool:
        """Add a solution to the pool (to be implemented by subclasses).

        Tracks the most recent MetaHeuristic subclass that called this method.
        """
        
        from oahf.Base.MetaHeuristic import MetaHeuristic
        from oahf.Utils.Util import Util
        
        if solution is None or solution in self._solution_set:
            return False

        # Use a more efficient stack traversal (f_back) to find the MetaHeuristic caller.
        frame = inspect.currentframe()
        while frame:
            instance = frame.f_locals.get("self")
            if instance and isinstance(instance, MetaHeuristic):
                if solution.id not in self._solution_info:
                    self._solution_info[solution.id] = {}
                self._solution_info[solution.id]["metaheuristic"] = type(instance).__name__
                self._solution_info[solution.id]["execution_time"] = Util.get_duration_from_start_timestamp()
                break
            frame = frame.f_back

        # Append solution and add it to the lookup set.
        self.solutions.append(solution)
        self._solution_set.add(solution)
        return True

    def get_best(self, evaluator: Optional[Evaluator] = None) -> Optional[Solution]:
        """
        Get the best solution from the pool based on evaluation.
        The evaluator is optional, if the pool already has it`s own evaluator, it`ll be used if None is passed.
        """

        evaluator = evaluator or self.evaluator

        if evaluator:
            if self.any():
                best = self.get_solution_at(0)
                best_eval = evaluator.evaluate(best)
                for solution in self:
                    new_eval = evaluator.evaluate(solution)
                    if new_eval.better_than(best_eval):
                        best = solution
                        best_eval = new_eval
                return best
        return None

    def to_dict(self) -> dict:
        """
        Converts the pool data into a dictionary format.

        Returns:
            dict: A structured dictionary representing the Pool.
        """

        pool_dict = super().to_dict()
        pool_dict["id"] = self.heuristic_parser_key

        pool_dict.update(
            {
                "pool_size": self.count(),
                "solution_info": self._solution_info,
                "solutions": [solution.to_dict() for solution in self.get_list()],
            }
        )

        return pool_dict

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Pool":
        """
        Creates an instance of the Pool class from a dictionary.

        Args:
            data (dict): A dictionary representing the Pool.

        Returns:
            Pool: An instance of the Pool class populated with data from the dictionary.
        """
        
        raise NotImplementedError