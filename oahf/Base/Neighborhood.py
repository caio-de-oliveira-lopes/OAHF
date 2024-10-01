from typing import Dict, List, Optional, Tuple, Type

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Movement import Movement
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Logger.LogManager import LogManager
from oahf.Utils.Util import Util


class Neighborhood:
    def __init__(
        self, stop_criteria: "StopCriteria", is_perturbation: bool = False
    ) -> None:
        """
        Initializes the Neighborhood object with the specified stop criteria and perturbation flag.

        Args:
            stop_criteria (StopCriteria): The stopping criteria for the neighborhood operations.
            is_perturbation (bool): A flag indicating if the neighborhood is a perturbation. Default is False.
        """
        super().__init__()
        self.report: "EfficiencyReport" = EfficiencyReport(type(self).__name__)
        self.stop_criteria: "StopCriteria" = stop_criteria
        self.is_perturbation: bool = is_perturbation

    def copy(self) -> "Neighborhood":
        """Abstract method to create a copy of the neighborhood."""
        raise NotImplementedError

    def build_neighborhood_operation(
        self, thread_id: int, solution: "Solution"
    ) -> bool:
        """
        Builds the neighborhood operation for the given solution and thread ID.

        Args:
            thread_id (int): The ID of the thread.
            solution (Solution): The solution to operate on.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        self.clear_related_keys()
        return self.build_neighborhood(thread_id, solution)

    def build_neighborhood(self, thread_id: int, solution: "Solution") -> bool:
        """Abstract method to build the neighborhood. To be implemented in subclasses."""
        raise NotImplementedError

    def get_move(self) -> "Movement":
        """Abstract method to get a movement. To be implemented in subclasses."""
        raise NotImplementedError

    def reset(self, solution: "Solution") -> None:
        """Resets the neighborhood for the given solution. Can be overridden by subclasses."""
        pass

    def accept_movement(self) -> None:
        """Accepts the movement and clears related keys."""
        self.clear_related_keys()

    def clear_related_keys(self) -> None:
        """Clears related keys. Can be overridden by subclasses."""
        pass

    def get_move_operation(self) -> Optional["Movement"]:
        """
        Gets the movement operation for the neighborhood.

        Returns:
            Movement: The movement if available; None otherwise.
        """
        if self.stop():
            return None

        self.report.report_move_search_start()

        move: Optional["Movement"] = None

        try:
            move = self.get_move()
        except Exception as ex:
            LogManager.invalid_action(
                "get movement, neighborhood", type(self).__name__, ex
            )
            raise

        self.report.report_move_search_end()
        return move

    def stop(self) -> bool:
        """Checks if the stopping criteria have been met."""
        return self.stop_criteria is not None and self.stop_criteria.stop()

    def get_efficiency_report(self) -> str:
        """Returns the efficiency report as a string."""
        return str(self.report)

    def get_efficiency_to_json(self) -> List[Tuple[int, "Event"]]:
        """Returns the efficiency report in JSON format."""
        return self.report.to_json()

    def get_constraints(self) -> Dict[Type["Constraint"], int]:
        """Returns the constraints associated with the efficiency report."""
        return self.report.get_constraints()

    def set_stop_criteria(self, stop: "StopCriteria") -> None:
        """Sets the stopping criteria for the neighborhood."""
        self.stop_criteria = stop
