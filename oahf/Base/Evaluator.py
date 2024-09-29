from abc import ABC, abstractmethod
from typing import List, Optional

from oahf.Base.Constraint import Constraint
from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class Evaluator(Entity, ABC):
    def __init__(self, stop_on_first: bool, *constraints: "Constraint"):
        """
        Initializes an Evaluator with the option to stop on the first infeasibility.
        :param stop_on_first: Boolean indicating whether to stop on first infeasibility.
        :param constraints: Variable-length list of Constraint objects.
        """
        super().__init__()
        self._constraints: List["Constraint"] = list(constraints)
        self._stop_on_first_infeasibility: bool = stop_on_first
        self.stop_criteria: Optional["StopCriteria"] = None

    @abstractmethod
    def evaluate(self, sol: "Solution") -> "Evaluation":
        """
        Abstract method to evaluate a Solution.
        :param sol: A Solution object to evaluate.
        :return: An Evaluation object.
        """
        pass

    def save_evaluation_state(self, sol: "Solution") -> None:
        """
        Saves the state of the evaluation for a given Solution.
        :param sol: A Solution object.
        """
        pass  # Default implementation does nothing

    def update_evaluation_after_unapply(self, sol: "Solution") -> None:
        """
        Updates the evaluation after an unapply action on a Solution.
        :param sol: A Solution object.
        """
        pass  # Default implementation does nothing

    @property
    def constraints(self) -> List["Constraint"]:
        """Returns the list of constraints."""
        return self._constraints

    @property
    def stop_on_first_infeasibility(self) -> bool:
        """Returns whether to stop on the first infeasibility."""
        return self._stop_on_first_infeasibility
