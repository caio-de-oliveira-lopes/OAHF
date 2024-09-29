import logging
from abc import ABC, abstractmethod

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Entity import Entity
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Utils.Util import Util


class CrossOver(Entity, ABC):
    def __init__(self, stop_criteria: "StopCriteria") -> None:
        """
        Initializes the CrossOver with the given stopping criteria.

        Args:
            stop_criteria (StopCriteria): The stopping criteria for the crossover.
        """
        super().__init__()
        self.report = EfficiencyReport(self.__class__.__name__.split(".")[-1])
        self.stop_criteria = stop_criteria

    @abstractmethod
    def copy(self, thread: int) -> "CrossOver":
        """Creates a copy of the current CrossOver instance."""
        pass

    @abstractmethod
    def cross(self, sol1: "Solution", sol2: "Solution") -> "Solution":
        """Performs the crossover operation between two solutions."""
        pass

    def cross_operation(self, sol1: "Solution", sol2: "Solution") -> "Solution":
        """
        Executes the crossover operation if the stopping criteria are not met.

        Args:
            sol1 (Solution): The first solution.
            sol2 (Solution): The second solution.

        Returns:
            Solution: The new solution created from the crossover.
        """
        if self.stop():
            return None

        self.report.report_move_search_start()
        new_sol = None

        try:
            new_sol = self.cross(sol1, sol2)
        except Exception as ex:
            Util.logger.error(
                f"Unable to do cross-over, neighborhood: {self.__class__.__name__}\n{ex}"
            )
            raise

        self.report.report_move_search_end()
        return new_sol

    def stop(self) -> bool:
        """Checks whether the stopping criteria are met."""
        return self.stop_criteria is not None and self.stop_criteria.stop()

    def get_efficiency_report(self) -> str:
        """Returns the efficiency report as a string."""
        return str(self.report)
