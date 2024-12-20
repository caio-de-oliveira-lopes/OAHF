from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from oahf.Utils.Util import Util

from oahf.Base.Entity import Entity


class Solution(Entity, ABC):
    def __init__(self) -> None:
        super().__init__()  # Call the constructor of the Entity class
        self.print_solution_updates = False

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
    def validade_aspects(self) -> bool:
        """
        Validates specific aspects of the solution.

        Returns:
            bool: True if all aspects are valid, False otherwise.
        """
        return True

    @abstractmethod
    def reset(self) -> None:
        """
        Resets the solution to its initial state.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @abstractmethod
    def narrow_bounds(self) -> None:
        """
        Narrows the bounds of the solution, if applicable.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @abstractmethod
    def fix_solution(self) -> None:
        """
        Applies adjustments to fix inconsistencies in the solution.
        Like a final sort method or something like it.
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

    def set_print_solution_updates(self, print_solution_updates: bool) -> None:
        """
        Configures whether solution updates should be printed.

        Args:
            print_solution_updates (bool): A flag indicating whether to enable or disable
                                           printing solution updates.
        """
        self.print_solution_updates = print_solution_updates

    def print_update(self, update_message: str) -> None:
        """
        Prints an update message if printing solution updates is enabled.

        Args:
            update_message (str): The message to be printed as an update.
        """
        if self.print_solution_updates:
            print(update_message)