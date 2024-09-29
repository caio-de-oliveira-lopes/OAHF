from abc import ABC, abstractmethod
from typing import Iterable

class StopCriteria(ABC):
    def __init__(self) -> None:
        self._progress_report: bool = False

    @abstractmethod
    def stop(self) -> bool:
        """Determines whether the stopping criteria have been met."""
        pass

    def increment_counter(self) -> None:
        """Increments the internal counter and prints the progress report if enabled."""
        if self._progress_report:
            self.print_progress_report()

    def reset(self) -> None:
        """Resets the stopping criteria."""
        pass

    def stop_on_evaluations(self, evaluations: Iterable['Evaluation']) -> bool:
        """Checks if the stopping criteria are met based on evaluations.

        Args:
            evaluations (Iterable[Evaluation]): The evaluations to check against.

        Returns:
            bool: True if stopping criteria are met; otherwise, False.
        """
        return self.stop()

    def set_progress_report(self, perc_counter: float) -> None:
        """Enables progress reporting.

        Args:
            perc_counter (float): The percentage of completion.
        """
        self._progress_report = True

    def get_progress(self) -> float:
        """Gets the current progress.

        Returns:
            float: The current progress percentage.
        """
        return 0.0

    def print_progress_report(self) -> None:
        """Prints the progress report if stopping criteria are met."""
        if self.stop():
            print("Finished")

    def current_status(self) -> str:
        """Returns the current status of the stop criteria.

        Returns:
            str: A string representing the current status.
        """
        return f"Time: {ThreadManager.Watch.ElapsedMilliseconds};"

    @abstractmethod
    def copy(self) -> 'StopCriteria':
        """Creates a copy of the stop criteria instance."""
        pass
