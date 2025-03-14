from typing import Optional

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.StopCriteria import StopCriteria
from oahf.MetaHeuristics.BRKGA import BRKGA


class HGA(BRKGA):
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
        local_search: MetaHeuristic,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ) -> None:
        """Initialize the Hybrid Genetic Algorithm (HGA) extending BRKGA.

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
            local_search (MetaHeuristic): Local search method to be used in hybridization.
        """
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            population_size,
            elite_fraction,
            mutant_fraction,
            bias,
            origin_pool,
            destination_pool,
        )
        self.local_search = local_search

    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current HGA instance, including local search."""
        return HGA(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.population_size,
            self.elite_fraction,
            self.mutant_fraction,
            self.bias,
            self.local_search.copy(thread),  # Ensuring local search is copied
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )
