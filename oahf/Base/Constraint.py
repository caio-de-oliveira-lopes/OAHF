from abc import ABC, abstractmethod

from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Entity import Entity
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class Constraint(Entity, ABC):

    @abstractmethod
    def evaluate(self, solution: "Solution", cache: bool) -> "ConstraintEvaluation":
        """
        Abstract method to evaluate the constraint based on a solution.
        :param solution: A Solution object.
        :return: A ConstraintEvaluation object.
        """
        pass

    def evaluate_with_stop_criteria(
        self, solution: "Solution", stop_criteria: "StopCriteria", cache: bool
    ) -> "ConstraintEvaluation":
        """
        Virtual method to evaluate the constraint, optionally considering stop criteria.
        :param solution: A Solution object.
        :param stop_criteria: A StopCriteria object.
        :return: A ConstraintEvaluation object (default behavior is to ignore stop criteria).
        """
        return self.evaluate(solution, cache)

    @classmethod
    @abstractmethod
    def multiply_penalty(cls, multiplier: float) -> None:
        """
        Adjust the penalty multiplier for the constraint violations.
        :param multiplier: Multiplier for the penalty value.
        """
        pass

    @classmethod
    @abstractmethod
    def set_penalty(cls, value: float) -> None:
        """
        Set the penalty value for the constraint violations.
        :param value: Penalty value.
        """
        pass
