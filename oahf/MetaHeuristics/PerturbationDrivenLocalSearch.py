from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.Pertubation import Pertubation
from oahf.MetaHeuristics.BestImprovement import BestImprovement


class PerturbationDrivenLocalSearch(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        perturbation: Pertubation,
        local_search: MetaHeuristic
    ) -> None:
        """
        Initializes the PerturbationDrivenLocalSearch metaheuristic.

        Args:
            thread_id (int): Identifier for the thread.
            stop_criteria (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            acceptance_criteria (AcceptanceCriteria): The acceptance criteria for solutions.
            perturbation (Pertubation): Perturbation mechanism applied before local search.
        """
        super().__init__(thread_id, stop_criteria, evaluator, acceptance_criteria, None, [perturbation, local_search])
        self.perturbation = perturbation
        self.local_search = local_search

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current PerturbationDrivenLocalSearch instance."""
        return PerturbationDrivenLocalSearch(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.perturbation.copy(thread),
            self.local_search.copy(thread),
        )

    def run(self, sol: Solution) -> Solution:
        """Executes the Perturbation Driven Local Search on a single solution."""
        best_sol = sol.copy()
        best_eval = self.evaluator.evaluate(best_sol)

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()

        while not self.stop_on_evaluations([best_eval]):
            try:
                # Apply perturbation
                perturbed_sol = self.perturbation.run(best_sol)

                # Perform local search using BestImprovement
                improved_sol = self.local_search.run(perturbed_sol)
                improved_eval = self.evaluator.evaluate(improved_sol)

                # Update the best solution if improvement is found
                if self.acceptance_criteria.accept(best_eval, improved_eval, improved_sol):
                    best_sol = improved_sol.copy()
                    best_eval = improved_eval

                self.stop_criteria.increment_counter()

            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)

        return best_sol
