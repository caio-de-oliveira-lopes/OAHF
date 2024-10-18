from typing import Iterable, List, Optional

from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Evaluation import Evaluation
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class AlwabpEvaluation(Evaluation):
    def __init__(self, constraints: Iterable["ConstraintEvaluation"], max_cycle_time: float, num_unassigned_tasks: int, num_unassigned_workers: int):
        """
        Initializes the Alwabp Evaluation object with constraints.
        :param constraints: Iterable of ConstraintEvaluation objects.
        """
        super().__init__(constraints)
        self._max_cycle_time = max_cycle_time
        self._num_unassigned_tasks = num_unassigned_tasks
        self._num_unassigned_workers = num_unassigned_workers

    @property
    def num_unassigned_tasks(self) -> int:
        return self._num_unassigned_tasks    
    
    @property
    def num_unassigned_workers(self) -> int:
        return self._num_unassigned_workers
    
    def completed_assignment(self) -> bool:
        return not (self._num_unassigned_tasks or self._num_unassigned_workers)

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