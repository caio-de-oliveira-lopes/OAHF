import time
from typing import List, Dict, Tuple, Type, Optional
from oahf.Base.Event import *

class Event:
    class TYPE:
        SEARCH_START = "SEARCH_START"
        SEARCH_END = "SEARCH_END"
        APPLY_START = "APPLY_START"
        APPLY_END = "APPLY_END"
        UNNAPLY_START = "UNNAPLY_START"
        UNNAPLY_END = "UNNAPLY_END"

    def __init__(self, event_type: str) -> None:
        """
        Initializes an Event with the specified type.
        
        Args:
            event_type (str): The type of the event.
        """
        self.type: str = event_type
        self.constraints: Optional[List['ConstraintEvaluation']] = None
        self.objective_function: float = 0.0
        self.start_time: float = time.time() * 1000  # Current time in milliseconds

class EfficiencyReport:
    def __init__(self, name: str) -> None:
        """
        Initializes the EfficiencyReport with the specified name.
        
        Args:
            name (str): The name of the report.
        """
        self.name: str = name
        self.count_searches: int = 0
        self.count_apply: int = 0
        self.count_apply_failed: int = 0
        self.count_unapply: int = 0
        self.total_time_for_search: float = 0.0
        self.total_time_for_apply: float = 0.0
        self.total_time_for_unapply: float = 0.0
        self.constraint_per_unapply: Dict[Type['Constraint'], int] = {}
        self.unapply_no_constraint: int = 0
        self.events: List[Tuple[float, Event]] = []
        self.summed_improvement: float = 0.0

    def report_apply_improvement(self, new_eval: 'Evaluation', old_eval: 'Evaluation') -> None:
        """
        Reports the improvement after applying a new evaluation.
        
        Args:
            new_eval (Evaluation): The new evaluation.
            old_eval (Evaluation): The old evaluation.
        """
        improvement = new_eval.get_objective_function() - old_eval.get_objective_function()
        self.summed_improvement += improvement
        # Uncomment for detailed reporting
        # if self.events:  # Ensure there's at least one event
        #     self.events[-1][1].objective_function = improvement

    def report_apply_start(self) -> None:
        """Reports the start of the apply operation."""
        self.count_apply += 1
        self.events.append((time.time() * 1000, Event(Event.TYPE.APPLY_START)))  # Time in milliseconds
        self.start_time_apply = time.time()

    def report_apply_failed(self) -> None:
        """Reports a failed apply operation."""
        self.report_apply_end()
        self.count_apply_failed += 1

    def report_apply_end(self) -> None:
        """Reports the end of the apply operation."""
        self.total_time_for_apply += (time.time() - self.start_time_apply) * 1000  # Time in milliseconds
        self.events.append((time.time() * 1000, Event(Event.TYPE.APPLY_END)))

    def process_constraints(self, eval: 'Evaluation', event: Event) -> None:
        """Processes constraints related to the given evaluation."""
        constraints = eval.get_infeasible_constraints()
        if not constraints:
            self.unapply_no_constraint += 1
        event.constraints = constraints
        for constraint in constraints:
            if constraint.constraint_type not in self.constraint_per_unapply:
                self.constraint_per_unapply[constraint.constraint_type] = 0
            self.constraint_per_unapply[constraint.constraint_type] += 1

    def get_constraints(self) -> Dict[Type['Constraint'], int]:
        """Returns the constraints recorded in the report."""
        return self.constraint_per_unapply

    def report_unapply_start(self, evaluation: Optional['Evaluation']) -> None:
        """Reports the start of the unapply operation."""
        self.count_unapply += 1
        event = Event(Event.TYPE.UNNAPLY_START)
        if evaluation is not None:
            self.process_constraints(evaluation, event)
        self.events.append((time.time() * 1000, event))
        self.start_time_unapply = time.time()

    def report_unapply_end(self) -> None:
        """Reports the end of the unapply operation."""
        self.total_time_for_unapply += (time.time() - self.start_time_unapply) * 1000  # Time in milliseconds
        self.events.append((time.time() * 1000, Event(Event.TYPE.UNNAPLY_END)))

    def report_move_search_start(self) -> None:
        """Reports the start of the move search operation."""
        self.count_searches += 1
        self.events.append((time.time() * 1000, Event(Event.TYPE.SEARCH_START)))  # Time in milliseconds
        self.start_time_search = time.time()

    def report_move_search_end(self) -> None:
        """Reports the end of the move search operation."""
        self.total_time_for_search += (time.time() - self.start_time_search) * 1000  # Time in milliseconds
        self.events.append((time.time() * 1000, Event(Event.TYPE.SEARCH_END)))

    def to_json(self) -> List[Tuple[float, Event]]:
        """Converts the report's events to JSON format."""
        return self.events

    def __str__(self) -> str:
        """Returns a string representation of the efficiency report."""
        avg_improvement = (self.summed_improvement / (self.count_apply - self.count_unapply - self.count_apply_failed)) if (self.count_apply - self.count_unapply - self.count_apply_failed) > 0 else 0
        avg_search_time = (self.total_time_for_search / self.count_searches) if self.count_searches > 0 else 0
        avg_apply_time = (self.total_time_for_apply / self.count_apply) if self.count_apply > 0 else 0
        avg_unapply_time = (self.total_time_for_unapply / self.count_unapply) if self.count_unapply > 0 else 0
        constraints_summary = "\n".join(
            [f"Constraint {key} Times: {value}" for key, value in sorted(self.constraint_per_unapply.items(), key=lambda x: x[1])]
        )

        return (f"Report for {self.name}. Num. Searches: {self.count_searches}, Num. Apply: {self.count_apply}, "
                f"Num. Unapply: {self.count_unapply}.\n"
                f"Avg. Improvement: {avg_improvement}, Avg. Search Time: {avg_search_time}, "
                f"Avg. Apply Time: {avg_apply_time}, Avg. Unapply Time: {avg_unapply_time}.\n"
                f"Unapplied for non-constraint related reasons: {self.unapply_no_constraint}\n"
                f"{constraints_summary}")
