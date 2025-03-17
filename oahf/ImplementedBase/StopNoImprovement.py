from typing import Iterable, List, Optional

from tqdm import tqdm

from oahf.Base.Evaluation import Evaluation
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria


class StopNoImprovement(StopTimeIterationCriteria):
    def __init__(
        self,
        iterations_no_improv: int,
        seconds: Optional[float] = None,
        iterations: Optional[int] = None,
        perc_improv: Optional[float] = None,
    ):
        """
        Initializes a StopNoImprovement instance.
        :param iterations_no_improv: The number of iterations without improvement before stopping.
        :param seconds: The maximum time allowed for the process.
        :param iterations: The maximum number of iterations.
        :param perc_improv: The percentage improvement required.
        """
        super().__init__(seconds, iterations)
        self.ofs: List[float] = []
        self.iterations_no_improv = iterations_no_improv
        self.perc_improvement: Optional[float] = perc_improv
        self.last_evaluation: Optional[Evaluation] = None

    def stop(self) -> bool:
        """Determines if the stopping criteria have been met."""
        return super().stop()

    def copy(self) -> StopCriteria:
        """Creates a copy of the current StopNoImprovement instance."""
        return StopNoImprovement(
            self.iterations_no_improv,
            self.seconds,
            self.max_iterations,
            self.perc_improvement,
        )

    def stop_on_evaluations(self, evaluations: Iterable[Evaluation]) -> bool:
        """Checks if the stopping criteria are met based on evaluations."""
        evaluation = next(iter(evaluations))  # Get the first evaluation
        self.last_evaluation = evaluation
        ofs_size = len(self.ofs)
        if ofs_size > self.iterations_no_improv:
            if self.perc_improvement:
                if (
                    abs((self.ofs[0] / self.ofs[ofs_size - 1]) - 1)
                    <= self.perc_improvement
                ):
                    return True
                else:
                    self.stop()
            else:
                if self.ofs[ofs_size - 2] <= self.ofs[ofs_size - 1]:
                    return True
                else:
                    self.stop()
        return self.stop()

    def current_status(self) -> str:
        """Returns the current status of the stopping criteria."""
        status = super().current_status()
        ofs_size = len(self.ofs)
        if ofs_size > 1:
            improvement = self.ofs[0] / self.ofs[ofs_size - 1] - 1
            status += f" improvement: {improvement};"
        return status

    def increment_counter(self, pbar: Optional[tqdm] = None) -> None:
        """Increments the counter for evaluations."""
        if self.last_evaluation is not None:
            self.ofs.append(self.last_evaluation.get_objective_function())
            if len(self.ofs) > self.iterations_no_improv + 1:
                self.ofs.pop(0)  # Remove the first element
        super().increment_counter(pbar)

    def reset(self) -> None:
        """Resets the stopping criteria."""
        super().reset()
        self.ofs.clear()  # Clear the objective function values
