from typing import Iterable, List, Optional

from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Entity import Entity


class Evaluation(Entity):
    def __init__(self, constraints: Iterable["ConstraintEvaluation"]):
        """
        Initializes the Evaluation object with constraints.
        :param constraints: Iterable of ConstraintEvaluation objects.
        """
        super().__init__()
        self.constraints: List["ConstraintEvaluation"] = list(constraints)
        self._infeasible_constraints: Optional[List["ConstraintEvaluation"]] = None

    def better_than(self, ev: "Evaluation") -> bool:
        """
        Determines if the current evaluation is better than another.
        :param ev: Another Evaluation object.
        :return: True if the current evaluation is better.
        """
        if self.infeasible() and not ev.infeasible():
            return False
        if not self.infeasible() and ev.infeasible():
            return True
        return self.get_objective_function() < ev.get_objective_function()

    def better_or_equal_to(self, ev: "Evaluation") -> bool:
        """
        Determines if the current evaluation is better than or equal to another.
        :param ev: Another Evaluation object.
        :return: True if the current evaluation is better or equal.
        """
        if self.infeasible() and not ev.infeasible():
            return False
        if not self.infeasible() and ev.infeasible():
            return True
        return self.get_objective_function() <= ev.get_objective_function()

    def get_infeasible_constraints(self) -> List["ConstraintEvaluation"]:
        """
        Retrieves the list of infeasible constraints.
        :return: List of infeasible ConstraintEvaluation objects.
        """
        if self._infeasible_constraints is None:
            self._infeasible_constraints = [x for x in self.constraints if x.infeasible]
        return self._infeasible_constraints

    def infeasible(self) -> bool:
        """
        Checks if the current evaluation has infeasible constraints.
        :return: True if there are infeasible constraints.
        """
        return bool(self.get_infeasible_constraints())

    def get_objective_function_value(self) -> float:
        """
        Virtual method to get the objective function value, can be overridden.
        :return: Default value is 0.0.
        """
        return 0.0

    def get_objective_function(self) -> float:
        """
        Calculates the objective function value, including penalties for constraints.
        :return: The objective function value.
        """
        return self.get_objective_function_value() + sum(
            x.penalty for x in self.constraints if self.constraints
        )

    def update_penalties(self) -> None:
        """
        Updates the penalty associated with the constraint type based on the current penalty value:
        - If the penalty is positive, the associated penalty for the constraint type is doubled.
        - If the penalty is zero, the associated penalty for the constraint type is halved.
        """
        for constraint in self.constraints:
            if constraint.penalty > 0:
                constraint.constraint_type().multiply_penalty(2)
            elif constraint.penalty == 0.0:
                constraint.constraint_type().multiply_penalty(0.5)
