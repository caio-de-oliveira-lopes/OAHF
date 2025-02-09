from abc import ABC
from typing import Iterable, List

from oahf.Base.StopCriteria import StopCriteria


class MultipleStopCriteria(StopCriteria):
    def __init__(self, stop_when_any: bool, *stop_criterias: StopCriteria) -> None:
        """
        Initializes the MultipleStopCriteria with a list of StopCriteria.

        Args:
            stop_criterias (List[StopCriteria]): The list of stop criteria to evaluate.
            stop_when_any (bool): If True, will stop when any criteria are met.
                                  If False, will stop only when all criteria are met.
        """
        super().__init__()
        self.stop_criterias: List[StopCriteria] = list(stop_criterias)
        self.stop_when_any: bool = stop_when_any

    def stop(self) -> bool:
        """Determines whether any or all stopping criteria have been met based on the configuration."""
        if self.stop_when_any:
            return any(criteria.stop() for criteria in self.stop_criterias)
        return all(criteria.stop() for criteria in self.stop_criterias)

    def stop_on_evaluations(self, evaluations: Iterable["Evaluation"]) -> bool:
        """Checks if the stopping criteria are met based on evaluations.

        Args:
            evaluations (Iterable[Evaluation]): The evaluations to check against.

        Returns:
            bool: True if stopping criteria are met; otherwise, False.
        """
        if self.stop_when_any:
            return any(
                criteria.stop_on_evaluations(evaluations)
                for criteria in self.stop_criterias
            )
        return all(
            criteria.stop_on_evaluations(evaluations)
            for criteria in self.stop_criterias
        )

    def copy(self) -> "MultipleStopCriteria":
        """Creates a copy of the MultipleStopCriteria instance."""
        return MultipleStopCriteria(
            self.stop_when_any, *(criteria.copy() for criteria in self.stop_criterias)
        )

    def increment_counter(self) -> None:
        """
        Increments the internal counter for each stop criteria and prints progress report if enabled.
        """
        for criteria in self.stop_criterias:
            criteria.increment_counter()

        super().increment_counter()

    def reset(self) -> None:
        """Resets the stopping criteria."""
        for criteria in self.stop_criterias:
            criteria.reset()
