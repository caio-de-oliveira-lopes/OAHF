from typing import Optional

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Movement import Movement

class AlwabpInsertionMovement(Movement):
    def __init__(
        self,
        task: Optional[int],
        worker: Optional[int],
        station: Optional[int],
        solution: "AlwabpSolution",
        report: EfficiencyReport,
    ):
        super().__init__(solution, report)

        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

        self.solution: AlwabpSolution = solution
        self.task: Optional[int] = task
        self.worker: Optional[int] = worker
        self.station: Optional[int] = station
        self.override_cost: Optional[float] = None

    def get_cost(self) -> float:
        if self.override_cost is not None:
            return self.override_cost

        # Placeholder cost calculation logic, should be updated with ALWABP-specific logic
        return -1.0

    def apply(self) -> bool:
        if self.task and self.station:
            return self.solution.add_task_to_station(self.task, self.station)

        if self.worker and self.station:
            return self.solution.add_worker_to_station(self.worker, self.station)

        return True

    def unapply(self) -> bool:
        # Implement logic to revert the movement in the ALWABP solution
        if self.task and self.station:
            return self.solution.remove_task_from_station(self.task, self.station)

        if self.worker and self.station:
            return self.solution.remove_worker_from_station(self.worker, self.station)

        return True

    def __str__(self) -> str:
        return f"AlwabpInsertionMove(Task: {self.task}, Worker: {self.worker}, Station: {self.station})"

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
        # Use the provided solution or retain the current one
        solution_to_use = new_solution if new_solution else self.solution

        # Create a new instance of AlwabpInsertionMovement
        copied_movement = AlwabpInsertionMovement(
            task=self.task,
            worker=self.worker,
            station=self.station,
            solution=solution_to_use,
            report=self.report,
        )

        # Copy additional attributes if needed
        copied_movement.override_cost = self.override_cost

        return copied_movement

    def __eq__(self, other: object) -> bool:
        """
        Checks equality between two AlwabpInsertionMovement instances.
        Equality is based on task, worker, station, and solution reference.

        Args:
            other (object): Another object to compare.

        Returns:
            bool: True if the objects are equal, False otherwise.
        """
        if not isinstance(other, AlwabpInsertionMovement):
            return False

        return (
            self.task == other.task
            and self.worker == other.worker
            and self.station == other.station
        )

    def __hash__(self) -> int:
        """
        Returns a hash value for the AlwabpInsertionMovement instance.
        The hash is based on task, worker, station, and solution reference.

        Returns:
            int: Hash value for the instance.
        """
        return hash((self.task, self.worker, self.station))
