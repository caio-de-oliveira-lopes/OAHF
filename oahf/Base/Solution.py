from abc import ABC, abstractmethod
from typing import List, Optional

from oahf.Base.Entity import Entity


class Solution(Entity, ABC):
    def __init__(self) -> None:
        super().__init__()  # Call the constructor of the Entity class

    @abstractmethod
    def copy(self) -> "Solution":
        """Creates a copy of the solution."""
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @abstractmethod
    def decompose_solution(self, k: int) -> Optional[List["Solution"]]:
        """Decomposes the solution into smaller parts.

        Args:
            k (int): The number of parts to decompose into.

        Returns:
            Optional[List[Solution]]: A list of decomposed solutions or None.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @abstractmethod
    def merge_solutions(self, solutions: List["Solution"]) -> "Solution":
        """Merges multiple solutions into one.

        Args:
            solutions (List[Solution]): A list of solutions to merge.

        Returns:
            Solution: The merged solution.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @abstractmethod
    def solution_hash(self) -> int:
        """Generates a hash for the solution.

        Returns:
            int: The hash value of the solution.
        """
        return hash(self)

    @abstractmethod
    def solution_diff(self, other: "Solution") -> float:
        """Calculates the difference between this solution and another.

        Args:
            other (Solution): The other solution to compare against.

        Returns:
            float: The difference between the two solutions.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @abstractmethod
    def __str__(self) -> str:
        """Gets a string representation of the solution.

        Returns:
            str: A string that represents the solution.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    def __eq__(self, obj: "Solution") -> bool:
        """
        Overrides the equality comparison method to compare solutions.
        Supports comparison between instances of the same class/subclasses.

        Args:
            obj (Solution): The other solution to compare against.

        Returns:
            bool: True if objects have the same type and hash.
        """
        if isinstance(obj, self.__class__):
            return self.solution_hash() == obj.solution_hash()
        return False
