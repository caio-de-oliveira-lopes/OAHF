import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.EfficiencyReport import Event
from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class MetaHeuristicReport:
    def __init__(self, name: str):
        self.name: str = name
        self.report: List[Tuple[int, "Event"]] = []
        self.reports: List["MetaHeuristicReport"] = []
        self.start_time: int = 0
        self.end_time: int = 0


class SolutionReport:
    def __init__(self):
        self.best_solutions: List[Tuple[str, float]] = []
        self.current_solutions: List[Tuple[str, float]] = []
        self.name: str = ""
        self.start_time: int = 0
        self.end_time: int = 0


class MetaHeuristic(Entity, ABC):
    logger = logging.getLogger(__name__)

    def __init__(
        self,
        thread_id: int,
        stop_criteria: "StopCriteria",
        evaluator: "Evaluator",
        neighborhood_selection: Optional["NeighborhoodSelection"] = None,
        acceptance_criteria: Optional["AcceptanceCriteria"] = None,
        meta_heuristics_used: Optional[
            Union["MetaHeuristic", List["MetaHeuristic"]]
        ] = None,
    ):

        super().__init__()
        self.neighborhood_selection: Optional["NeighborhoodSelection"] = (
            neighborhood_selection
        )
        self.evaluator: "Evaluator" = evaluator
        self.thread_id: int = thread_id
        self.stop_criteria: "StopCriteria" = stop_criteria
        self.parent_metaheuristic: Optional["MetaHeuristic"] = None
        self.meta_heuristics_used: List["MetaHeuristic"] = (
            meta_heuristics_used
            if isinstance(meta_heuristics_used, list)
            else [meta_heuristics_used] if meta_heuristics_used else []
        )
        self.acceptance_criteria: Optional["AcceptanceCriteria"] = acceptance_criteria
        self.solution_reports: SolutionReport = SolutionReport()
        self.log_solutions: bool = False
        self.start_time: int = 0
        self.end_time: int = 0

    def get_efficiency_reports(self) -> Optional[List[Tuple[type, str]]]:
        if self.neighborhood_selection is None:
            return None
        else:
            return [
                (type(x), x.get_efficiency_report())
                for x in self.neighborhood_selection.get_all()
            ]

    def get_efficiency_reports_to_json(self) -> MetaHeuristicReport:
        report = MetaHeuristicReport(self.__class__.__name__)
        report.start_time = self.start_time
        report.end_time = self.end_time

        if self.neighborhood_selection is None:
            report.reports = [
                x.get_efficiency_reports_to_json() for x in self.meta_heuristics_used
            ]
        else:
            report.reports = [
                MetaHeuristicReport(y.__class__.__name__, y.get_efficiency_to_json())
                for y in self.neighborhood_selection.get_all()
            ]

        return report

    def print_efficiency_reports(self):
        if self.neighborhood_selection is None:
            print(f"MetaHeuristic: {self.__class__}")
            print("------------")
            for meta in self.meta_heuristics_used:
                meta.print_efficiency_reports()
                print("------------")
        else:
            reports = self.get_efficiency_reports()
            for r in reports:
                print(f"{r[0]} {r[1]}")

    @abstractmethod
    def run(self, sol: "Solution") -> "Solution":
        """Run the heuristic on a given solution."""
        pass

    def run_operation(
        self, sol: "Pool", parent: Optional["MetaHeuristic"] = None
    ) -> "Pool":
        try:
            self.parent_metaheuristic = parent
            self.stop_criteria.reset()
            if self.neighborhood_selection:
                self.neighborhood_selection.reset(self.thread_id)

            self.start_time = self._current_milliseconds()
            result = self.run(sol)
            self.end_time = self._current_milliseconds()
            return result
        except Exception as ex:
            self.logger.warning(
                f"Something went wrong while trying to run {self.__class__}"
            )
            self.logger.error(str(ex))
            raise

    def stop(self) -> bool:
        return self.stop_criteria.stop() or (
            self.parent_metaheuristic is not None and self.parent_metaheuristic.stop()
        )

    def set_stop_criteria_report(self, perc_counter: float):
        self.stop_criteria.set_progress_report(perc_counter)

    def log_best_solution(self, eval: "Evaluation"):
        if self.log_solutions:
            self.solution_reports.best_solutions.append(
                (self.stop_criteria.current_status(), eval.get_objective_function())
            )

    def log_current_solution(self, eval: "Evaluation"):
        if self.log_solutions:
            self.solution_reports.current_solutions.append(
                (self.stop_criteria.current_status(), eval.get_objective_function())
            )

    def get_solution_reports(self) -> SolutionReport:
        self.solution_reports.name = self.__class__.__name__
        self.solution_reports.start_time = self.start_time
        self.solution_reports.end_time = self.end_time
        return self.solution_reports

    def set_log_solution(self):
        self.log_solutions = True

    def stop_on_evaluations(self, ev: "Evaluation") -> bool:
        return self.stop_on_evaluations([ev])

    def stop_on_evaluations(self, evs: List["Evaluation"]) -> bool:
        return self.stop_criteria.stop_on_evaluations(evs) or (
            self.parent_metaheuristic is not None
            and self.parent_metaheuristic.stop_on_evaluations(evs)
        )

    @abstractmethod
    def copy(self, thread: int) -> "MetaHeuristic":
        """Creates a copy of the current MetaHeuristic instance."""
        pass

    def set_thread_id(self, thread_id: int):
        self.thread_id = thread_id
        if self.meta_heuristics_used:
            for n in self.meta_heuristics_used:
                n.set_thread_id(thread_id)

    def reset_neighborhoods(self, sol: "Solution"):
        for neighborhood in self.neighborhood_selection.get_all():
            neighborhood.reset(sol)

    @abstractmethod
    def set_neighborhood(self, neighborhood: "Neighborhood"):
        pass

    def get_neighborhood_selection(self) -> Optional["NeighborhoodSelection"]:
        return self.neighborhood_selection

    def get_stop_criteria(self) -> "StopCriteria":
        return self.stop_criteria

    @staticmethod
    def _current_milliseconds() -> int:
        """Utility method to get current time in milliseconds."""
        import time

        return int(round(time.time() * 1000))
