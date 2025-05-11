import copy
from typing import Optional

from oahf.Base.Movement import Movement


class AlwabpInsertionMovement(Movement):
    __slots__ = ("task", "worker", "station", "override_cost")

    def __init__(
        self,
        task: Optional[int],
        worker: Optional[int],
        station: Optional[int],
        solution: "AlwabpSolution",
    ):
        super().__init__(solution)

        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

        self.solution: AlwabpSolution = solution
        self.task: Optional[int] = task
        self.worker: Optional[int] = worker
        self.station: Optional[int] = station
        self.override_cost: Optional[float] = None
        self._hash = None

    def get_cost(self) -> float:
        return self.override_cost if self.override_cost is not None else -1.0

    def apply(self) -> bool:
        if self.task and self.station:
            return self.solution.add_task_to_station(self.task, self.station)

        elif self.worker and self.station:
            return self.solution.add_worker_to_station(self.worker, self.station)

        return True

    def unapply(self) -> bool:
        # Implement logic to revert the movement in the ALWABP solution
        if self.task and self.station:
            return self.solution.remove_task_from_station(self.task, self.station)

        elif self.worker and self.station:
            return self.solution.remove_worker_from_station(self.worker, self.station)

        return True

    def __str__(self) -> str:
        return f"AlwabpInsertionMove(Task: {self.task}, Worker: {self.worker}, Station: {self.station})"

    def __deepcopy__(self, memo: dict) -> "AlwabpInsertionMovement":
        """
        Creates a deep copy of the AlwabpInsertionMovement instance.

        Args:
            memo (dict): Dictionary to store copied objects to prevent redundant copies.

        Returns:
            AlwabpInsertionMovement: A deep-copied instance of the movement.
        """
        cls = self.__class__
        copied_movement = cls.__new__(
            cls
        )  # Create a new instance without calling __init__

        copied_movement.get_new_id()

        # Manually copy attributes (minimizing deep copy overhead)
        copied_movement.task = self.task
        copied_movement.worker = self.worker
        copied_movement.station = self.station

        # Deep copy only when necessary
        copied_movement.solution = self.solution
        copied_movement.override_cost = self.override_cost
        copied_movement._hash = self._hash

        return copied_movement

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AlwabpInsertionMovement):
            return False
        return (
            self.task == other.task
            and self.worker == other.worker
            and self.station == other.station
        )

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash((self.task, self.worker, self.station))

        return self._hash

    def copy(
        self, new_solution: Optional["AlwabpSolution"] = None
    ) -> "AlwabpInsertionMovement":
        """
        Creates a copy of the current AlwabpInsertionMovement, optionally replacing the solution.

        Args:
            new_solution (Optional[AlwabpSolution]): A new solution to associate with the copied movement.
                If not provided, the current solution is used.

        Returns:
            AlwabpInsertionMovement: A new instance of AlwabpInsertionMovement with the same attributes,
            but optionally associated with a new solution.
        """
        new_move = copy.deepcopy(self)
        if new_solution:
            new_move.solution = new_solution

        return new_move
