from abc import ABC, abstractmethod
from typing import Optional

from oahf.Base.EfficiencyReport import EfficiencyReport
from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution
from oahf.Logger.LogManager import LogManager


class Movement(Entity, ABC):
    def __init__(self, solution: "Solution", report: "EfficiencyReport"):
        super().__init__()
        self.report: EfficiencyReport = report
        self.solution: Solution = solution
        self._tabu_counter_over_iterations: float = 0.25

    @property
    def tabu_counter_over_iterations(self) -> float:
        return self._tabu_counter_over_iterations

    @tabu_counter_over_iterations.setter
    def tabu_counter_over_iterations(self, value: float) -> None:
        self._tabu_counter_over_iteartions = value

    @abstractmethod
    def get_cost(self) -> float:
        """Calculate and return the cost of the movement."""
        pass

    @abstractmethod
    def apply(self) -> bool:
        """Apply the movement to the solution."""
        pass

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        """
        Check equality between two Movement instances.

        Args:
            other (object): The other instance to compare.

        Returns:
            bool: True if equal, False otherwise.
        """
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """
        Generate a hash for the Movement instance.

        Returns:
            int: The hash value.
        """
        pass

    def apply_operation(self) -> bool:
        """Wrapper method to apply the movement and report the outcome."""
        self.report.report_apply_start()
        result = False

        try:
            result = self.apply()
        except Exception as ex:
            LogManager.invalid_action("apply movement", type(self).__name__, ex)
            raise

        if result:
            self.report.report_apply_end()
        else:
            self.report.report_apply_failed()
        return result

    def report_apply_improvement(
        self, new_evaluation: "Evaluation", old_evaluation: "Evaluation"
    ):
        """Report an improvement when the movement is applied."""
        self.report.report_apply_improvement(new_evaluation, old_evaluation)

    @abstractmethod
    def unapply(self) -> bool:
        """Revert the movement on the solution."""
        pass

    def unapply_operation(self, evaluation: Optional["Evaluation"]) -> bool:
        """Wrapper method to unapply the movement and report the outcome."""
        self.report.report_unapply_start(evaluation)
        result = False

        try:
            result = self.unapply()
        except Exception as ex:
            LogManager.invalid_action("unapply movement", type(self).__name__, ex)
            raise

        self.report.report_unapply_end()
        return result

    def set_unapply_inconsistent(self):
        """Indicate that the unapply operation is inconsistent."""
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def copy(self, new_solution: Optional["Solution"] = None) -> "Movement":
        """
        Creates a copy of the current Movement object, optionally replacing the solution.

        Args:
            new_solution (Optional[Solution]): A new solution to associate with the copied movement.
                If not provided, the current solution is used.

        Returns:
            Movement: A new instance of the same Movement type, with the same attributes
            but optionally associated with a new solution.
        """
        # Use the provided solution or default to the current one
        solution_to_use = new_solution if new_solution else self.solution

        # Create a new instance of the same type
        new_instance = type(self)(solution=solution_to_use, report=self.report)

        # Copy any additional attributes if needed (in case of subclass extensions)
        for attr in vars(self):
            if attr not in {
                "solution",
                "report",
            }:  # Avoid overwriting explicitly set attributes
                setattr(new_instance, attr, getattr(self, attr))

        return new_instance
