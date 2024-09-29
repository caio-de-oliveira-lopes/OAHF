from typing import Type

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution


class BetterAcceptanceCriteria(AcceptanceCriteria):
    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: Solution
    ) -> bool:
        """
        Accepts the next evaluation if it's better than the current one.
        :param curr_eval: The current Evaluation object.
        :param next_eval: The next Evaluation object to compare.
        :param next_sol: The Solution associated with the next evaluation.
        :return: True if next_eval is better than curr_eval, otherwise False.
        """
        return next_eval.better_than(curr_eval)

    def copy(self) -> Type[AcceptanceCriteria]:
        """
        Returns a new instance of BetterAcceptanceCriteria.
        :return: A new BetterAcceptanceCriteria instance.
        """
        return BetterAcceptanceCriteria()

    def reset(self) -> None:
        """
        Resets the acceptance criteria.
        This method has no implementation in BetterAcceptanceCriteria.
        """
        pass  # No implementation needed
