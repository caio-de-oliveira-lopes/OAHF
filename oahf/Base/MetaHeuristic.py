import logging
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from tqdm import tqdm

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Evaluator import Evaluator
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.ListPool import ListPool
from oahf.Logger.LogManager import LogManager


class MetaHeuristic(Entity, ABC):
    """
    MetaHeuristic serves as an abstract base class for implementing various metaheuristic optimization algorithms.
    It provides a structured framework for solution evaluation, neighborhood selection, and acceptance criteria
    while also handling stopping conditions and execution management.

    Attributes:
        logger (logging.Logger): Logger instance for logging events.
        thread_id (int): ID of the thread executing the heuristic.
        stop_criteria (StopCriteria): Stopping criteria for terminating the heuristic execution.
        evaluator (Evaluator): Evaluator used for assessing solution quality.
        acceptance_criteria (AcceptanceCriteria): Defines how new solutions are accepted.
        neighborhood_selection (Optional[NeighborhoodSelection]): Selection strategy for generating neighboring solutions.
        meta_heuristics_used (List[MetaHeuristic]): List of other metaheuristics used in combination with this one.
        origin_pool (Optional[Pool]): Pool of initial solutions.
        destination_pool (Optional[Pool]): Pool where optimized solutions are stored.
        parent_metaheuristic (Optional[MetaHeuristic]): Reference to a parent metaheuristic if applicable.
        log_solutions (bool): Flag indicating whether to log solutions.
        start_time (int): Timestamp when execution started.
        end_time (int): Timestamp when execution ended.
    """

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        thread_id: int,
        stop_criteria: "StopCriteria",
        evaluator: "Evaluator",
        acceptance_criteria: "AcceptanceCriteria",
        neighborhood_selection: Optional["NeighborhoodSelection"] = None,
        meta_heuristics_used: List["MetaHeuristic"] = [],
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
        super().__init__()
        self.neighborhood_selection: Optional["NeighborhoodSelection"] = (
            neighborhood_selection
        )
        self.thread_id: int = thread_id
        self.stop_criteria: "StopCriteria" = stop_criteria
        self.evaluator: "Evaluator" = evaluator
        self.acceptance_criteria: "AcceptanceCriteria" = acceptance_criteria
        self.meta_heuristics_used: List["MetaHeuristic"] = meta_heuristics_used
        self.origin_pool: Optional[Pool] = origin_pool
        self.destination_pool: Optional[Pool] = destination_pool
        self.parent_metaheuristic: Optional["MetaHeuristic"] = None
        self.log_solutions: bool = False
        self.start_time: int = 0
        self.end_time: int = 0

    @abstractmethod
    def run(self, sol: Solution) -> Solution:
        """Run the heuristic on a given solution."""
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
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

            for sol in origin_pool.get_list():
                result.add_solution(self.run(sol), self, False)

            self.end_time = self._current_milliseconds()
            return result
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            raise

    def stop(self) -> bool:
        """Check if the stopping criteria have been met."""
        return self.stop_criteria.stop() or (
            self.parent_metaheuristic is not None and self.parent_metaheuristic.stop()
        )

    def set_stop_criteria_report(self, perc_counter: float):
        """Update the stopping criteria progress report."""
        self.stop_criteria.set_progress_report(perc_counter)

    def set_log_solution(self):
        """Enable solution logging."""
        self.log_solutions = True

    def stop_on_evaluations(
        self, evs: Iterable["Evaluation"], pbar: Optional[tqdm] = None
    ) -> bool:
        """Determine if the heuristic should stop based on evaluations."""
        if evs is not None:
            stop = self.stop_criteria.stop_on_evaluations(evs) or (
                self.parent_metaheuristic is not None
                and self.parent_metaheuristic.stop_on_evaluations(evs, pbar)
            )
            if pbar and stop:
                pbar.close()

            return stop
        return False

    @abstractmethod
    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current MetaHeuristic instance."""
        pass

    def set_thread_id(self, thread_id: int):
        """Set the thread ID for the heuristic and its dependencies."""
        self.thread_id = thread_id
        for heuristic in self.meta_heuristics_used:
            heuristic.set_thread_id(thread_id)

    def reset_neighborhoods(self, sol: "Solution"):
        """Reset all neighborhood structures based on the given solution."""
        if self.neighborhood_selection:
            for neighborhood in self.neighborhood_selection.get_all():
                neighborhood.reset(sol)

    def get_neighborhood_selection(self) -> Optional["NeighborhoodSelection"]:
        """Retrieve the neighborhood selection strategy."""
        return self.neighborhood_selection

    def get_stop_criteria(self) -> "StopCriteria":
        """Retrieve the stopping criteria object."""
        return self.stop_criteria

    @staticmethod
    def _current_milliseconds() -> int:
        """Utility method to get current time in milliseconds."""
        import time

        return int(round(time.time() * 1000))
