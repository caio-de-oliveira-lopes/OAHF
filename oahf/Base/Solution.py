from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy

from oahf.Base.Entity import Entity


class Solution(Entity, ABC):
    def __init__(self) -> None:
        super().__init__()  # Call the constructor of the Entity class
        self.print_solution_updates = True
        self.name = "Solution"

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

    @property
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
    def validate_aspects(self, update: bool = True) -> bool:
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
            return self.solution_hash == obj.solution_hash
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

    def to_random_keys(self) -> List[float]:
        """
        Converts the current solution into a random-keys representation suitable for BRKGA.

        Returns:
            List[float]: A list of random keys representing the solution.
        """
        random_keys = []
        return random_keys

    def from_random_key(
        self,
        random_keys: numpy.ndarray,
        local_seach: Optional["MetaHeuristic"],
        evaluator: "Evaluator",
        decoder_stop_criteria: Optional["StopCriteria"],
        destination_pool: Optional["Pool"],
        calling_mh: Optional["MetaHeuristic"]
    ) -> "Solution":
        """
        Reconstructs the solution from a random-keys representation.

        Args:
            random_keys (List[float]): A list of random keys representing the solution.

        Returns:
            Solution: A reconstructed solution.
        """
        new_solution = self.copy()
        new_solution.reset()
        return new_solution

    @classmethod
    def update_intensification_diversification_structures(
        cls, solution: "Solution"
    ) -> None:
        pass

    @classmethod
    def reset_intensification_diversification_structures(cls) -> None:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict, base_solution: "Solution") -> "Solution":
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    def __hash__(self) -> int:
        """
        Generates a hash for the solution based on its `solution_hash()` method.

        Returns:
            int: The hash value of the solution.
        """
        return self.solution_hash

    def find_move_to(self, other_solution: "Solution") -> "Movement":
        """
        Computes the necessary movements to transform the current solution into another solution
        by identifying differences.

        Parameters:
        - other_solution (Solution): The target solution to transform into.

        Returns:
        - Movement: The movement needed to transition to `other_solution`.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    @classmethod
    def generate_random_keys(
        cls, thread_id: int, example_solution: "Solution", population_size: int
    ) -> List[List[float]]:
        """
        Generates a population of random keys.

        Args:
            thread_id (int): Thread identifier for random number generation.
            example_sol (Solution): Problem instance.
            population_size (int): Number of individuals in the population.

        Returns:
            List[List[float]]: A population of randomly generated keys.
        """
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )
