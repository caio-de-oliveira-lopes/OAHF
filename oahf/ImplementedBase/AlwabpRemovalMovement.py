from typing import Optional

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Movement import Movement


class AlwabpRemovalMovement(Movement):
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
            return self.solution.remove_task_from_station(self.task, self.station)

        if self.worker and self.station:
            return self.solution.remove_worker_from_station(self.worker, self.station)

        return True

    def unapply(self) -> bool:
        # Implement logic to revert the movement in the ALWABP solution
        if self.task and self.station:
            return self.solution.add_task_to_station(self.task, self.station)

        if self.worker and self.station:
            return self.solution.add_worker_to_station(self.worker, self.station)

        return True

    def __str__(self) -> str:
        return f"AlwabpRemovalMovement(Task: {self.task}, Worker: {self.worker}, Station: {self.station})"

    def copy(
        self, new_solution: Optional["AlwabpSolution"] = None
    ) -> "AlwabpRemovalMovement":
        """
        Creates a copy of the current AlwabpRemovalMovement, optionally replacing the solution.

        Args:
            new_solution (Optional[AlwabpSolution]): A new solution to associate with the copied movement.
                If not provided, the current solution is used.

        Returns:
            AlwabpRemovalMovement: A new instance of AlwabpRemovalMovement with the same attributes,
            but optionally associated with a new solution.
        """
        # Use the provided solution or retain the current one
        solution_to_use = new_solution if new_solution else self.solution

        # Create a new instance of AlwabpRemovalMovement
        copied_movement = AlwabpRemovalMovement(
            task=self.task,
            worker=self.worker,
            station=self.station,
            solution=solution_to_use,
            report=self.report,
        )

        # Copy additional attributes if needed
        copied_movement.override_cost = self.override_cost

        return copied_movement
