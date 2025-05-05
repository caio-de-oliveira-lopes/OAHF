from typing import Iterator, List, Optional

from oahf.Base import MetaHeuristic
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution


class ListPool(Pool):
    def __init__(
        self,
        solutions: List[Solution] = [],
        heuristic_parser_key: Optional[int] = None,
        evaluator: Optional[Evaluator] = None,
    ):
        super().__init__(solutions, heuristic_parser_key, evaluator)
        self.name = "ListPool"

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
        new_pool = ListPool(
            [sol.copy() for sol in self.solutions], self.heuristic_parser_key
        )
        new_pool.evaluator = self.evaluator
        return new_pool

    def add_solution(
        self,
        solution: Optional[Solution],
        mh: Optional[MetaHeuristic],
        only_feasible: bool = True,        
        line_number: Optional[int] = None
    ) -> bool:
        """Add a solution to the pool."""
        return super().add_solution(solution, mh, only_feasible, line_number)

    def get_list(self) -> List[Solution]:
        """Get a list of solutions in the pool."""
        return self.solutions

    @classmethod
    def from_dict(
        cls, heuristic_parser: "HeuristicParser", data: dict, base_solution: Solution
    ) -> "ListPool":
        """
        Creates an instance of the ListPool class from a dictionary.

        Args:
            data (dict): A dictionary representing the ListPool.

        Returns:
            ListPool: An instance of the ListPool class populated with data from the dictionary.
        """

        from oahf.MetaHeuristicsParser.HeuristicParser import HeuristicParser

        if not isinstance(heuristic_parser, HeuristicParser):
            raise ValueError(
                f"Unavailable Heuristic Parser when trying to parse pool: {data.get('id')}"
            )

        # Populate the solutions list
        solutions = data.get("solutions", [])
        parsed_solutions = [
            type(base_solution).from_dict(sol, base_solution) for sol in solutions
        ]

        instance = ListPool(parsed_solutions, heuristic_parser_key=data.get("id"))

        # Populate specific attributes
        instance._solution_info = data.get("solution_info", [])
        instance.evaluator = heuristic_parser.parse_evaluator(data.get("evaluator", {}))

        return instance
