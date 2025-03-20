from typing import List, Optional

import numpy as np
from pymoo.algorithms.soo.nonconvex.brkga import BRKGA as PymooBRKGA
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from tqdm import tqdm

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.Logger.LogManager import LogManager


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
        self.local_seach: Optional[MetaHeuristic] = None
        self.use_progress_bar = (
            isinstance(stop_criteria, StopTimeIterationCriteria)
            and stop_criteria.max_iterations is not None
        )

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
        """Runs the meta-heuristic on a single solution. Not implemented in this class."""
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(self, origin_pool: Pool, destination_pool: Pool) -> Pool:
        """Executes the meta-heuristic with external control, optimized for computational efficiency."""

        # Cache frequently used attributes
        evaluator = self.evaluator
        acceptance = self.acceptance_criteria
        stop_criteria = self.stop_criteria
        thread_id = self.thread_id
        use_progress_bar = self.use_progress_bar
        local_search = self.local_seach
        population_size = self.population_size
        name = self.name

        # Randomly generate initial population
        example_sol = origin_pool.get_solution_at(0)
        initial_population = type(example_sol).generate_random_keys(
            thread_id, example_sol, population_size
        )

        # Problem definition for Pymoo
        class PymooProblem(Problem):
            def __init__(
                self,
                evaluator: Evaluator,
                local_search: Optional[MetaHeuristic],
                origin_solution: Solution,
                initial_population: List[List[float]],
            ):
                super().__init__(
                    n_var=len(initial_population[0]), n_obj=1, xl=0.0, xu=1.0
                )
                self.evaluator = evaluator
                self.local_search = local_search
                self.origin_solution = (
                    origin_solution  # A representative solution from the origin pool.
                )
                self.cache = {}  # Dictionary for memoization.

            def _make_hashable(self, key):
                """
                Converts the key into a hashable form.
                If key is a numpy array, it is converted to a tuple of its elements.
                """
                if isinstance(key, np.ndarray):
                    # Convert to tuple. Alternatively, you could use key.tobytes() if preferred.
                    return tuple(key.tolist())
                return key

            def get_solution_from_key(self, key):
                """
                Retrieves the solution corresponding to the given key from the cache.
                If it's not in the cache, computes it and stores it.
                """
                hashable_key = self._make_hashable(key)
                if hashable_key not in self.cache:
                    self.cache[hashable_key] = self.origin_solution.from_random_key(
                        key, self.local_search, self.evaluator
                    )
                return self.cache[hashable_key]

            def _evaluate(self, X, out, *args, **kwargs):
                # Compute solutions using memoization.
                solutions = [self.get_solution_from_key(key) for key in X]
                # Evaluate each solution and extract the objective function value.
                out["F"] = np.array(
                    [
                        self.evaluator.evaluate(sol).get_objective_function()
                        for sol in solutions
                    ]
                )

        problem = PymooProblem(evaluator, local_search, example_sol, initial_population)

        # Initialize BRKGA algorithm
        algorithm = CustomBRKGA(
            pop_size=population_size,
            elite_frac=self.elite_fraction,
            mutant_frac=self.mutant_fraction,
            bias=self.bias,
        )

        # External loop control
        stop_criteria.reset()
        acceptance.reset()

        best_solution = origin_pool.get_best(evaluator)
        best_evaluation = evaluator.evaluate(best_solution)

        pbar = None
        if use_progress_bar:
            max_iterations = stop_criteria.max_iterations  # type: ignore
            pbar = tqdm(
                total=max_iterations, desc=f"{name} Progress", position=0, leave=False
            )

        while not self.stop_on_evaluations([best_evaluation], pbar):
            stop_criteria.increment_counter(pbar)

            # Run a single generation of BRKGA
            res = minimize(
                problem, algorithm, ("n_gen", 1), seed=thread_id, verbose=False
            )

            if res.opt:
                # Get the best solution from this generation
                best_idx = np.argmin(res.F)  # type: ignore
                best_key = res.opt.get("X")[best_idx]
                current_solution = origin_pool.solutions[0].from_random_key(
                    best_key, local_search, evaluator
                )
                current_evaluation = evaluator.evaluate(current_solution)

                destination_pool.add_solution(current_solution, self)

                # Accept new solution if it improves the best one
                if acceptance.accept(
                    best_evaluation, current_evaluation, current_solution
                ):
                    best_solution = current_solution.copy()
                    best_evaluation = current_evaluation
            else:
                LogManager.something_went_wrong(str(BRKGA), "res.opt is None")

        return destination_pool


class CustomBRKGA(PymooBRKGA):
    def __init__(
        self, pop_size=100, elite_frac=0.2, mutant_frac=0.1, bias=0.0, **kwargs
    ):
        # Calculate numbers based on your intended pop_size
        n_elites = int(pop_size * elite_frac)
        n_mutants = int(pop_size * mutant_frac)
        n_offsprings = pop_size - n_elites - n_mutants

        # Instead of passing pop_size to the super class (which leads to conflict),
        # we call the super constructor without the pop_size parameter.
        super().__init__(
            elite_frac=elite_frac, mutant_frac=mutant_frac, bias=bias, **kwargs
        )

        # Then override the internal population size attributes if needed.
        self.n_elites = n_elites
        self.n_mutants = n_mutants
        self.n_offsprings = n_offsprings
        self.pop_size = pop_size  # Use your intended total pop_size
