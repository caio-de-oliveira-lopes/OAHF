from abc import ABC, abstractmethod
from typing import Union

from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution


class AcceptanceCriteria(Entity, ABC):

    @abstractmethod
    def accept(
        self,
        curr_eval: "Evaluation",
        next_eval: "Evaluation",
        next_sol: Union["Solution", Pool],
    ) -> bool:
        """
        Abstract method to evaluate acceptance criteria.
        :param curr_eval: Current evaluation.
        :param next_eval: Next evaluation.
        :param next_sol: Next solution or pool of solutions.
        :return: Boolean value indicating acceptance.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Abstract method to reset the acceptance criteria.
        """
        pass

    @abstractmethod
    def copy(self) -> "AcceptanceCriteria":
        """
        Abstract method to copy the acceptance criteria.
        :return: A copy of the acceptance criteria.
        """
        pass
