from typing import Iterable, LinkedList, Optional

from oahf.Base.Evaluation import Evaluation
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria


class StopNoImprovement(StopTimeIterationCriteria):
    def __init__(
        self,
        seconds: Optional[float],
        iterations: Optional[int],
        iterations_no_improv: int,
        perc_improv: Optional[float],
    ):
        """
        Initializes a StopNoImprovement instance.
        :param seconds: The maximum time allowed for the process.
        :param iterations: The maximum number of iterations.
        :param iterations_no_improv: The number of iterations without improvement before stopping.
        :param perc_improv: The percentage improvement required.
        """
        super().__init__(seconds, iterations)
        self.ofs: LinkedList[float] = LinkedList()
        self.iterations_no_improv = iterations_no_improv
        self.perc_improvement = (
            perc_improv if perc_improv is not None else float("epsilon")
        )
        self.last_evaluation: Optional[Evaluation] = None

    def stop(self) -> bool:
        """Determines if the stopping criteria have been met."""
        return super().stop()

    def copy(self) -> StopCriteria:
        """Creates a copy of the current StopNoImprovement instance."""
        return StopNoImprovement(
            self.seconds,
            self.max_iterations,
            self.iterations_no_improv,
            self.perc_improvement,
        )

    def stop_on_evaluations(self, evaluations: Iterable[Evaluation]) -> bool:
        """Checks if the stopping criteria are met based on evaluations."""
        eval = next(iter(evaluations))  # Get the first evaluation
        self.last_evaluation = eval
        if len(self.ofs) >= self.iterations_no_improv:
            if abs(self.ofs[0] / self.ofs[-1] - 1) <= self.perc_improvement:
                return True
        return self.stop()

    def current_status(self) -> str:
        """Returns the current status of the stopping criteria."""
        status = super().current_status()
        if len(self.ofs) > 1:
            improvement = self.ofs[0] / self.ofs[-1] - 1
            status += f"improvement: {improvement};"
        return status

    def increment_counter(self) -> None:
        """Increments the counter for evaluations."""
        if self.last_evaluation is not None:
            self.ofs.append(self.last_evaluation.get_objective_function())
            if len(self.ofs) > self.iterations_no_improv:
                self.ofs.pop(0)  # Remove the first element
        super().increment_counter()

    def reset(self) -> None:
        """Resets the stopping criteria."""
        super().reset()
