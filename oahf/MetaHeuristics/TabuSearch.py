from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager

class TabuSearch(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection,
        tabu_tenure: int,
    ) -> None:
        """
        Initializes the TabuSearch metaheuristic.

        Args:
            thread_id (int): The thread identifier.
            stop_criteria (StopCriteria): The stopping criteria for the metaheuristic.
            evaluator (Evaluator): Evaluator to assess solutions.
            acceptance_criteria (AcceptanceCriteria): Acceptance criteria for new solutions.
            ns (NeighborhoodSelection): Neighborhood selection strategy.
            tabu_tenure (int): The number of iterations a move remains in the tabu list.
        """
        super().__init__(thread_id, stop_criteria, evaluator, acceptance_criteria, ns)
        self.tabu_list = []  # List to store tabu moves
        self.tabu_tenure = tabu_tenure

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current TabuSearch instance."""
        return TabuSearch(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
            self.tabu_tenure,
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the Tabu Search on a single solution."""
        best_sol = sol.copy()
        curr_sol = best_sol
        best_eval = self.evaluator.evaluate(best_sol)
        
        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while (ns := self.neighborhood_selection.get_next(self.thread_id)) and not self.stop_on_evaluations([best_eval]):  # type: ignore
            try:
                if ns is None:
                    break
                
                ns.allow_infeasible_movements = True
                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)

                if build:
                    best_move = None
                    best_move_eval = None

                    while (move := ns.get_move_operation()) is not None and not self.stop_on_evaluations([best_eval]):
                        if move not in self.tabu_list:
                            worked = move.apply_operation()
                            if worked:
                                curr_eval = self.evaluator.evaluate(curr_sol)

                                # TODO: make the new constraints soft constraints, so they'll pass by
                                if best_move_eval is not None and self.acceptance_criteria.accept(best_move_eval, curr_eval, curr_sol):
                                    best_move_eval = curr_eval
                                    best_move = move

                                move.unapply_operation(curr_eval)
                                self.evaluator.update_evaluation_after_unapply(curr_sol)

                            self.stop_criteria.increment_counter()

                    if best_move:
                        best_move.apply_operation()
                        curr_eval = self.evaluator.evaluate(curr_sol)
                        
                        # Update best solution if necessary
                        if self.acceptance_criteria.accept(best_eval, curr_eval, curr_sol):
                            best_sol = curr_sol.copy()
                            best_eval = curr_eval

                        # Add move to tabu list and enforce tabu tenure
                        self.tabu_list.append(best_move)
                        if len(self.tabu_list) > self.tabu_tenure:
                            self.tabu_list.pop(0)

                if self.log_solutions:
                    self.log_best_solution(best_eval)
                    
                ns.allow_infeasible_movements = False

            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                curr_sol = best_sol.copy()
                ns.allow_infeasible_movements = False

        return best_sol
