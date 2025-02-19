from collections import deque
from typing import Dict, Iterator, List, Optional, Tuple

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
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
        priority_matrix: Optional[Dict[int, List[int]]] = None
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
        self.priority_matrix = priority_matrix

    def build_neighborhood(self, thread_id: int, solution: AlwabpSolution, task_ordering_rule_dict: Optional[Dict[TaskOrderingRule, Dict[int, Tuple[float, ...]]]] = None) -> bool:
        """Prepares the neighborhood search by initializing the solution and computing initial station assignments."""

        solution.default_graph_orientation = self.graph_orientation

        rebuild = self.solution != solution
        self.solution = solution
        self.station = solution.get_first_unassigned_station()

        if not self.station:
            return False

        self.cost_function = solution.get_worker_min_rlb
        self.thread_id = thread_id
           
        if rebuild or task_ordering_rule_dict:
            self.task_ordering_rule_dict = task_ordering_rule_dict[self.task_ordering_rule] if task_ordering_rule_dict else self.compute_tasks_priority()[self.task_ordering_rule]

        self.enumerator = self.all_moves()
        return True

    def compute_tasks_priority(self) -> Dict[TaskOrderingRule, Dict[int, tuple[float, ...]]]:
        """Computes task priority based on the selected weight type, then updates with precedence values."""
        if not self.solution:
            raise ValueError(
                "No solution object was associated with this neighborhood search."
            )

        return self.solution.get_task_ordering_rules_dict(self.priority_matrix)

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
        if self.solution and self.station:
            worker_moves: Dict[int, MultipleMovement] = {}

            # Neighborhood will prioritize keeping workers at their respective stations
            worker_assigned_to_station = self.solution.station_worker_assignment[
                self.station
            ]
            worker_already_assigned = worker_assigned_to_station is not None
            if not worker_already_assigned:
                unassigned_workers = self.solution.unassigned_workers
            else:
                unassigned_workers = [worker_assigned_to_station]

            solution_copy = self.solution.copy()
            for unassigned_worker in unassigned_workers:
                
                worker_related_values = tuple(
                    self.task_ordering_rule_dict[task][unassigned_worker - 1] 
                    for task in self.task_ordering_rule_dict
                )
                c_min = min(worker_related_values)
                c_max = max(worker_related_values)
                self.threshold_value = c_min + ((1 - self.greediness) * (c_max - c_min))

                ordered_unassigned_tasks = sorted(
                    self.solution.unassigned_tasks, 
                    key=lambda task: worker_related_values[task - 1]
                )
                
                lcr = [
                    task
                    for task in ordered_unassigned_tasks
                    if worker_related_values[task - 1] <= self.threshold_value
                ]

                # Set up data structures for incremental update
                lcr_set = set(lcr)  # For quick membership tests and removals
                lcr_queue = deque(lcr)  # To preserve original ordering for filtering
                ordered_chosen_tasks = (
                    []
                )  # Will hold the tasks in the order they are chosen

                # Precompute the immediate precedences for the current orientation
                immediate_precedences = self.solution.immediate_task_precedences[
                    self.graph_orientation
                ]

                # Build a mapping of each task to the number of its unsatisfied prerequisites.
                # We count a prerequisite as "unsatisfied" if it is still in the solution unassigned tasks.
                unsatisfied_counts = {}
                for task in lcr_set:
                    prerequisites = immediate_precedences.get(task, [])
                    unsatisfied_counts[task] = sum(
                        1 for p in prerequisites if p in self.solution.unassigned_tasks
                    )

                # Build a reverse mapping: for each task, which tasks (from lcr_set) depend on it.
                dependents = {}
                for task in lcr_set:
                    for p in immediate_precedences.get(task, []):
                        # Only consider prerequisites that are also in lcr_set
                        if p in lcr_set:
                            dependents.setdefault(p, set()).add(task)

                # Initialize the set of available tasks: tasks whose unsatisfied count is zero.
                available_tasks = {
                    task for task, count in unsatisfied_counts.items() if count == 0
                }

                # 3. Incrementally select tasks using the available_tasks set
                while available_tasks:
                    # Filter lcr_queue to maintain the original order among tasks that are available.
                    filtered_lcr = [task for task in lcr_queue if task in available_tasks]
                    if not filtered_lcr:
                        break

                    # Select a task randomly (using your ThreadManager) among the available ones.
                    task_index = ThreadManager.get_next(
                        self.thread_id, 0, len(filtered_lcr) - 1
                    )
                    chosen_task = filtered_lcr[task_index]
                    ordered_chosen_tasks.append(chosen_task)

                    # Remove the chosen task from our data structures.
                    available_tasks.remove(chosen_task)
                    lcr_set.remove(chosen_task)
                    try:
                        lcr_queue.remove(chosen_task)
                    except ValueError:
                        pass  # Task already removed

                    # For every task that depends on the chosen task, decrement its unsatisfied count.
                    # If a count reaches zero, it becomes available.
                    for dependent in dependents.get(chosen_task, set()):
                        if dependent in lcr_set:
                            unsatisfied_counts[dependent] -= 1
                            if unsatisfied_counts[dependent] == 0:
                                available_tasks.add(dependent)

                # 4. If no tasks were chosen, return an empty iterator.
                if not ordered_chosen_tasks:
                    continue

                moves_executed_on_copy = []

                if not worker_already_assigned:
                    worker_move = AlwabpInsertionMovement(
                        None, unassigned_worker, self.station, solution_copy
                    )
                    if worker_move.apply():
                        moves_executed_on_copy.append(worker_move)

                for task in ordered_chosen_tasks:
                    if solution_copy.can_task_be_assigned_to(
                        task, self.station, unassigned_worker
                    ):
                        new_move = AlwabpInsertionMovement(
                            task, unassigned_worker, self.station, solution_copy
                        )
                        if new_move.apply():
                            moves_executed_on_copy.append(new_move)

                construction_composition = MultipleMovement(
                    solution_copy, moves_executed_on_copy
                )

                if moves_executed_on_copy:
                    move = construction_composition.copy(self.solution)
                    worker_moves[unassigned_worker] = move

                    # Calculate cost for the movement
                    if self.cost_function and not worker_already_assigned:
                        cost = self.cost_function(
                            unassigned_worker, solution_copy.unassigned_tasks
                        )
                        move.override_cost = (
                            move.override_cost + float(cost)
                            if move.override_cost
                            else float(cost)
                        )

                construction_composition.unapply()

            # Apply tiebreaker by preferring movements with more tasks when costs are equal
            sorted_moves = sorted(
                worker_moves.values(),
                key=lambda mv: (mv.override_cost, -len(mv.movements)),
            )

            # Reapply cost based on sorted order (list position + 1)
            for idx, movement in enumerate(sorted_moves, start=1):
                movement.override_cost = (
                    idx  # Change cost to consider the tiebreakers applied
                )
                yield movement
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> "AlwabpWorkerOrientedInsertNS":
        """Creates a copy of the current neighborhood search with the same settings."""
        return AlwabpWorkerOrientedInsertNS(
            self.task_ordering_rule,
            self.graph_orientation,
            self.greediness,
            self.priority_matrix
        )
