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
        max_possible_tasks: int
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
        self._max_possible_tasks = max_possible_tasks

    def get_objective_function_value(self) -> float:
        """
        Method to get the objective function value.
        """
        part_1 = (JobRotationAlwabpSolution._tasks_executed_factor / float(self._max_possible_tasks)) * self._total_distinct_tasks
        part_2 = (JobRotationAlwabpSolution._cycle_time_factor / JobRotationAlwabpSolution._current_alwabp_upper_bound) * self._average_cycle_time
        return part_1 - part_2

    def better_than(self, ev: "Evaluation") -> bool:
        """
        Determines if the current evaluation is better than another.

        Args:
            other (JobRotationAlwabpEvaluation): Another evaluation object.

        Returns:
            bool: True if current evaluation is better, otherwise False.
        """
        if not isinstance(ev, JobRotationAlwabpEvaluation):
            return super().better_than(ev)

        if self.infeasible() and not ev.infeasible():
            return False
        if not self.infeasible() and ev.infeasible():
            return True
        return self.get_objective_function() > ev.get_objective_function()

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
        return self.get_objective_function() >= ev.get_objective_function()