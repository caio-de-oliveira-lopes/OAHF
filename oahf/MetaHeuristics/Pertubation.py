from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Utils.Util import Util


class Pertubation(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        ns: NeighborhoodSelection,
        accept_infeasible: bool,
        criteria: AcceptanceCriteria,
    ) -> None:
        """Initialize the Pertubation meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            ns (NeighborhoodSelection): The neighborhood selection method.
            accept_infeasible (bool): Whether to accept infeasible solutions.
            criteria (AcceptanceCriteria): The acceptance criteria for solutions.
        """
        super().__init__(thread_id, stop, evaluator, ns, criteria)
        self.accept_infeasible = accept_infeasible

    def copy(self, thread: int) -> "Pertubation":
        """Creates a copy of the Pertubation instance.

        Args:
            thread (int): The ID of the thread for the copied instance.

        Returns:
            Pertubation: A new instance of Pertubation that is a copy of this instance.
        """
        return Pertubation(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            NeighborhoodSelection.copy(),
            self.accept_infeasible,
            self.acceptance_criteria.copy(),
        )

    def run(self, sol: Optional[Solution]) -> Optional[Solution]:
        """Executes the Pertubation meta-heuristic.

        Args:
            sol (Optional[Solution]): The initial solution, which can be None.

        Returns:
            Optional[Solution]: The best solution found during execution.
        """
        best_sol = sol  # Keep track of the best solution
        curr_sol = best_sol
        best_eval = self.evaluator.evaluate(best_sol)

        self.evaluator.save_evaluation_state(best_sol)

        self.stop_criteria.reset()

        while not self.stop_on_evaluations(best_eval):
            ns = None

            try:
                ns = NeighborhoodSelection.get_next(self.thread_id)
            except Exception as ex:
                Util.logger.error("Unable to get neighborhood.")

            try:
                if ns is None:
                    break

                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)

                if build:
                    move = ns.get_move_operation()
                    self.stop_criteria.increment_counter()
                    while move is not None and not self.stop_on_evaluations(best_eval):
                        worked = move.apply_operation()
                        if worked:
                            curr_eval = self.evaluator.evaluate(curr_sol)
                            if (
                                self.accept_infeasible or not curr_eval.infeasible()
                            ):  # TODO: use AcceptanceCriteria
                                best_sol = curr_sol.copy()
                                move.report_apply_improvement(curr_eval, best_eval)
                                self.evaluator.save_evaluation_state(best_sol)
                                return best_sol
                            else:
                                move.unapply_operation(curr_eval)
                                self.evaluator.update_evaluation_after_unapply(curr_sol)

                        move = ns.get_move_operation()
                        self.stop_criteria.increment_counter()
            except Exception as ex:
                Util.logger.error(
                    f"Something went wrong while trying to use {ns}.\n{ex}"
                )

                curr_sol = best_sol.copy()

        self.evaluator.save_evaluation_state(best_sol)

        return best_sol
