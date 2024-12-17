from typing import Iterable

from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Evaluation import Evaluation
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution


class JobRotationAlwabpEvaluation(Evaluation):
    def __init__(
        self,
        constraints: Iterable["ConstraintEvaluation"],
        total_distinct_tasks: int,
        average_cycle_time: float,
    ):
        """
        Initializes the JobRotationAlwabpEvaluation object.

        Args:
            constraints (List[ConstraintEvaluation]): List of constraint evaluations.
            total_distinct_tasks (int): Total distinct tasks of the JobRotationAlwabpSolution evaluated.
            average_cycle_time (float): Average cycle time of the JobRotationAlwabpSolution evaluated.
        """
        super().__init__(constraints)
        self._total_distinct_tasks = total_distinct_tasks
        self._average_cycle_time = average_cycle_time

    def get_objective_function_value(self) -> float:
        """
        Method to get the objective function value.
        """
        return self._total_distinct_tasks

    def better_than(self, ev: "Evaluation") -> bool:
        """
        Determines if the current evaluation is better than another.

        Args:
            other (JobRotationAlwabpEvaluation): Another evaluation object.

        Returns:
            bool: True if current evaluation is better, otherwise False.
        """
        if not isinstance(ev, JobRotationAlwabpEvaluation):
            return super().better_or_equal_to(ev)

        if self.infeasible() and not ev.infeasible():
            return False
        if not self.infeasible() and ev.infeasible():
            return True
        return self.get_objective_function() > ev.get_objective_function() or (
            self.get_objective_function() == ev.get_objective_function()
            and self._average_cycle_time < ev._average_cycle_time
        )

    def better_or_equal_to(self, ev: "Evaluation") -> bool:
        """
        Determines if the current evaluation is better than or equal to another.

        Args:
            other (JobRotationAlwabpEvaluation): Another evaluation object.

        Returns:
            bool: True if current evaluation is better or equal, otherwise False.
        """
        if not isinstance(ev, JobRotationAlwabpEvaluation):
            return super().better_or_equal_to(ev)

        if self.infeasible() and not ev.infeasible():
            return False
        if not self.infeasible() and ev.infeasible():
            return True
        return self.get_objective_function() > ev.get_objective_function() or (
            self.get_objective_function() == ev.get_objective_function()
            and self._average_cycle_time <= ev._average_cycle_time
        )
