import math
from typing import Dict, List, Tuple, Optional, Set
import heapq

from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.Evaluator import Evaluator
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import AlwaysAcceptAcceptanceCriteria

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
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
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
            AlwaysAcceptAcceptanceCriteria(),
            None,
            [],
            origin_pool,
            destination_pool,
        )
        # unique pattern lengths
        self.pattern_sizes: Set[int] = pattern_sizes
        # relative lower bound for pattern frequency [0, 1]
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

    def run_operation(self, origin_pool: Pool, destination_pool: Pool, parent: Optional["MetaHeuristic"] = None) -> Pool:
        from oahf.Base.Movement import Movement
        
        self.parent_metaheuristic = parent
        rng = ThreadManager.get_random_obj(self.thread_id)
        
        # Use first solution just to get extra data if needed
        example_sol = origin_pool.solutions[0]

        # Using default behavior when missing max_patterns_injected
        if self.max_patterns_injected is None:
            self.max_patterns_injected = example_sol.get_default_max_patterns_injected()

        # Using default behavior when missing pattern_sizes
        if len(self.pattern_sizes) == 0:
            self.pattern_sizes = example_sol.get_default_max_pattern_sizes()

        # Setting parent MetaHeuristic
        if self.local_search:
            self.local_search.named_parent = self
            self.local_search.parent_metaheuristic = self

        self.stop_criteria.reset()
        self.acceptance_criteria.reset()
        out_pool = destination_pool

        while not self.stop_on_evaluations([]):
            # snapshot to avoid self-modification
            origin_snapshot = origin_pool.copy()
            pool_size = origin_snapshot.count()

            # split elite vs regular
            n_elite = max(1, int(self.elite_threshold * pool_size))
            elite_sols = origin_snapshot.get_n_best(n_elite, self.evaluator)
            regular_sols = [s for s in origin_snapshot.solutions if s not in elite_sols]

            # Stoping check placed here to contemplate the time stop criteria
            if self.stop_on_evaluations([]):
                break

            # mine patterns separately
            self._mine_patterns(elite_sols, regular_sols, pool_size)

            # prepare output pool
            out_pool = destination_pool or origin_pool.copy()
            for solution in rng.sample(elite_sols, len(elite_sols)):

                # Stoping check placed here to contemplate the time stop criteria
                if self.stop_on_evaluations([]):
                    break

                # determine base injection counts
                base_elite = math.ceil(self.elite_injection_ratio * self.max_patterns_injected)
                base_regular = self.max_patterns_injected - base_elite
                for p in self.pattern_sizes:
                    e_candidates = list(self.elite_patterns[p])
                    r_candidates = list(self.regular_patterns[p])

                    # actual samples
                    use_elite = min(len(e_candidates), base_elite)
                    use_regular = min(len(r_candidates), base_regular)
                    # sample those
                    sampled_e = rng.sample(e_candidates, use_elite) if use_elite > 0 else []
                    sampled_r = rng.sample(r_candidates, use_regular) if use_regular > 0 else []

                    # if not enough regular, fill with additional elites
                    total_selected = use_elite + use_regular
                    if total_selected < self.max_patterns_injected:
                        remaining = self.max_patterns_injected - total_selected
                        # exclude already chosen elites
                        remaining_elite_pool = [p for p in e_candidates if p not in sampled_e]
                        extra = min(len(remaining_elite_pool), remaining)
                        sampled_e += rng.sample(remaining_elite_pool, extra) if extra > 0 else []

                    # Stoping check placed here to contemplate the time stop criteria
                    if self.stop_on_evaluations([]):
                        break

                    all_samples = sampled_e + sampled_r
                    # inject sampled elite patterns
                    for freq, pat in all_samples:
                        generated_moves: List[Movement] = solution.generate_moves_to_inject_pattern(pat)
                        for move in generated_moves:
                            if move.apply():

                                current_evaluation = self.evaluator.evaluate(solution)
                                if not (current_evaluation.infeasible() or current_evaluation.has_penalty()):
                                    out_pool.add_solution(solution.copy(), self)
                        
                                if self.local_search:
                                    improved_solution = self.local_search.run(solution)
                                    current_evaluation = self.evaluator.evaluate(improved_solution)
                                    if not (current_evaluation.infeasible() or current_evaluation.has_penalty()):
                                        out_pool.add_solution(improved_solution, self)

                                # Always unapply move to avoid unnecessary copies of solution object (can cause overhead)
                                move.unapply()

                            # Stoping check placed here to contemplate the time stop criteria
                            if self.stop_on_evaluations([]):
                                break

            # Increment stop_criteria counter only at the end
            self.stop_criteria.increment_counter()

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
            for p in self.pattern_sizes:
                for pat in sol.extract_patterns(p):
                    elite_counts[p][pat] = elite_counts[p].get(pat, 0) + 1

        # Stoping check placed here to contemplate the time stop criteria
        if self.stop_on_evaluations([]):
            return

        # so that elite_counts include both elite and regular occurrences for those patterns
        for sol in regular_solutions:
            for p in self.pattern_sizes:
                for pat in sol.extract_patterns(p):
                    if pat in elite_counts[p]:
                        # increment existing elite pattern count
                        elite_counts[p][pat] += 1
                    else:
                        # count for regular patterns (those never in elite)
                        reg_counts[p][pat] = reg_counts[p].get(pat, 0) + 1

        # build top-K mine heaps with frequency_lb filter
        min_freq = max(1, int(self.frequency_lb * pool_size))
        for p in self.pattern_sizes:

            # Stoping check placed here to contemplate the time stop criteria
            if self.stop_on_evaluations([]):
                return

            # elites
            heap_e: List[Tuple[int, Pattern]] = []
            for pat, freq in elite_counts[p].items():
                if freq < min_freq:
                    continue
                if self.max_patterns_mined is None or len(heap_e) < self.max_patterns_mined:
                    heapq.heappush(heap_e, (freq, pat))
                elif freq > heap_e[0][0]:
                    heapq.heapreplace(heap_e, (freq, pat))
            self.elite_patterns[p] = heap_e

            # regulars
            heap_r: List[Tuple[int, Pattern]] = []
            for pat, freq in reg_counts[p].items():
                if freq < min_freq:
                    continue
                if self.max_patterns_mined is None or len(heap_r) < self.max_patterns_mined:
                    heapq.heappush(heap_r, (freq, pat))
                elif freq > heap_r[0][0]:
                    heapq.heapreplace(heap_r, (freq, pat))
            self.regular_patterns[p] = heap_r