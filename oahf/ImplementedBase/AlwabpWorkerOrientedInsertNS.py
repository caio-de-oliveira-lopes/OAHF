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
    
    def compute_task_priority(self, task: int) -> float:
        """Computes task priority based on the selected weight type, using the priority matrix if available."""
        if self.solution:
            if not self.priority_matrix:
                return self.solution.get_max_positional_weight_list(self.max_positional_weight_type)[task - 1]
        
            workers_priorities = [self.priority_matrix[w][task - 1] for w in range(len(self.priority_matrix))]
        
            if self.max_positional_weight_type == MaxPositionalWeightType.MIN:
                min_predecessor_value = min(
                    [self.compute_task_priority(pred) for pred in self.solution.all_task_precedences[self.graph_orientation][task]],
                    default=0
                )
                return min(workers_priorities) + min_predecessor_value

            elif self.max_positional_weight_type == MaxPositionalWeightType.MAX:
                max_predecessor_value = max(
                    [self.compute_task_priority(pred) for pred in self.solution.all_task_precedences[self.graph_orientation][task]],
                    default=0
                )
                return max(workers_priorities) + max_predecessor_value

            elif self.max_positional_weight_type == MaxPositionalWeightType.AVERAGE:
                return sum(workers_priorities) / len(workers_priorities)

        return 0  # Fallback case

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
            max_positional_weight_list = [self.compute_task_priority(task) for task in self.solution.tasks]
            c_min = min(max_positional_weight_list)
            c_max = max(max_positional_weight_list)
            threshold_value = c_min + ((1 - self.greediness) * (c_max - c_min))

            # Filter tasks within the threshold
            lcr = [
                task
                for task in self.solution.unassigned_tasks
                if max_positional_weight_list[task - 1] <= threshold_value
            ]
            available_tasks = self.solution.get_available_tasks_to_assign_to_station(
                self.station, lcr
            )
            ordered_chosen_tasks = []

            # Generate movements for tasks that are still available
            while available_tasks:
                filtered_lcr = [task for task in lcr if task in available_tasks]

                if not filtered_lcr:
                    break

                # Randomly select a task using thread-specific randomization
                task = filtered_lcr[
                    ThreadManager.get_next(self.thread_id, 0, len(filtered_lcr) - 1)
                ]
                ordered_chosen_tasks.append(task)

                # Update lists after each move
                lcr.remove(task)
                available_tasks = (
                    self.solution.get_available_tasks_to_assign_to_station(
                        self.station, lcr
                    )
                )

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
                        None,
                        unassigned_worker,
                        self.station,
                        solution_copy,
                        self.report,
                    )
                    if worker_move.apply():
                        moves_executed_on_copy.append(worker_move)

                for task in ordered_chosen_tasks:
                    if solution_copy.can_task_be_assigned_to(
                        task, self.station, unassigned_worker
                    ):
                        new_move = AlwabpInsertionMovement(
                            task,
                            unassigned_worker,
                            self.station,
                            solution_copy,
                            self.report,
                        )
                        if new_move.apply():
                            moves_executed_on_copy.append(new_move)

                construction_composition = MultipleMovement(
                    solution_copy, self.report, moves_executed_on_copy
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
