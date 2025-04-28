from typing import Dict, List, Tuple, Optional
import heapq

from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.Evaluator import Evaluator
from oahf.Base.ThreadManager import ThreadManager

# Define a pattern as a tuple of task IDs
Pattern = Tuple[int, ...]

class PILS(MetaHeuristic):
    """
    Pattern Injection Local Search.
    Mines frequent task-sequence patterns from elite solutions and injects them
    as high-order moves into current solutions.
    """
    def __init__(
        self,
        thread_id: int,
        stop_criteria,
        evaluator: Evaluator,
        acceptance_criteria,
        pattern_sizes: List[int],
        top_k: int = 50,
        injection_probability: float = 0.5,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
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
        self.pattern_sizes = pattern_sizes
        self.top_k = top_k
        self.injection_probability = injection_probability
        # Store mined patterns: size -> list of (frequency, pattern)
        self.patterns: Dict[int, List[Tuple[int, Pattern]]] = {p: [] for p in pattern_sizes}

    def copy(self, thread_id: int) -> "PILS":
        return PILS(
            thread_id,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.pattern_sizes,
            self.top_k,
            self.injection_probability,
            self.origin_pool.copy() if self.origin_pool else None,
            self.destination_pool.copy() if self.destination_pool else None,
        )

    def run(self, sol: Solution) -> Solution:
        """Runs the meta-heuristic on a single solution. Not implemented in this class."""
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(self, origin_pool: Pool, destination_pool: Pool) -> Pool:
        random_obj = ThreadManager.get_random_obj(self.thread_id)
        # 1) Mine patterns from the current pool of solutions
        self._mine_patterns(origin_pool.solutions)

        # 2) Inject patterns into each solution
        out_pool = destination_pool or origin_pool.copy()
        for sol in origin_pool.solutions:
            curr = sol.copy()
            best_eval = self.evaluator.evaluate(curr)

            # Try injecting patterns of each size
            for p in self.pattern_sizes:
                # Sample up to top_k patterns
                for freq, pat in random_obj.sample(self.patterns[p], min(len(self.patterns[p]), self.top_k)):
                    if ThreadManager.get_next_float(self.thread_id, 0, 1) > self.injection_probability:
                        continue
                    # Perform injection on a copy
                    candidate = curr.copy()
                    if hasattr(candidate, 'inject_pattern'):
                        success = candidate.inject_pattern(pat)
                        if success:
                            eval_c = self.evaluator.evaluate(candidate)
                            if self.acceptance_criteria.accept(best_eval, eval_c, candidate):
                                curr = candidate
                                best_eval = eval_c

            out_pool.add_solution(curr, self)
        return out_pool

    def _mine_patterns(self, solutions: List[Solution]) -> None:
        # Count pattern frequencies
        counters: Dict[int, Dict[Pattern, int]] = {p: {} for p in self.pattern_sizes}
        for sol in solutions:
            if hasattr(sol, 'extract_patterns'):
                for p in self.pattern_sizes:
                    pats = sol.extract_patterns(p)
                    for pat in pats:
                        counters[p][pat] = counters[p].get(pat, 0) + 1

        # Keep only top_k patterns per size using a min-heap
        for p in self.pattern_sizes:
            heap: List[Tuple[int, Pattern]] = []
            for pat, freq in counters[p].items():
                if len(heap) < self.top_k:
                    heapq.heappush(heap, (freq, pat))
                else:
                    if freq > heap[0][0]:
                        heapq.heapreplace(heap, (freq, pat))
            self.patterns[p] = heap
