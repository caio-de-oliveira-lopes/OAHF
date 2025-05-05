import collections
import gc
from typing import Optional

from tqdm import tqdm

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Movement import Movement
from oahf.Base.MultipleStopCriteria import MultipleStopCriteria
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.ImplementedBase import ListSelection, MaxCycleTimeStopCriteria
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import (
    AlwaysAcceptAcceptanceCriteria,
)
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.ImplementedBase.StopNoImprovement import StopNoImprovement
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.BestImprovement import BestImprovement
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
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
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
            origin_pool (Optional[Pool]): Pool of initial solutions.
            destination_pool (Optional[Pool]): Pool where optimized solutions are stored.
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            ns.copy(),
            [],
            origin_pool,
            destination_pool,
        )
        self.tabu_list = TabuSearch.TabuTenure()
        self.intensification_criteria = intensification_criteria
        self.second_level_ns = second_level_ns.copy()
        self.intensification_ns = intensification_ns.copy()
        self.diversification_ns = diversification_ns.copy()
        self.intensification_ls = intensification_ls
        self.diversification_ls = diversification_ls
        self.use_progress_bar = (
            isinstance(stop_criteria, StopTimeIterationCriteria)
            and stop_criteria.max_iterations is not None
        )

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
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run_operation(
        self,
        origin_pool: Pool,
        destination_pool: Optional[Pool],
        parent: Optional["MetaHeuristic"] = None,
    ) -> Pool:
        """Run the heuristic on a given pool of solutions."""
        try:
            self.parent_metaheuristic = parent
            self.stop_criteria.reset()
            if self.neighborhood_selection:
                self.neighborhood_selection.reset(self.thread_id)

            result = destination_pool if destination_pool else ListPool()
            self.start_time = self._current_milliseconds()

            sol = origin_pool.get_best(self.evaluator)

            if sol:
                result.add_solution(self.run(sol), self)

            self.end_time = self._current_milliseconds()
            return result
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            raise

    def run(self, sol: Solution) -> Solution:
        """Executes the Tabu Search on a single solution with optimizations for computational time."""
        # Create initial copies and cache frequently used attributes
        best_sol = sol.copy()
        curr_sol = sol.copy()

        name = self.name
        evaluator = self.evaluator
        tabu_list = self.tabu_list
        acceptance = self.acceptance_criteria
        stop_criteria = self.stop_criteria
        intensification_criteria = self.intensification_criteria
        neighborhood_selection: NeighborhoodSelection = self.neighborhood_selection  # type: ignore
        thread_id = self.thread_id
        destination_pool = self.destination_pool

        curr_eval = evaluator.evaluate(curr_sol)
        best_eval = evaluator.evaluate(best_sol)

        # Reset criteria and structures
        stop_criteria.reset()
        acceptance.reset()
        intensification_criteria.reset()
        type(best_sol).reset_intensification_diversification_structures()

        counter = 0
        intensification = True

        pbar = None
        if self.use_progress_bar:
            max_iterations = stop_criteria.max_iterations  # type: ignore
            pbar = tqdm(
                total=max_iterations, desc=f"{name} Progress", position=0, leave=False
            )

        # Cache neighborhood count if constant
        num_neigh = neighborhood_selection.num_neighborhoods()

        while (
            ns := neighborhood_selection.get_next(thread_id)
        ) and not self.stop_on_evaluations([best_eval], pbar):
            if curr_sol is None:
                break

            # Every full cycle over neighborhoods, update penalties and reevaluate
            if counter % num_neigh == 0:
                best_eval.update_penalties()
                curr_eval.reevaluate()
                best_eval.reevaluate()

            try:
                ns.allow_infeasible_movements = True
                if not ns.build_neighborhood_operation(thread_id, curr_sol):
                    ns.allow_infeasible_movements = False
                    continue

                counter += 1
                best_move = None
                best_move_eval = None

                # Iterate through moves in the current neighborhood
                while (
                    move := ns.get_move()
                ) is not None and not self.stop_on_evaluations([best_eval], pbar):
                    if move.apply():
                        curr_eval = evaluator.evaluate(curr_sol)

                        if not curr_eval.infeasible() and not curr_eval.has_penalty():
                            type(
                                curr_sol
                            ).update_intensification_diversification_structures(
                                curr_sol
                            )

                        # If move is tabu, check if it still meets acceptance criteria
                        if move in tabu_list:
                            if acceptance.accept(best_eval, curr_eval, curr_sol):
                                best_improv = BestImprovement(
                                    thread_id,
                                    NoStopCriteria(),
                                    evaluator,
                                    acceptance,
                                    self.second_level_ns,
                                )

                                best_improv.named_parent = self
                                previous_curr_sol = curr_sol
                                curr_sol = best_improv.run(curr_sol)
                                curr_eval = evaluator.evaluate(curr_sol)

                                if (
                                    destination_pool
                                    and not curr_eval.infeasible()
                                    and not curr_eval.has_penalty()
                                ):
                                    destination_pool.add_solution(curr_sol, self)

                                if (
                                    not curr_eval.infeasible()
                                    and not curr_eval.has_penalty()
                                    and acceptance.accept(
                                        best_eval, curr_eval, curr_sol
                                    )
                                    and curr_sol != best_sol
                                ):
                                    best_sol = curr_sol.copy()
                                    best_eval = curr_eval
                                    best_move = None
                                    best_move_eval = None
                                    break
                                else:
                                    curr_sol = previous_curr_sol
                        else:
                            # Update best move if found or if current move is acceptable compared to the previous one
                            if best_move_eval is None or acceptance.accept(
                                best_move_eval, curr_eval, curr_sol
                            ):
                                best_move_eval = curr_eval
                                best_move = move

                        move.unapply()

                intensification_criteria.increment_counter()

                if best_move:
                    best_move.apply()
                    curr_eval = evaluator.evaluate(curr_sol)
                    if (
                        destination_pool
                        and not curr_eval.infeasible()
                        and not curr_eval.has_penalty()
                    ):
                        destination_pool.add_solution(curr_sol, self)
                    # Update best solution if criteria are met
                    if (
                        not curr_eval.infeasible()
                        and not curr_eval.has_penalty()
                        and acceptance.accept(best_eval, curr_eval, curr_sol)
                        and curr_sol != best_sol
                    ):
                        curr_sol = best_sol.copy()
                        best_eval = curr_eval

                    tabu_list.add_element(
                        best_move, self.get_tabu_iterations_block(best_move)
                    )
                    tabu_list.decrement_and_clean()

                # Intensification/Diversification phase
                if intensification_criteria.stop():
                    gc.collect()  # trigger garbage collection
                    intensification_criteria.reset()

                    selected_ns = (
                        self.intensification_ns.copy()
                        if intensification
                        else self.diversification_ns.copy()
                    )
                    selected_ls = (
                        self.intensification_ls.copy(thread_id)
                        if intensification
                        else self.diversification_ls.copy(thread_id)
                    )
                    intensification = not intensification

                    pool = ListPool(solutions=[curr_sol])
                    while search := selected_ns.get_next(thread_id):
                        perturbation = Pertubation(
                            thread_id,
                            MultipleStopCriteria(True, 
                                                 StopTimeIterationCriteria(iterations=1), 
                                                 curr_sol.get_default_limit_stop_criteria()),
                            evaluator,
                            ListSelection(False, search.copy()),
                            AlwaysAcceptAcceptanceCriteria(),
                            True,
                        )
                        perturbation_ls = PerturbationDrivenLocalSearch(
                            thread_id,
                            StopTimeIterationCriteria(iterations=1),
                            evaluator,
                            acceptance,
                            perturbation,
                            selected_ls,
                        )
                        
                        perturbation_ls.named_parent = self
                        perturbation.named_parent = perturbation_ls
                        selected_ls.named_parent = perturbation_ls

                        perturbated_sol = perturbation_ls.run(curr_sol)
                        perturbated_evaluation = self.evaluator.evaluate(perturbated_sol)
                        if not (perturbated_evaluation.infeasible() or perturbated_evaluation.has_penalty()):
                            pool.add_solution(perturbated_sol, self)
                            if destination_pool:
                                destination_pool.add_solution(perturbated_sol, self)

                    curr_sol = pool.get_best(evaluator)
                    curr_eval = evaluator.evaluate(curr_sol)
                    if (
                        destination_pool
                        and not (curr_eval.infeasible() or curr_eval.has_penalty())
                    ):
                        destination_pool.add_solution(curr_sol, self)

                    if (
                        curr_sol and not (curr_eval.infeasible() or curr_eval.has_penalty())
                        and acceptance.accept(best_eval, curr_eval, curr_sol)
                        and curr_sol != best_sol
                    ):
                        curr_sol = best_sol.copy()
                        best_eval = curr_eval

                if curr_sol != best_sol:
                    curr_sol = best_sol.copy()

                ns.allow_infeasible_movements = False                
                stop_criteria.increment_counter(pbar)

            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                if curr_sol != best_sol:
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
            self.elements = collections.defaultdict(int)

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
            self.elements = {e: c - 1 for e, c in self.elements.items() if c > 1}

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
