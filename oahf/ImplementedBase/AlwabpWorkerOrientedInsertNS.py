from collections import deque
from typing import Dict, Iterator, List, Optional

from oahf.Base.Movement import Movement
from oahf.Base.MultipleMovement import MultipleMovement
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
from oahf.ImplementedBase.AlwabpSolution import (
    AlwabpSolution,
    GraphOrientation,
    MaxPositionalWeightType,
)
from oahf.Logger.LogManager import LogManager


class AlwabpWorkerOrientedInsertNS(Neighborhood):
    def __init__(
        self,
        max_positional_weight_type: MaxPositionalWeightType,
        graph_orientation: GraphOrientation,
        greediness: float = 0,
        priority_matrix: Optional[List[List[int]]] = None,
        stop_criteria: Optional[StopCriteria] = None,
    ):
        """Initializes the neighborhood search for ALWABP, setting configuration parameters for worker-oriented task insertion."""
        super().__init__(stop_criteria, False)
        self.enumerator: Optional[Iterator[Movement]] = None
        self.solution: Optional[AlwabpSolution] = None
        self.thread_id: int = 0
        self.cost_function = None
        self.max_positional_weight_type = max_positional_weight_type
        self.graph_orientation = graph_orientation
        self.station: Optional[int] = None
        self.greediness: float = greediness
        self.priority_matrix = priority_matrix

    def build_neighborhood(self, thread_id: int, solution: AlwabpSolution) -> bool:
        """Prepares the neighborhood search by initializing the solution and computing initial station assignments."""

        solution.default_graph_orientation = self.graph_orientation

        self.solution = solution
        self.station = solution.get_first_unassigned_station()

        if not self.station:
            return False

        self.cost_function = solution.get_worker_min_rlb
        self.thread_id = thread_id
        self.enumerator = self.all_moves()
        return True

    def compute_tasks_priority(self) -> Dict[int, float]:
        """Computes task priority based on the selected weight type, then updates with precedence values."""
        if not self.solution:
            raise ValueError(
                "No solution object was associated with this neighborhood search."
            )

        if not self.priority_matrix:
            return self.solution.get_max_positional_weight_dict(
                self.max_positional_weight_type
            )

        # Step 1: Compute initial priorities without precedences
        task_priorities = {
            task: self.get_task_priority_without_precedences(task)
            for task in self.solution.tasks
        }

        # Step 2: Add precedence values in a second pass
        for task in self.solution.tasks:
            precedences = self.solution.all_task_precedences[
                self.graph_orientation
            ].get(task, [])
            task_priorities[task] += sum(task_priorities[pred] for pred in precedences)

        return task_priorities

    def get_task_priority_without_precedences(self, task: int) -> float:
        """Computes the priority of a task based on worker priorities only, without precedences."""
        if not self.solution or not self.priority_matrix:
            return 0.0

        workers_priorities = [
            self.priority_matrix[w][task - 1]
            for w in range(self.solution._number_of_workers)
        ]

        if self.max_positional_weight_type == MaxPositionalWeightType.MIN:
            return min(workers_priorities)

        if self.max_positional_weight_type == MaxPositionalWeightType.MAX:
            return max(workers_priorities)

        if self.max_positional_weight_type == MaxPositionalWeightType.AVERAGE:
            return sum(workers_priorities) / self.solution._number_of_workers

        raise ValueError("Invalid max positional weight type.")

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

            # Determine the task list based on positional weights and greediness
            max_positional_weight_dict = self.compute_tasks_priority()
            c_min = min(max_positional_weight_dict.values())
            c_max = max(max_positional_weight_dict.values())
            threshold_value = c_min + ((1 - self.greediness) * (c_max - c_min))

            # Filter tasks within the threshold
            lcr = [
                task
                for task in self.solution.unassigned_tasks
                if max_positional_weight_dict[task] <= threshold_value
            ]

            # Generate movements for tasks that are still available
            lcr_set = set(lcr)  # Convert to set for faster lookup
            lcr_queue = deque(lcr)  # Using deque for efficient removals
            ordered_chosen_tasks = []

            while available_tasks := set(
                self.solution.get_available_tasks_to_assign_to_station(
                    self.station, lcr_set
                )
            ):
                filtered_lcr = [task for task in lcr_queue if task in available_tasks]

                if not filtered_lcr:
                    break

                # Select a task (randomly but efficiently)
                task_index = ThreadManager.get_next(
                    self.thread_id, 0, len(filtered_lcr) - 1
                )
                task = filtered_lcr[task_index]
                ordered_chosen_tasks.append(task)

                # Update lists after each move
                lcr_set.remove(task)
                lcr_queue.remove(
                    task
                )  # `deque.remove()` is still `O(n)`, but avoids full list reconstruction

            if not ordered_chosen_tasks:
                return iter([])  # Return an empty iterator if no moves are generated

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
            self.max_positional_weight_type,
            self.graph_orientation,
            self.greediness,
            self.priority_matrix,
            self.stop_criteria.copy() if self.stop_criteria else None,
        )
