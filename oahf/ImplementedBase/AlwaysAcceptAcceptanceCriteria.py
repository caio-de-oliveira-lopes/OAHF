from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution


class AlwaysAcceptAcceptanceCriteria(AcceptanceCriteria):
    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: Solution
    ) -> bool:
        """
        This method always accepts the new solution, regardless of the comparison
        with the current solution.
        
        :param curr_eval: The current evaluation being considered
        :param next_eval: The new evaluation being considered
        :return: True, indicating the new solution is always accepted
        """
        return True

    def copy(self) -> "AlwaysAcceptAcceptanceCriteria":
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
