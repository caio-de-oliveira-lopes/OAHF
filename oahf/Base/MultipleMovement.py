from typing import List, Optional

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Movement import Movement
from oahf.Base.Solution import Solution


class MultipleMovement(Movement):
    def __init__(
        self,
        solution: "Solution",
        report: "EfficiencyReport",
        movements: List[Movement],
        override_cost: Optional[float] = None,
    ):
        super().__init__(solution, report)
        self.movements: List[Movement] = movements
        self.override_cost: Optional[float] = override_cost

    def get_cost(self) -> float:
        """Calculate the total cost of all movements or return the overridden cost if specified."""
        if self.override_cost is not None:
            return self.override_cost
        return sum(movement.get_cost() for movement in self.movements)

    def apply(self) -> bool:
        """Apply each movement and return whether any movement was successful."""
        worked = False
        for movement in self.movements:
            worked = movement.apply_operation() or worked
        return worked

    def unapply(self) -> bool:
        """Unapply each movement in reverse order and return whether any movement was successfully unapplied."""
        worked = False
        for movement in reversed(self.movements):
            worked = movement.unapply_operation(None) or worked
        return worked

    def set_unapply_inconsistent(self):
        """Override this method as it is not implemented in this class."""
        pass
