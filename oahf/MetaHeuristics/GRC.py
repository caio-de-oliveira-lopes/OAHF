from typing import List, Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Movement import Movement
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.Utils.Util import Util


class GRC(MetaHeuristic):
    """Greedy Randomized Construction.

    Given a greediness value G (0-1), selects a random move out of the (G * NumCandidates) best candidates.
    """

    def __init__(
        self,
        thread_id: int,
        greediness: float,
        stop: StopCriteria,
        evaluator: Evaluator,
        ns: NeighborhoodSelection,
        criteria: AcceptanceCriteria,
    ) -> None:
        """Initialize the GRC meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            greediness (float): The greediness value.
            stop (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            ns (NeighborhoodSelection): The neighborhood selection strategy.
            criteria (AcceptanceCriteria): The acceptance criteria for solutions.
        """
        super().__init__(thread_id, stop, evaluator, ns, criteria)
        self.greediness = greediness
        self.original_greediness = greediness

    def copy(self, thread: int) -> "GRC":
        """Creates a copy of the GRC instance.

        Args:
            thread (int): The ID of the thread for the copied instance.

        Returns:
            GRC: A new instance of GRC that is a copy of this instance.
        """
        return GRC(
            thread,
            self.greediness,
            self.stop_criteria.copy(),
            self.evaluator,
            self.neighborhood_selection.copy(),
            self.acceptance_criteria.copy(),
        )

    def run(self, sol: Optional[Solution]) -> Optional[Solution]:
        """Executes the GRC meta-heuristic.

        Args:
            sol (Optional[Solution]): The initial solution, which can be None.

        Returns:
            Optional[Solution]: The best solution found during execution.
        """
        curr_sol = sol.copy() if sol is not None else sol
        best_eval = self.evaluator.evaluate(sol)

        ns = self.neighborhood_selection.get_next(self.thread_id)
        improved = False

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while not self.stop_on_evaluations(best_eval):
            try:
                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)
                improved = False
                if build:
                    all_moves: List[Movement] = []
                    move = ns.get_move_operation()
                    while move is not None:
                        all_moves.append(move)
                        move = ns.get_move_operation()

                    if not all_moves:
                        break  # no moves available

                    num_chosen = max(1, int(len(all_moves) * self.greediness))
                    ordered_moves = sorted(all_moves, key=lambda x: x.get_cost())[
                        :num_chosen
                    ]
                    ordered_moves.sort(
                        key=lambda x: (
                            x.get_cost()
                            if self.greediness > 0.9999
                            else ThreadManager.get_next_double(self.thread_id)
                        ),
                        reverse=True,
                    )

                    while ordered_moves and not self.stop_on_evaluations(best_eval):
                        self.stop_criteria.increment_counter()
                        move = ordered_moves.pop()  # Get the last (least desirable)
                        worked = move.apply_operation()

                        if worked:
                            curr_eval = self.evaluator.evaluate(curr_sol)
                            if self.acceptance_criteria.accept(
                                best_eval, curr_eval, curr_sol
                            ):
                                if self.original_greediness > 0:
                                    self.greediness = self.original_greediness
                                    self.original_greediness = 0
                                move.report_apply_improvement(curr_eval, best_eval)
                                improved = True
                                best_eval = curr_eval
                                ns.accept_movement()
                                break
                            else:
                                move.unapply_operation(curr_eval)

                    if self.greediness > 0.99999 and not improved:
                        break  # No improvement found even with greediness set to 1
                    elif not improved:
                        self.original_greediness = self.greediness
                        self.greediness = 1
                else:
                    break  # fail on building NS

            except Exception as ex:
                Util.logger.trace_warning("Something wrong happened.")
                Util.logger.trace_error(str(ex))
                raise

        return curr_sol
