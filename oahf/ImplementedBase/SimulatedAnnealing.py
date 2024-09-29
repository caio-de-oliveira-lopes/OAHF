import math

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.Utils.Util import Util


class SimulatedAnnealing(AcceptanceCriteria):
    def __init__(self, t_start: float, t_end: float, iter_max: int):
        """
        Initializes a SimulatedAnnealing acceptance criteria.
        :param t_start: The starting temperature.
        :param t_end: The ending temperature.
        :param iter_max: The maximum number of iterations.
        """
        self._t_start = t_start
        self._t_end = t_end
        self._iter_max = iter_max
        self._curr_iter = 0
        self._step = (t_start - t_end) / iter_max

    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: Solution
    ) -> bool:
        """
        Determines whether to accept the next solution.
        :param curr_eval: The current evaluation.
        :param next_eval: The next evaluation.
        :param next_sol: The next solution.
        :return: True if the next solution is accepted, otherwise False.
        """
        self._curr_iter += 1
        v = ThreadManager.get_next_double(Util.get_current_thread_id())

        return next_eval.better_than(curr_eval) or (
            not next_eval.infeasible()
            and v
            <= math.exp(
                (
                    curr_eval.get_objective_function()
                    - next_eval.get_objective_function()
                )
                / ((self._iter_max - self._curr_iter) * self._step)
            )
        )

    def copy(self) -> "SimulatedAnnealing":
        """Creates a copy of the current SimulatedAnnealing instance."""
        return SimulatedAnnealing(self._t_start, self._t_end, self._iter_max)

    def reset(self) -> None:
        """Resets the current iteration counter."""
        self._curr_iter = 0
