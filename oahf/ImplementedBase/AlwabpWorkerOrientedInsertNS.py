from oahf.Base.Neighborhood import Neighborhood
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.Base.ThreadManager import ThreadManager
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.Movement import Movement
from typing import Iterator, Optional, List, Dict
from oahf.Logger.LogManager import LogManager
from oahf.ImplementedBase.AlwabpInsertOrderMove import AlwabpInsertOrderMove
from oahf.ImplementedBase.AlwabpSolution import MaxPositionalWeightType
from oahf.ImplementedBase.AlwabpSolution import GraphOrientation
from oahf.Base.MultipleMovement import MultipleMovement


class AlwabpWorkerOrientedInsertNS(Neighborhood):
    def __init__(self, max_positional_weight_type: MaxPositionalWeightType, graph_orientation: GraphOrientation, greediness: float = 0, stop_criteria: Optional[StopCriteria] = None):
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

    def build_neighborhood(self, thread_id: int, solution: AlwabpSolution) -> bool:
        """Prepares the neighborhood search by initializing the solution and computing initial station assignments."""
        self.solution = solution
        self.station = solution.get_first_unassigned_station() or self.station
        self.cost_function = solution.get_worker_min_rlb
        self.thread_id = thread_id
        self.enumerator = self.all_moves()
        return True

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
            max_positional_weight_list = self.solution.get_max_positional_weight_list(self.max_positional_weight_type)
            c_min = min(max_positional_weight_list)
            c_max = max(max_positional_weight_list)
            threshold_value = c_min + ((1 - self.greediness) * (c_max - c_min))

            # Filter tasks within the threshold
            lcr = [task for task in self.solution.unassigned_tasks if max_positional_weight_list[task - 1] <= threshold_value]
            available_tasks = self.solution.get_available_tasks_to_assign_to_station(self.station, self.graph_orientation, lcr)
            all_moves: List[AlwabpInsertOrderMove] = []

            # Generate movements for tasks that are still available
            while available_tasks:
                filtered_lcr = [task for task in lcr if task in available_tasks]

                if not filtered_lcr:
                    break

                # Randomly select a task using thread-specific randomization
                task = filtered_lcr[ThreadManager.get_next(self.thread_id, 0, len(filtered_lcr) - 1)]
                all_moves.append(AlwabpInsertOrderMove(task, None, self.station, self.solution, self.report))

                # Update lists after each move
                lcr.remove(task)
                available_tasks = self.solution.get_available_tasks_to_assign_to_station(self.station, self.graph_orientation, lcr)

            if not all_moves:
                return iter([])  # Return an empty iterator if no moves are generated

            for unassigned_worker in self.solution.unassigned_workers:
                feasible_movements = self.solution.simulate_worker_tasks_allocation(unassigned_worker, all_moves)
                if feasible_movements:
                    chosen_tasks = {move.task for move in feasible_movements}
                    unassigned_tasks = [task for task in self.solution.unassigned_tasks if task not in chosen_tasks]

                    worker_move = AlwabpInsertOrderMove(None, unassigned_worker, self.station, self.solution, self.report)
                    feasible_movements.append(worker_move)

                    move = MultipleMovement(self.solution, self.report, feasible_movements)

                    worker_moves[unassigned_worker] = move

                    # Calculate cost for the movement
                    if self.cost_function:
                        cost = self.cost_function(unassigned_worker, unassigned_tasks)
                        move.override_cost = move.override_cost + float(cost) if move.override_cost else float(cost)

            # Apply tiebreaker by preferring movements with more tasks when costs are equal
            sorted_moves = sorted(worker_moves.values(), key=lambda mv: (mv.override_cost, -len(mv.movements)))

            # Reapply cost based on sorted order (list position + 1)
            for idx, movement in enumerate(sorted_moves, start=1):
                movement.override_cost = idx  # Change cost to consider the tiebreakers applied
                yield movement
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)


    def copy(self) -> 'AlwabpWorkerOrientedInsertNS':
        """Creates a copy of the current neighborhood search with the same settings."""
        return AlwabpWorkerOrientedInsertNS(self.max_positional_weight_type, self.graph_orientation, self.greediness, self.stop_criteria.copy() if self.stop_criteria else None)
