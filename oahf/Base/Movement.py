import logging
from abc import ABC, abstractmethod
from typing import Optional
from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution

class Movement(Entity, ABC):
    logger = logging.getLogger(__name__)

    def __init__(self, solution: 'Solution', report: 'EfficiencyReport'):
        super().__init__()
        self.report: EfficiencyReport = report
        self.solution: Solution = solution

    @abstractmethod
    def get_cost(self) -> float:
        """Calculate and return the cost of the movement."""
        pass

    @abstractmethod
    def apply(self) -> bool:
        """Apply the movement to the solution."""
        pass

    def apply_operation(self) -> bool:
        """Wrapper method to apply the movement and report the outcome."""
        self.report.report_apply_start()
        result = False

        try:
            result = self.apply()
        except Exception as ex:
            self.logger.warning(f"Unable to apply movement, movement: {type(self).__name__}")
            self.logger.error(str(ex))
            raise

        if result:
            self.report.report_apply_end()
        else:
            self.report.report_apply_failed()
        return result

    def report_apply_improvement(self, new_evaluation: 'Evaluation', old_evaluation: 'Evaluation'):
        """Report an improvement when the movement is applied."""
        self.report.report_apply_improvement(new_evaluation, old_evaluation)

    @abstractmethod
    def unapply(self) -> bool:
        """Revert the movement on the solution."""
        pass

    def unapply_operation(self, evaluation: 'Evaluation') -> bool:
        """Wrapper method to unapply the movement and report the outcome."""
        self.report.report_unapply_start(evaluation)
        result = False

        try:
            result = self.unapply()
        except Exception as ex:
            self.logger.warning(f"Unable to unapply movement, movement: {type(self).__name__}")
            self.logger.error(str(ex))
            raise

        self.report.report_unapply_end()
        return result

    def set_unapply_inconsistent(self):
        """Indicate that the unapply operation is inconsistent."""
        raise NotImplementedError("Subclasses must implement this method.")
