from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.Pertubation import Pertubation


class PerturbationDrivenLocalSearch(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        perturbation: Pertubation,
        local_search: MetaHeuristic,
    ) -> None:
        """
        Initializes the PerturbationDrivenLocalSearch metaheuristic.

        Args:
            thread_id (int): The thread identifier, used to manage thread-specific operations.
            stop_criteria (StopCriteria): Criteria that determine when the algorithm should stop
                iterating.
            evaluator (Evaluator): An object responsible for evaluating the quality of solutions.
            acceptance_criteria (AcceptanceCriteria): Criteria to decide whether a new solution
                should be accepted into the current set of solutions.
            perturbation (Pertubation): A mechanism used to apply controlled changes to solutions,
                helping the algorithm escape local optima by diversifying the search space.
            local_search (MetaHeuristic): A local search metaheuristic used to intensively improve
                the solutions generated after perturbation.
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            None,
            [perturbation, local_search],
        )
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
                perturbed_sol = self.perturbation.run(best_sol.copy())

                # Perform local search using BestImprovement
                improved_sol = self.local_search.run(perturbed_sol)
                improved_eval = self.evaluator.evaluate(improved_sol)

                # Update the best solution if improvement is found
                if self.acceptance_criteria.accept(
                    best_eval, improved_eval, improved_sol
                ):
                    best_sol = improved_sol.copy()
                    best_eval = improved_eval

                self.stop_criteria.increment_counter()

            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)

        return best_sol
