from typing import Type
from oahf.Base.Constraint import Constraint
from oahf.Base.Entity import Entity

class ConstraintEvaluation(Entity):
    def __init__(self, constraint: 'Constraint', infeasibility: bool, penalty: float = 0.0):
        """
        Initializes a ConstraintEvaluation object.
        :param constraint: An instance of Constraint.
        :param infeasibility: Boolean indicating whether the constraint is infeasible.
        :param penalty: The penalty associated with the constraint (default is 0.0).
        """
        super().__init__()
        self._infeasible: bool = infeasibility
        self._penalty: float = penalty
        self._constraint_type: Type['Constraint'] = type(constraint)

    @property
    def infeasible(self) -> bool:
        """Returns whether the constraint is infeasible."""
        return self._infeasible

    @property
    def penalty(self) -> float:
        """Returns the penalty associated with the constraint."""
        return self._penalty

    @property
    def constraint_type(self) -> Type['Constraint']:
        """Returns the type of the constraint."""
        return self._constraint_type
