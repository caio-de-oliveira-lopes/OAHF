from typing import Iterable

from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase import AlwabpEvaluation


class MaxCycleTimeStopCriteria(StopCriteria):
    def __init__(self, cycle_time_limit: int) -> None:
        """Initializes the stop criteria with a cycle time limit."""
        super().__init__()
        self.cycle_time_limit = cycle_time_limit

    def stop(self) -> bool:
        """Determines whether the stopping criteria have been met."""
        return super().stop()

    def stop_on_evaluations(self, evaluations: Iterable["AlwabpEvaluation"]) -> bool:
        """Checks if the stopping criteria are met based on evaluations.

        Args:
            evaluations (Iterable[AlwabpEvaluation]): The evaluations to check against.

        Returns:
            bool: True if stopping criteria are met; otherwise, False.
        """
        return any(
            evaluation.cycle_time_limit > self.cycle_time_limit
            for evaluation in list(evaluations)
        )

    def copy(self) -> "MaxCycleTimeStopCriteria":
        """Creates a copy of the stop criteria instance."""
        return MaxCycleTimeStopCriteria(self.cycle_time_limit)
