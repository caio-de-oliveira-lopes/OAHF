from typing import Optional

from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.BetterAcceptanceCriteria import BetterAcceptanceCriteria
from oahf.Utils.Util import Util


class BetterUnknownAcceptance(BetterAcceptanceCriteria):
    def __init__(self, fixed_perc: Optional[float], log_factor: Optional[float]):
        """
        Initializes the BetterUnknownAcceptance criteria with optional fixed percentage and log factor.

        :param fixed_perc: Fixed percentage for acceptance criteria.
        :param log_factor: Log factor for acceptance criteria.
        """
        super().__init__()
        self.fixed_perc = fixed_perc
        self.log_factor = log_factor  # value between 0 and 1
        self.counter: int = 0

    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: Solution
    ) -> bool:
        """
        Determines whether to accept the next solution based on the evaluation and known solutions.

        :param curr_eval: The current evaluation.
        :param next_eval: The next evaluation.
        :param next_sol: The next solution.
        :return: True if the next solution is accepted, False otherwise.
        """
        return super().accept(curr_eval, next_eval, next_sol) and (
            next_sol.shared_memory.solution_nodes.get(
                next_sol.solution_string_representation()
            )
            is None
            or self.accept_known_solution()
        )

    def accept_known_solution(self) -> bool:
        """
        Determines whether to accept a known solution based on the fixed percentage or log factor.

        :return: True if the known solution is accepted, False otherwise.
        """
        self.counter += 1
        v = ThreadManager.get_next_double(Util.get_current_thread_id())
        target = (
            self.fixed_perc
            if self.fixed_perc is not None
            else (self.log_factor / (self.counter**0.1))
        )  # Using logarithm base 10
        return v < target

    def reset(self) -> None:
        """
        Resets the acceptance criteria state.
        """
        self.counter = 0
        super().reset()

    def copy(self) -> "BetterUnknownAcceptance":
        """
        Creates a copy of the current instance.

        :return: A new instance of BetterUnknownAcceptance.
        """
        return BetterUnknownAcceptance(self.fixed_perc, self.log_factor)
