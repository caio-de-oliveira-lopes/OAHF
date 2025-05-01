import traceback
from typing import List, Optional

from oahf.Base import Neighborhood
from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Movement import Movement
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.Logger.LogManager import LogManager


class GRC(MetaHeuristic):
    """Greedy Randomized Construction.

    Given a greediness value G (0-1), selects a random move out of the (G * NumCandidates) best candidates.
    """

    def __init__(
        self,
        thread_id: int,
        greediness: float,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection,
        order_moves: bool = False,
        destination_pool: Optional[Pool] = None,
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

        super().__init__(
            thread_id, stop_criteria, evaluator, acceptance_criteria, ns.copy()
        )
        self.greediness = greediness
        self.original_greediness = greediness
        self.order_moves = order_moves

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
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
            self.order_moves,
            destination_pool=(
                self.destination_pool.copy() if self.destination_pool else None
            ),
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the GRC meta-heuristic.

        Args:
            sol (Solution): The initial solution, which can be None.

        Returns:
            Solution: The best solution found during execution.
        """
        curr_sol = sol.copy() if sol is not None else sol
        best_eval = self.evaluator.evaluate(sol)

        if self.neighborhood_selection:
            self.neighborhood_selection.reset(self.thread_id)

        ns: Optional[Neighborhood] = self.neighborhood_selection.get_next(self.thread_id)  # type: ignore

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while ns and not self.stop_on_evaluations([best_eval]):
            try:
                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)
                if build:
                    all_moves: List[Movement] = []
                    move = ns.get_move()
                    while move is not None:
                        all_moves.append(move)
                        move = ns.get_move()

                    if not all_moves:
                        break  # no moves and no ns available

                    num_chosen = max(1, int(len(all_moves) * (1 - self.greediness)))
                    ordered_moves = sorted(all_moves, key=lambda x: x.get_cost())[
                        :num_chosen
                    ]
                    if self.order_moves:
                        ordered_moves.sort(
                            key=lambda x: (
                                x.get_cost()
                                if self.greediness > 0.9999
                                else ThreadManager.get_next_float(
                                    self.thread_id, 0, len(ordered_moves)
                                )
                            )
                        )

                    while ordered_moves and not self.stop_on_evaluations([best_eval]):
                        move = ordered_moves.pop()
                        worked = move.apply()

                        if worked:
                            curr_eval = self.evaluator.evaluate(curr_sol)
                            if self.acceptance_criteria.accept(
                                best_eval, curr_eval, curr_sol
                            ):
                                best_eval = curr_eval
                                break
                            else:
                                move.unapply()
                        self.stop_criteria.increment_counter()

                else:
                    break  # fail on building NS

            except Exception as ex:
                LogManager.something_went_wrong(str(ns), ex)
                traceback.print_exc()
                raise

        return curr_sol
