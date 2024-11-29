from typing import Iterable

from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase import AlwabpEvaluation


class TasksUnassignedStopCriteria(StopCriteria):
    def __init__(self, num_unassigned_tasks: int) -> None:
        super().__init__()
        self.num_unassigned_tasks = num_unassigned_tasks

    def stop(self) -> bool:
        """Determines whether the stopping criteria have been met."""
        return super().stop()

    def stop_on_evaluations(self, evaluations: Iterable["AlwabpEvaluation"]) -> bool:
        """Checks if the stopping criteria are met based on evaluations.

        Args:
            evaluations (Iterable[Evaluation]): The evaluations to check against.

        Returns:
            bool: True if stopping criteria are met; otherwise, False.
        """
        return any(
            evaluation.num_unassigned_tasks <= self.num_unassigned_tasks
            for evaluation in list(evaluations)
        )

    def copy(self) -> "TasksUnassignedStopCriteria":
        """Creates a copy of the stop criteria instance."""
        return TasksUnassignedStopCriteria(self.num_unassigned_tasks)
