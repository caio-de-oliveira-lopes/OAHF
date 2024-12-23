from typing import Optional

import numpy as np
from pymoo.algorithms.soo.nonconvex.brkga import BRKGA as PymooBRKGA
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class BRKGA(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        population_size: int,
        elite_fraction: float,
        mutant_fraction: float,
        bias: float,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ) -> None:
        """Initialize the BRKGA meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop_criteria (StopCriteria): The stopping criteria for the algorithm.
            evaluator (Evaluator): The evaluator used to assess solutions.
            acceptance_criteria (AcceptanceCriteria): The acceptance criteria for solutions.
            origin_pool (Optional[Pool]): The pool containing initial solutions.
            destination_pool (Optional[Pool]): The pool to store resulting solutions.
            population_size (int): The size of the BRKGA population.
            elite_fraction (float): Fraction of elite individuals.
            mutant_fraction (float): Fraction of mutant individuals.
            bias (float): Probability bias for inheritance during crossover.
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            None,
            [],
            origin_pool,
            destination_pool,
        )

        self.population_size = population_size
        self.elite_fraction = elite_fraction
        self.mutant_fraction = mutant_fraction
        self.bias = bias

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current BRKGA instance."""
        return BRKGA(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.population_size,
            self.elite_fraction,
            self.mutant_fraction,
            self.bias,
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run(self, sol: Solution) -> Solution:
        """Runs the BRKGA on a single solution. Not implemented in this class."""
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(self, origin_pool: Pool, destination_pool: Pool) -> Pool:
        """Executes the BRKGA meta-heuristic with external control.

        Args:
            origin_pool (Pool): The initial solution pool.
            destination_pool (Pool): The output solution pool.

        Returns:
            Pool: The pool of solutions found during execution.
        """
        # Convert Pool to initial population
        initial_population = [sol.to_random_keys() for sol in origin_pool.solutions]

        # Problem definition for Pymoo
        class PymooProblem(Problem):
            def __init__(self):
                super().__init__(
                    n_var=len(initial_population[0]), n_obj=1, xl=0.0, xu=1.0
                )

            def _evaluate(self, X, out, *args, **kwargs):
                solutions = []
                for keys in X:
                    solutions.append(origin_pool.solutions[0].from_random_keys(keys))

                fitness = Solution.evaluate_population(solutions)
                out["F"] = np.array(fitness)

        problem = PymooProblem()

        # Initialize BRKGA algorithm
        algorithm = PymooBRKGA(
            pop_size=self.population_size,
            elite_frac=self.elite_fraction,
            mutant_frac=self.mutant_fraction,
            bias=self.bias,
        )

        # External loop control
        self.stop_criteria.reset()
        self.acceptance_criteria.reset()
        best_solution = origin_pool.get_best(self.evaluator)
        best_evaluation = self.evaluator.evaluate(best_solution)

        while not self.stop_on_evaluations([best_evaluation]):
            self.stop_criteria.increment_counter()

            res = minimize(
                problem,
                algorithm,
                ("n_gen", 1),  # Run one generation at a time
                seed=self.thread_id,
                verbose=False,
            )

            # Get the best solution from this generation
            current_best_keys = res.X[np.argmin(res.F)]  # type: ignore
            current_solution = origin_pool.solutions[0].from_random_keys(
                current_best_keys
            )
            current_evaluation = self.evaluator.evaluate(current_solution)

            # Accept new solution if it improves the best solution
            if self.acceptance_criteria.accept(
                best_evaluation, current_evaluation, current_solution
            ):
                best_solution = current_solution.copy()
                best_evaluation = current_evaluation
                destination_pool.add_solution(best_solution)

        return destination_pool
