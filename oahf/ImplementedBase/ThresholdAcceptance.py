from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution


class ThresholdAcceptance(AcceptanceCriteria):
    def __init__(self, t_start: float, t_end: float, iter_max: int):
        """
        Initializes the ThresholdAcceptance criteria with start and end thresholds and maximum iterations.

        :param t_start: The starting threshold.
        :param t_end: The ending threshold.
        :param iter_max: The maximum number of iterations.
        """
        super().__init__()
        self.t_start = t_start
        self.t_end = t_end
        self.iter_max = iter_max
        self.curr_iter: int = 0
        self.step: float = (t_start - t_end) / iter_max

    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: Solution
    ) -> bool:
        """
        Determines whether to accept the next solution based on the current and next evaluations.

        :param curr_eval: The current evaluation.
        :param next_eval: The next evaluation.
        :param next_sol: The next solution.
        :return: True if the next solution is accepted, False otherwise.
        """
        return next_eval.better_than(curr_eval) and (
            curr_eval.get_objective_function() - next_eval.get_objective_function()
            > ((self.iter_max - self.curr_iter) * self.step)
        )

    def copy(self) -> "ThresholdAcceptance":
        """
        Creates a copy of the current instance.

        :return: A new instance of ThresholdAcceptance.
        """
        return ThresholdAcceptance(self.t_start, self.t_end, self.iter_max)

    def reset(self) -> None:
        """
        Resets the acceptance criteria state.
        """
        self.curr_iter = 0
