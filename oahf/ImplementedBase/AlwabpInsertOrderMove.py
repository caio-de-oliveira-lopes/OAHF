from typing import Optional

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Movement import Movement


class AlwabpInsertOrderMove(Movement):
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
        return f"AlwabpInsertOrderMove(Task: {self.task}, Worker: {self.worker}, Station: {self.station})"
