from abc import ABC, abstractmethod
from typing import Iterable

from oahf.Base.Evaluation import Evaluation
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase import AlwabpEvaluation


class CompleteAssignmentStopCriteria(StopCriteria):
    def __init__(self) -> None:
        super().__init__()

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
        return any(evaluation.completed_assignment() for evaluation in list(evaluations))
    
    def copy(self) -> "CompleteAssignmentStopCriteria":
        """Creates a copy of the stop criteria instance."""
        return CompleteAssignmentStopCriteria()
