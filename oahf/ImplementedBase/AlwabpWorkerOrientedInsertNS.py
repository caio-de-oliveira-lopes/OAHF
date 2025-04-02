import bisect
from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Tuple

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpSolution import (
    AlwabpSolution,
    GraphOrientation,
    TaskOrderingRule,
)
from oahf.Logger.LogManager import LogManager


class AlwabpWorkerOrientedInsertNS(Neighborhood):
    def __init__(
        self,
        task_ordering_rule: TaskOrderingRule,
        graph_orientation: GraphOrientation,
        greediness: float = 0,
    ):
        """Initializes the neighborhood search for ALWABP, setting configuration parameters for worker-oriented task insertion."""
        super().__init__(False)
        self.enumerator: Optional[Iterator[Movement]] = None
        self.solution: Optional[AlwabpSolution] = None
        self.thread_id: int = 0
        self.cost_function = None
        self.task_ordering_rule = task_ordering_rule
        self.graph_orientation = graph_orientation
        self.station: Optional[int] = None
        self.greediness: float = greediness
        self.task_ordering_rule_dict: Optional[Dict[int, Tuple[float, ...]]] = None

    def set_task_ordering_rule_dict(
        self, task_ordering_rule_dict: Dict[int, Tuple[float, ...]]
    ) -> None:
        self.task_ordering_rule_dict = task_ordering_rule_dict

    def build_neighborhood(
        self,
        thread_id: int,
        solution: AlwabpSolution,
    ) -> bool:
        """Prepares the neighborhood search by initializing the solution and computing initial station assignments."""

        solution.default_graph_orientation = self.graph_orientation

        rebuild = self.solution != solution
        self.solution = solution
        self.station = solution.get_first_unassigned_station()

        if not self.station:
            return False

        self.cost_function = solution.get_worker_min_rlb
        self.thread_id = thread_id

        if rebuild:
            if not self.task_ordering_rule_dict:
                priorities = self.compute_tasks_priority()
                self.task_ordering_rule_dict = priorities[self.task_ordering_rule]
                self.first_tiebreaker = priorities[TaskOrderingRule.MAX_IF]
            else:
                self.first_tiebreaker = self.task_ordering_rule_dict

        self.enumerator = self.all_moves()
        return True

    def compute_tasks_priority(
        self,
    ) -> Dict[TaskOrderingRule, Dict[int, tuple[float, ...]]]:
        """Computes task priority based on the selected weight type, then updates with precedence values."""
        if not self.solution:
            raise ValueError(
                "No solution object was associated with this neighborhood search."
            )

        return self.solution.get_task_ordering_rules_dict()

    def get_move(self) -> Optional[Movement]:
        """Retrieves the next available movement in the neighborhood search."""
        if not self.enumerator:
            return None
        try:
            return next(self.enumerator)
        except StopIteration:
            return None

    def all_moves(self) -> Iterator[Movement]:
        """
        Generates all possible movements based on ALWABP context, filtering tasks according to a greediness threshold.
        It considers available tasks and workers, attempting to minimize cycle time violations.
        In case multiple movements have the same cost, the movement with fewer tasks will be preferred as a tiebreaker.
        After sorting, cost is reapplied based on the position in the sorted list.
        """
        if not (self.solution and self.station and self.task_ordering_rule_dict):
            LogManager.invalid_action("generate movements", type(self).__name__)
            return

        worker_moves = {}
        solution = self.solution
        station = self.station
        worker_assigned = solution.station_worker_assignment[station]
        worker_already_assigned = worker_assigned is not None
        if not worker_already_assigned:
            unassigned_workers = solution.unassigned_workers
        else:
            unassigned_workers = [worker_assigned]

        solution_unassigned_tasks = solution.unassigned_tasks
        # Precompute set for unassigned tasks for faster membership tests
        unassigned_tasks_set = set(solution_unassigned_tasks)
        graph_orient = self.graph_orientation
        immediate_precedences = solution.immediate_task_precedences[graph_orient]
        task_order_rule = self.task_ordering_rule_dict
        first_tiebreaker = self.first_tiebreaker
        solution_copy = solution.copy()

        for worker in unassigned_workers:
            # Compute worker related values once for the current worker
            w_idx = worker - 1
            worker_related_values = tuple(
                task_order_rule[task][w_idx] for task in task_order_rule
            )
            tiebreaker_rule = tuple(
                first_tiebreaker[task][w_idx] for task in task_order_rule
            )
            c_min = min(worker_related_values)
            c_max = max(worker_related_values)
            threshold_value = c_min + ((1 - self.greediness) * (c_max - c_min))
            self.threshold_value = threshold_value

            # Filter unassigned tasks first then sort; this should reduce sorting overhead
            filtered_tasks = [
                t
                for t in solution_unassigned_tasks
                if worker_related_values[t - 1] <= threshold_value
            ]
            ordered_tasks = sorted(
                filtered_tasks,
                key=lambda t: (
                    worker_related_values[t - 1],  # primary factor
                    tiebreaker_rule[
                        t - 1
                    ],  # first tiebreaker (used if primary factor is equal)
                    solution_copy.get_task_execution_time(
                        t, worker
                    ),  # second tiebreaker
                    t,  # fourth factor (the task itself)
                ),
            )
            lcr = ordered_tasks

            # Data structures for incremental update
            lcr_set = set(lcr)
            lcr_list = list(lcr)  # Preserve original ordering
            ordered_chosen_tasks = []

            # Compute unsatisfied prerequisite counts using unassigned_tasks_set
            unsatisfied_counts = {
                t: sum(
                    1
                    for p in immediate_precedences.get(t, [])
                    if p in unassigned_tasks_set
                )
                for t in lcr_set
            }

            # Build reverse mapping (dependents) using defaultdict for tasks in lcr_set
            dependents = defaultdict(set)
            for t in lcr_set:
                for p in immediate_precedences.get(t, []):
                    if p in lcr_set:
                        dependents[p].add(t)

            # Initialize available tasks as those with zero unsatisfied prerequisites
            available_tasks = {t for t, cnt in unsatisfied_counts.items() if cnt == 0}

            # Precompute index mapping to preserve original ordering
            index_map = {t: i for i, t in enumerate(lcr_list)}
            # Maintain parallel lists for available tasks and their positions to avoid recomputing order
            available_in_order = [t for t in lcr_list if t in available_tasks]
            available_positions = [
                index_map[t] for t in lcr_list if t in available_tasks
            ]

            # Incrementally select tasks while available tasks exist
            while available_tasks:
                if not available_in_order:
                    break

                # Select a task randomly among the available ones using ThreadManager
                task_index = ThreadManager.get_next(
                    self.thread_id, 0, len(available_in_order) - 1
                )
                # Select the first element of the list
                # task_index = 0

                chosen_task = available_in_order.pop(task_index)
                available_positions.pop(task_index)
                ordered_chosen_tasks.append(chosen_task)
                available_tasks.remove(chosen_task)
                lcr_set.remove(chosen_task)

                # For each task that depends on the chosen task, update its unsatisfied count and add if available
                for dependent in dependents.get(chosen_task, set()):
                    if dependent in lcr_set:
                        unsatisfied_counts[dependent] -= 1
                        if unsatisfied_counts[dependent] == 0:
                            available_tasks.add(dependent)
                            pos = index_map[dependent]
                            # Insert dependent into available_in_order preserving original order using available_positions
                            insert_index = bisect.bisect_left(available_positions, pos)
                            available_positions.insert(insert_index, pos)
                            available_in_order.insert(insert_index, dependent)

            if not ordered_chosen_tasks:
                continue

            moves_executed = []
            if not worker_already_assigned:
                worker_move = AlwabpInsertionMovement(
                    None, worker, station, solution_copy
                )
                if worker_move.apply():
                    moves_executed.append(worker_move)

            for t in ordered_chosen_tasks:
                if solution_copy.can_task_be_assigned_to(t, station, worker):
                    new_move = AlwabpInsertionMovement(
                        t, worker, station, solution_copy
                    )
                    if new_move.apply():
                        moves_executed.append(new_move)

            construction = MultipleMovement(solution_copy, moves_executed)
            if (worker_already_assigned and len(moves_executed) > 0) or (not worker_already_assigned and len(moves_executed) > 1):
                move = construction.copy(solution)
                worker_moves[worker] = move
                if self.cost_function and not worker_already_assigned:
                    cost = self.cost_function(worker, solution_copy.unassigned_tasks)
                    move.override_cost = (
                        (move.override_cost + float(cost))
                        if move.override_cost
                        else float(cost)
                    )

            construction.unapply()

        sorted_moves = sorted(
            worker_moves.values(), key=lambda mv: (mv.override_cost, -len(mv.movements))
        )

        for idx, movement in enumerate(sorted_moves, start=1):
            movement.override_cost = idx
            yield movement

    def copy(self) -> "AlwabpWorkerOrientedInsertNS":
        """Creates a copy of the current neighborhood search with the same settings."""
        return AlwabpWorkerOrientedInsertNS(
            self.task_ordering_rule, self.graph_orientation, self.greediness
        )
