from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution


class BetterOrSameAcceptanceCriteria(AcceptanceCriteria):
    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: Solution
    ) -> bool:
        """
        Determines whether to accept the next solution based on the evaluation.

        :param curr_eval: The current evaluation.
        :param next_eval: The next evaluation.
        :param next_sol: The next solution.
        :return: True if the next solution is better or equal, False otherwise.
        """
        return next_eval.better_or_equal_to(curr_eval)

    def copy(self) -> "BetterOrSameAcceptanceCriteria":
        """
        Creates a copy of the current instance.

        :return: A new instance of BetterOrSameAcceptanceCriteria.
        """
        return self

    def reset(self) -> None:
        """
        Resets the acceptance criteria state.
        """
        pass
