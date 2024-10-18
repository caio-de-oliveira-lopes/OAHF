from abc import ABC, abstractmethod
from typing import List, Optional, Type

from oahf.Base.Entity import Entity


class Solution(Entity, ABC):
    def __init__(self) -> None:
        super().__init__()  # Call the constructor of the Entity class

    @abstractmethod
    def copy(self) -> "Solution":
        """Creates a copy of the solution."""
        pass

    @abstractmethod
    def decompose_solution(self, k: int) -> Optional[List["Solution"]]:
        """Decomposes the solution into smaller parts.

        Args:
            k (int): The number of parts to decompose into.

        Returns:
            Optional[List[Solution]]: A list of decomposed solutions or None.
        """
        return None

    @abstractmethod
    def merge_solutions(self, solutions: List["Solution"]) -> "Solution":
        """Merges multiple solutions into one.

        Args:
            solutions (List[Solution]): A list of solutions to merge.

        Returns:
            Solution: The merged solution.
        """
        return None

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
        pass

    @abstractmethod
    def solution_string_representation(self) -> str:
        """Gets a string representation of the solution.

        Returns:
            str: A string that represents the solution.
        """
        pass
    
    def __eq__(self, obj: "Solution") -> bool:
        """
        Overrides the equality comparison method to compare solutions based on their solution hash.
        Supports comparison between instances of the same class or its subclasses.

        Args:
            obj (Solution): The other solution to compare against.

        Returns:
            bool: True if both objects have the same type (including subclasses) and same solution hash, False otherwise.
        """
        if isinstance(obj, self.__class__):
            return self.solution_hash() == obj.solution_hash()
        return False
