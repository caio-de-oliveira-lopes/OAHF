from typing import Iterable, List, Optional

from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Evaluation import Evaluation
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class AlwabpEvaluation(Evaluation):
    def __init__(self, constraints: Iterable["ConstraintEvaluation"], max_cycle_time: float):
        """
        Initializes the Alwabp Evaluation object with constraints.
        :param constraints: Iterable of ConstraintEvaluation objects.
        """
        super().__init__(constraints)
        self._max_cycle_time = max_cycle_time

    def get_objective_function_value(self) -> float:
        """
        Method to get the objective function value.
        """
        return self._max_cycle_time

    def get_objective_function(self) -> float:
        """
        Calculates the objective function value, including penalties for constraints.
        :return: The objective function value.
        """
        return self.get_objective_function_value() + sum(
            x.penalty for x in self.constraints if self.constraints
        )