from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.Base.ThreadManager import ThreadManager
from oahf.Base.StopCriteria import StopCriteria
from oahf.Base.Movement import Movement
from abc import ABC
from typing import Iterator, Optional
from oahf.Logger.LogManager import LogManager
from oahf.ImplementedBase.AlwabpInsertOrderMove import AlwabpInsertOrderMove
from oahf.ImplementedBase.AlwabpSolution import MaxPositionalWeightType

class AlwabpTaskInsertOrderNS(Neighborhood, ABC):
    def __init__(self, max_positional_weight_type: MaxPositionalWeightType, station: int, change_station: bool = True, greediness: float = 0, stop_criteria: Optional[StopCriteria] = None):
        super().__init__(stop_criteria, False)
        self.enumerator: Optional[Iterator[Movement]] = None
        self.solution: Optional[AlwabpSolution] = None
        self.station: int = station
        self.change_station: bool = change_station
        self.max_positional_weight_type = max_positional_weight_type
        self.thread_id: int = 0
        self.cost_function = None
        self.greediness: float = greediness

    def build_neighborhood(self, thread_id: int, solution: AlwabpSolution) -> bool:
        self.solution = solution
        
        if self.change_station:
            station = self.solution.get_first_unassigned_station()
            self.station = station if station else self.station
            
        self.thread_id = thread_id
        self.enumerator = self.all_moves()
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
        if self.solution:
            # Strategy for threshold
            max_positional_weight_list = self.solution.get_max_positional_weight_list(self.max_positional_weight_type)
            c_min = min(max_positional_weight_list)
            c_max = max(max_positional_weight_list)
            threshold_value = c_min + ((1 - self.greediness)*(c_max - c_min))
            
            lcr = [task for task in self.solution.unassigned_tasks 
                   if self.solution.get_max_positional_weight_value(task, self.max_positional_weight_type) 
                   <= threshold_value]
            
            for task in lcr:
                move = AlwabpInsertOrderMove(task, None, self.station, self.solution, self.report)
                
                # Assuming some cost evaluation function might be added here for ALWABP
                if self.cost_function:
                    move.override_cost += self.cost_function(move)
                
                yield move
        else:
            LogManager.invalid_action("generate movements", type(self).__name__)

    def copy(self) -> 'AlwabpTaskInsertOrderNS':
        return AlwabpTaskInsertOrderNS(self.max_positional_weight_type, self.station, self.greediness, self.stop_criteria.copy() if self.stop_criteria else None)
