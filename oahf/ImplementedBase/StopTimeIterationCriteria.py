import time
from typing import Optional

from oahf.Base.StopCriteria import StopCriteria


class StopTimeIterationCriteria(StopCriteria):
    def __init__(
        self, seconds: Optional[float] = None, iterations: Optional[int] = None
    ):
        """
        Initializes a StopTimeIterationCriteria instance.
        :param seconds: The maximum time allowed for the process in seconds.
        :param iterations: The maximum number of iterations.
        """
        self.sw_start = time.time()
        self.milliseconds = int(seconds * 1000) if seconds is not None else None
        self.counter = 0
        self.max_iterations = iterations
        self.perc_progress_counter = 0

    def copy(self) -> "StopCriteria":
        """Creates a copy of the current StopTimeIterationCriteria instance."""
        return StopTimeIterationCriteria(
            seconds=None if self.milliseconds is None else self.milliseconds / 1000,
            iterations=self.max_iterations,
        )

    def set_progress_report(self, perc_counter: float) -> None:
        """Sets the progress report based on the current percentage counter."""
        if self.max_iterations is not None:
            self.perc_progress_counter = int(perc_counter * self.max_iterations)
            super().set_progress_report(perc_counter)

    def print_progress_report(self) -> None:
        """Prints the progress report if conditions are met."""
        if self.progress_report and (
            self.max_iterations is not None
            and self.counter
            % (
                self.perc_progress_counter
                if self.perc_progress_counter != 0
                else self.perc_progress_counter + 1
            )
            == 0
        ):
            print(f"{(self.counter / self.max_iterations) * 100:.2f}% progress")

    def current_status(self) -> str:
        """Returns the current status of the stopping criteria."""
        status = super().current_status()
        if self.milliseconds is not None:
            elapsed_time = int((time.time() - self.sw_start) * 1000)
            status += (
                f"time: {elapsed_time} - {elapsed_time / self.milliseconds * 100:.2f}%;"
            )
        if self.max_iterations is not None:
            status += f"iteration: {self.counter} - {self.counter / self.max_iterations * 100:.2f};"
        return status

    def stop(self) -> bool:
        """Determines if the stopping criteria have been met."""
        elapsed_time = int((time.time() - self.sw_start) * 1000)
        return (self.milliseconds is not None and elapsed_time > self.milliseconds) or (
            self.max_iterations is not None and self.counter > self.max_iterations
        )

    def increment_counter(self) -> None:
        """Increments the counter for iterations."""
        self.counter += 1
        super().increment_counter()

    def get_progress(self) -> float:
        """Returns the current progress as a fraction of the maximum iterations."""
        return (
            self.counter / self.max_iterations
            if self.max_iterations is not None
            else 0.0
        )

    def reset(self) -> None:
        """Resets the stopping criteria."""
        self.counter = 0
        self.sw_start = time.time()

    def elapsed_time(self) -> str:
        """Returns the elapsed time as a string."""
        elapsed = time.time() - self.sw_start
        return str(elapsed)
