from typing import Optional, Sequence

from oahf.Base.Movement import Movement
from oahf.Base.Solution import Solution


class MultipleMovement(Movement):
    def __init__(
        self,
        solution: "Solution",
        movements: Sequence[Movement],
        override_cost: Optional[float] = None,
    ):
        super().__init__(solution)
        self.movements: Sequence[Movement] = movements
        self.override_cost: Optional[float] = override_cost
        # Cache the hash of movements to avoid recomputation
        self._movements_hash: Optional[int] = None

    def get_cost(self) -> float:
        """Calculate the total cost of all movements or return the overridden cost if specified."""
        if self.override_cost is not None:
            return self.override_cost
        return sum(movement.get_cost() for movement in self.movements)

    def apply(self) -> bool:
        """Apply each movement and return whether all movements were successful."""
        for movement in self.movements:
            if not movement.apply_operation():
                return False
        return True

    def unapply(self) -> bool:
        """Unapply each movement in reverse order and return whether all movements were successfully unapplied."""
        for movement in reversed(self.movements):
            if not movement.unapply_operation(None):
                return False
        return True

    def set_unapply_inconsistent(self):
        """Override this method as it is not implemented in this class."""
        raise NotImplementedError("Subclasses must implement this method.")

    def copy(self, new_solution: Optional["Solution"] = None) -> "MultipleMovement":
        """
        Creates a copy of the current MultipleMovement, optionally replacing the solution.

        Args:
            new_solution (Optional[Solution]): A new solution to associate with the copied movements.
                If not provided, the current solution is used.

        Returns:
            MultipleMovement: A new instance of MultipleMovement with the same attributes,
            but optionally associated with a new solution.
        """
        # Use the provided solution or retain the current one
        solution_to_use = new_solution if new_solution else self.solution

        # Copy each movement, passing the new solution if applicable
        copied_movements = [
            movement.copy(new_solution=solution_to_use) for movement in self.movements
        ]

        # Create a new instance of MultipleMovement with copied movements
        copied_multiple_movement = MultipleMovement(
            solution=solution_to_use,
            movements=copied_movements,
            override_cost=self.override_cost,
        )
        copied_multiple_movement._movements_hash = self._movements_hash

        return copied_multiple_movement

    def __eq__(self, other: object) -> bool:
        """
        Check equality between two MultipleMovement instances.

        Args:
            other (object): The other instance to compare.

        Returns:
            bool: True if equal, False otherwise.
        """
        if not isinstance(other, MultipleMovement):
            return False
        return (
            self.override_cost == other.override_cost
            and self.movements == other.movements
        )

    def _compute_movements_hash(self) -> int:
        """Helper method to compute the hash of the movements."""
        return hash(
            tuple(self.movements)
        )  # Or use another hashing method for the list.

    def __hash__(self) -> int:
        if self._movements_hash is None:
            self._movements_hash = self._compute_movements_hash()

        return hash((self.override_cost, self._movements_hash))
