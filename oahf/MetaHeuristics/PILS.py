from typing import Dict, List, Tuple, Optional, Set
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
    Pattern Injection Local Search with elite vs. regular patterns.
    Mines frequent task combinations separately from an "elite" subset of solutions
    and the remainder, then injects a controlled mix into candidates.
    """
    def __init__(
        self,
        thread_id: int,
        stop_criteria,
        evaluator: Evaluator,
        acceptance_criteria,
        pattern_sizes: Set[int],
        frequency_lb: float,
        elite_threshold: float,
        elite_injection_ratio: float,
        max_patterns_mined: Optional[int] = None,
        max_patterns_injected: Optional[int] = None,
        local_search: Optional[MetaHeuristic] = None,
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
        # unique pattern lengths
        self.pattern_sizes: Set[int] = set(pattern_sizes)
        # relative lower bound for pattern frequency (0.0–1.0)
        self.frequency_lb = frequency_lb
        # fraction of pool to consider as elite
        self.elite_threshold = elite_threshold
        # fraction of injected patterns from elite set
        self.elite_injection_ratio = elite_injection_ratio
        # max patterns to mine (top-K by freq)
        self.max_patterns_mined = max_patterns_mined
        # max patterns to inject per solution
        self.max_patterns_injected = max_patterns_injected
        # optional local_search to improve solutions found
        self.local_search = local_search
        # patterns storage: size -> list of (freq, pattern)
        self.elite_patterns: Dict[int, List[Tuple[int, Pattern]]] = {p: [] for p in self.pattern_sizes}
        self.regular_patterns: Dict[int, List[Tuple[int, Pattern]]] = {p: [] for p in self.pattern_sizes}

    def copy(self, thread_id: int) -> "PILS":
        return PILS(
            thread_id,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.pattern_sizes,
            self.frequency_lb,
            self.elite_threshold,
            self.elite_injection_ratio,
            self.max_patterns_mined,
            self.max_patterns_injected,
            self.local_search,
            self.origin_pool.copy() if self.origin_pool else None,
            self.destination_pool.copy() if self.destination_pool else None,
        )

    def run(self, sol: Solution) -> Solution:
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(self, origin_pool: Pool, destination_pool: Pool) -> Pool:
        rng = ThreadManager.get_random_obj(self.thread_id)

        # snapshot to avoid self-modification
        origin_snapshot = origin_pool.copy()
        pool_size = len(origin_snapshot.solutions)

        # split elite vs regular
        n_elite = max(1, int(self.elite_threshold * pool_size))
        elite_sols = origin_snapshot.get_n_best(n_elite, self.evaluator)
        regular_sols = [s for s in origin_snapshot.solutions if s not in elite_sols]

        # mine patterns separately
        self._mine_patterns(elite_sols, regular_sols, pool_size)

        # prepare output pool
        out_pool = destination_pool or origin_pool.copy()
        for sol in origin_snapshot.solutions:

            # Using default behavior when missing max_patterns_injected
            if self.max_patterns_injected is None:
                self.max_patterns_injected = sol.get_default_max_patterns_injected()

            # injection counts
            elite_count = int(self.elite_injection_ratio * self.max_patterns_injected)
            regular_count = self.max_patterns_injected - elite_count
            for p in self.pattern_sizes:

                # sample elite patterns
                e_candidates = self.elite_patterns[p]
                for freq, pat in rng.sample(e_candidates, min(len(e_candidates), elite_count)):
                    candidate = sol.copy()
                    if candidate.inject_pattern(pat):
                        out_pool.add_solution(candidate, self)
                        
                        if self.local_search:
                            out_pool.add_solution(self.local_search.run(candidate), self)

                # sample regular patterns
                r_candidates = self.regular_patterns[p]
                for freq, pat in rng.sample(r_candidates, min(len(r_candidates), regular_count)):
                    candidate = sol.copy()
                    if candidate.inject_pattern(pat):
                        out_pool.add_solution(candidate, self)

                        if self.local_search:
                            out_pool.add_solution(self.local_search.run(candidate), self)
        return out_pool

    def _mine_patterns(
        self,
        elite_solutions: List[Solution],
        regular_solutions: List[Solution],
        pool_size: int
    ) -> None:
        # count frequencies
        elite_counts: Dict[int, Dict[Pattern, int]] = {p: {} for p in self.pattern_sizes}
        reg_counts: Dict[int, Dict[Pattern, int]] = {p: {} for p in self.pattern_sizes}

        # tally elite patterns
        for sol in elite_solutions:
            if hasattr(sol, 'extract_patterns'):
                for p in self.pattern_sizes:
                    for pat in sol.extract_patterns(p):
                        elite_counts[p][pat] = elite_counts[p].get(pat, 0) + 1

        # tally regular patterns (excluding elite)
        for sol in regular_solutions:
            if hasattr(sol, 'extract_patterns'):
                for p in self.pattern_sizes:
                    for pat in sol.extract_patterns(p):
                        if pat not in elite_counts[p]:
                            reg_counts[p][pat] = reg_counts[p].get(pat, 0) + 1

        # build top-K mine heaps with frequency_lb filter
        min_freq = lambda: max(1, int(self.frequency_lb * pool_size))
        for p in self.pattern_sizes:

            # elites
            heap_e: List[Tuple[int, Pattern]] = []
            for pat, freq in elite_counts[p].items():
                if freq < min_freq():
                    continue
                if self.max_patterns_mined is None or len(heap_e) < self.max_patterns_mined:
                    heapq.heappush(heap_e, (freq, pat))
                elif freq > heap_e[0][0]:
                    heapq.heapreplace(heap_e, (freq, pat))
            self.elite_patterns[p] = heap_e

            # regulars
            heap_r: List[Tuple[int, Pattern]] = []
            for pat, freq in reg_counts[p].items():
                if freq < min_freq():
                    continue
                if self.max_patterns_mined is None or len(heap_r) < self.max_patterns_mined:
                    heapq.heappush(heap_r, (freq, pat))
                elif freq > heap_r[0][0]:
                    heapq.heapreplace(heap_r, (freq, pat))
            self.regular_patterns[p] = heap_r