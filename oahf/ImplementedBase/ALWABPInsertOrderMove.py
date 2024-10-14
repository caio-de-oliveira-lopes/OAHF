from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Movement import Movement
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.ALWABP import ALWABP
from oahf.Utils.Util import Util
from typing import Optional


class ALWABPInsertOrderMove(Movement):
    def __init__(self, task: Optional[int], worker: Optional[int], station: Optional[int], solution: ALWABP, report: EfficiencyReport):
        super().__init__(solution, report)
        self.solution: ALWABP = solution
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
        # Implement logic to apply the movement in the ALWABP solution
        # e.g., reassign task to the worker and station in the solution
        return True

    def unapply(self) -> bool:
        # Implement logic to revert the movement in the ALWABP solution
        return True

    def __str__(self) -> str:
        return f"ALWABPInsertOrderMove(Task: {self.task}, Worker: {self.worker}, Station: {self.station})"

