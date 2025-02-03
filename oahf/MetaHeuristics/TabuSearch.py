from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Movement import Movement
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.ImplementedBase import ListSelection
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import (
    AlwaysAcceptAcceptanceCriteria,
)
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.BestImprovement import BestImprovement
from oahf.MetaHeuristics.MultipleBestImprovement import MultipleBestImprovement
from oahf.MetaHeuristics.Pertubation import Pertubation
from oahf.MetaHeuristics.PerturbationDrivenLocalSearch import (
    PerturbationDrivenLocalSearch,
)


class TabuSearch(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopTimeIterationCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        ns: NeighborhoodSelection,
        intensification_criteria: StopTimeIterationCriteria,
        second_level_ns: NeighborhoodSelection,
        intensification_ns: NeighborhoodSelection,
        diversification_ns: NeighborhoodSelection,
        intensification_ls: MetaHeuristic,
        diversification_ls: MetaHeuristic,
    ) -> None:
        """
        Initializes the TabuSearch metaheuristic.

        Args:
            thread_id (int): The thread identifier, used to manage thread-specific operations.
            stop_criteria (StopTimeIterationCriteria): Criteria that determine when the
                TabuSearch should stop iterating.
            evaluator (Evaluator): An object responsible for evaluating the quality of solutions.
            acceptance_criteria (AcceptanceCriteria): Criteria to decide whether a new solution
                should be accepted.
            ns (NeighborhoodSelection): Primary neighborhood selection strategy for exploring
                solution space.
            intensification_criteria (StopTimeIterationCriteria): Criteria for stopping
                the intensification phase.
            second_level_ns (NeighborhoodSelection): Secondary neighborhood selection strategy
                for deeper exploration of promising regions in the solution space.
            intensification_ns (NeighborhoodSelection): Neighborhood selection strategy used
                during the intensification phase to refine solutions.
            diversification_ns (NeighborhoodSelection): Neighborhood selection strategy used
                during the diversification phase to explore less-visited regions of the solution space.
            intensification_ls (MetaHeuristic): A local search metaheuristic used to enhance
                solutions during the intensification phase.
            diversification_ls (MetaHeuristic): A local search metaheuristic used to explore
                diverse solutions during the diversification phase.
        """
        super().__init__(
            thread_id, stop_criteria, evaluator, acceptance_criteria, ns.copy()
        )
        self.tabu_list = TabuSearch.TabuTenure()
        self.intensification_criteria = intensification_criteria
        self.second_level_ns = second_level_ns.copy()
        self.intensification_ns = intensification_ns.copy()
        self.diversification_ns = diversification_ns.copy()
        self.intensification_ls = intensification_ls
        self.diversification_ls = diversification_ls

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current TabuSearch instance."""
        return TabuSearch(
            thread,
            self.stop_criteria.copy(),  # type: ignore
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.neighborhood_selection.copy(),  # type: ignore
            self.intensification_criteria.copy(),  # type: ignore
            self.second_level_ns.copy(),
            self.intensification_ns.copy(),
            self.diversification_ns.copy(),
            self.intensification_ls.copy(thread),
            self.diversification_ls.copy(thread),
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the Tabu Search on a single solution."""
        best_sol = sol.copy()
        curr_sol = sol.copy()
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()
        self.intensification_criteria.reset()

        type(best_sol).reset_intensification_diversification_structures()

        counter = 0
        intensification = True

        while (ns := self.neighborhood_selection.get_next(self.thread_id)) and not self.stop_on_evaluations([best_eval]):  # type: ignore
            if counter % self.neighborhood_selection.num_neighborhoods() == 0:  # type: ignore
                best_eval.update_penalties()
                curr_eval = self.evaluator.evaluate(curr_sol)
                best_eval = self.evaluator.evaluate(best_sol)
            try:
                if ns is None:
                    break

                ns.allow_infeasible_movements = True
                build = ns.build_neighborhood_operation(self.thread_id, curr_sol)  # type: ignore

                if build:
                    counter += 1
                    best_move = None
                    best_move_eval = None

                    while (
                        move := ns.get_move_operation()
                    ) is not None and not self.stop_on_evaluations([best_eval]):
                        worked = move.apply_operation()
                        if worked:
                            curr_eval = self.evaluator.evaluate(curr_sol)

                            if (
                                not curr_eval.infeasible()
                                and not curr_eval.has_penalty()
                            ):
                                type(
                                    curr_sol
                                ).update_intensification_diversification_structures(
                                    curr_sol
                                )

                            if (
                                best_move_eval is not None
                                and self.acceptance_criteria.accept(
                                    best_move_eval, curr_eval, curr_sol
                                )
                            ) or (best_move_eval is None):
                                if (
                                    not curr_eval.infeasible()
                                    and not curr_eval.has_penalty()
                                    and move in self.tabu_list
                                ):

                                    best_improv = BestImprovement(
                                        self.thread_id,
                                        NoStopCriteria(),
                                        self.evaluator,
                                        self.acceptance_criteria,
                                        self.second_level_ns,
                                    )

                                    curr_sol = best_improv.run(curr_sol)
                                    curr_eval = self.evaluator.evaluate(curr_sol)

                                    # In order to update the penalties in the evaluation, we need to evaluate it again
                                    best_eval = self.evaluator.evaluate(best_sol)

                                    if self.acceptance_criteria.accept(
                                        best_eval, curr_eval, curr_sol
                                    ):
                                        best_move_eval = curr_eval
                                        best_move = move
                                        move.unapply_operation(curr_eval)
                                        break
                                else:
                                    best_move_eval = curr_eval
                                    best_move = move

                            move.unapply_operation(curr_eval)

                    self.stop_criteria.increment_counter()
                    self.intensification_criteria.increment_counter()

                    if best_move:
                        best_move.apply_operation()
                        curr_eval = self.evaluator.evaluate(curr_sol)

                        # In order to update the penalties in the evaluation, we need to evaluate it again
                        best_eval = self.evaluator.evaluate(best_sol)

                        # Update best solution if necessary
                        if (
                            not curr_eval.infeasible()
                            and not curr_eval.has_penalty()
                            and self.acceptance_criteria.accept(
                                best_eval, curr_eval, curr_sol
                            )
                        ):
                            best_sol = curr_sol.copy()
                            best_eval = curr_eval

                        # Add move to tabu list and enforce tabu tenure
                        self.tabu_list.add_element(
                            best_move, self.get_tabu_iterations_block(best_move)
                        )
                        self.tabu_list.decrement_and_clean()

                    # Apply intensification or diversification strategy

                    if self.intensification_criteria.stop():

                        self.intensification_criteria.reset()

                        selected_ns = (
                            self.intensification_ns.copy()
                            if intensification
                            else self.diversification_ns.copy()
                        )

                        selected_ls = (
                            self.intensification_ls.copy(self.thread_id)
                            if intensification
                            else self.diversification_ls.copy(self.thread_id)
                        )

                        intensification = not intensification
                        pool = ListPool(solutions=[curr_sol])

                        while search := selected_ns.get_next(self.thread_id):
                            perturbation = Pertubation(
                                self.thread_id,
                                StopTimeIterationCriteria(iterations=1),
                                self.evaluator,
                                ListSelection(False, search.copy()),
                                AlwaysAcceptAcceptanceCriteria(),
                                True,
                            )

                            perturbation_ls = PerturbationDrivenLocalSearch(
                                self.thread_id,
                                StopTimeIterationCriteria(iterations=1),
                                self.evaluator,
                                self.acceptance_criteria,
                                perturbation,
                                selected_ls,
                            )

                            pool.add_solution(perturbation_ls.run(curr_sol))

                        curr_sol = pool.get_best(self.evaluator)
                        curr_eval = self.evaluator.evaluate(curr_sol)

                        # In order to update the penalties in the evaluation, we need to evaluate it again
                        best_eval = self.evaluator.evaluate(best_sol)

                        # Update best solution if necessary
                        if (
                            curr_sol
                            and not curr_eval.infeasible()
                            and not curr_eval.has_penalty()
                            and self.acceptance_criteria.accept(
                                best_eval, curr_eval, curr_sol
                            )
                        ):
                            best_sol = curr_sol.copy()
                            best_eval = curr_eval

                    curr_sol = best_sol.copy()

                if self.log_solutions:
                    self.log_best_solution(best_eval)

                ns.allow_infeasible_movements = False

            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                curr_sol = best_sol.copy()
                ns.allow_infeasible_movements = False

        type(best_sol).reset_intensification_diversification_structures()

        return best_sol

    def get_tabu_iterations_block(self, movement: Movement) -> int:
        stop_criteria = self.get_stop_criteria()
        iterations = 1000

        if (
            isinstance(stop_criteria, StopTimeIterationCriteria)
            and stop_criteria.max_iterations
        ):
            iterations = stop_criteria.max_iterations

        return int(iterations * movement.tabu_counter_over_iterations)

    class TabuTenure:
        def __init__(self):
            # Dictionary to store elements and their counters
            self.elements = {}

        def add_element(self, element, iterations):
            """
            Adds an element to the structure with a given counter value.
            """
            if element not in self.elements:
                self.elements[element] = iterations

        def decrement_and_clean(self):
            """
            Decrements all counters and removes elements with a counter of zero.
            """
            to_remove = []
            for element in self.elements:
                self.elements[element] -= 1  # Decrement the counter
                if self.elements[element] <= 0:
                    to_remove.append(element)  # Mark for removal

            # Remove elements with zero counters
            for element in to_remove:
                del self.elements[element]

        def get_elements(self):
            """
            Returns the list of remaining elements.
            """
            return list(self.elements.keys())

        def __contains__(self, item):
            """
            Implements the 'in' operator for this class.
            Returns True if the element is in the structure; False otherwise.
            """
            return item in self.elements

        def reset(self):
            self.elements = {}
