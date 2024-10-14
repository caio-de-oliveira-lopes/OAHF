from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.ALWABP import ALWABP
from oahf.Base.ThreadManager import ThreadManager
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.Movement import Movement
from abc import ABC
from typing import Iterator, Optional
from oahf.Logger.LogManager import LogManager
from oahf.ImplementedBase.ALWABPInsertOrderMove import ALWABPInsertOrderMove

class ALWABPInsertOrderNS(Neighborhood, ABC):
    def __init__(self, stop_criteria: StopCriteria, kseed: int = 0):
        super().__init__(stop_criteria)
        self.enumerator: Optional[Iterator[Movement]] = None
        self.solution: Optional[ALWABP] = None
        self.thread_id: int = 0
        self.kseed: int = kseed
        self.cost_function = None

    def build_neighborhood(self, thread_id: int, solution: ALWABP) -> bool:
        self.enumerator = self.all_moves()
        self.solution = solution
        self.thread_id = thread_id
        return True

    def get_move(self) -> Optional[Movement]:
        if not self.enumerator:
            return None
        try:
            return next(self.enumerator)
        except StopIteration:
            return None

    def all_moves(self) -> Iterator[Movement]:
        # Generate movements based on ALWABP context
        # This part should be updated based on how ALWABP assigns tasks to workers, etc.
        # For now, it contains a placeholder for task assignments.
        if self.solution:
            for worker in self.solution.unassigned_workers:
                for task in self.solution.get_available_tasks_to_assign_to_worker(worker):
                    # Generate insertion movements based on some logic (order, worker capability, etc.)
                    move = ALWABPInsertOrderMove(task, worker, self.solution, self.report)
                
                    # Assuming some cost evaluation function might be added here for ALWABP
                    if self.cost_function:
                        move.override_cost += self.cost_function(move)
                
                    yield move
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> 'ALWABPInsertOrderNS':
        return ALWABPInsertOrderNS(self.stop_criteria.copy(), self.kseed)
