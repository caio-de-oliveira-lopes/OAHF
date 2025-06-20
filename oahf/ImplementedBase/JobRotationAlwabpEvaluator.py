from typing import Optional, Type

from oahf.Base.Constraint import Constraint
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Evaluator import Evaluator
from oahf.ImplementedBase.JobRotationAlwabpEvaluation import JobRotationAlwabpEvaluation
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution


class JobRotationAlwabpEvaluator(Evaluator):
    def __init__(self, stop_on_first: bool = True, *constraints: "Constraint"):
        """
        Initializes an JobRotationAlwabpEvaluator with the option to stop on the first infeasibility.
        :param stop_on_first: Boolean indicating whether to stop on first infeasibility.
        :param constraints: Variable-length list of Constraint objects.
        """
        super().__init__(stop_on_first, *constraints)

    def evaluate(self, sol: Optional["JobRotationAlwabpSolution"], cache: bool = True) -> "Evaluation":
        """
        Abstract method to evaluate a Solution.
        :param sol: A Solution object to evaluate.
        :return: An Evaluation object.
        """
        if isinstance(sol, JobRotationAlwabpSolution):
            alwabp_sol = sol.period_solutions[0]
            max_possible_task = sum([len(alwabp_sol.tasks_executed_by_worker[w]) for w in alwabp_sol.workers])
            return JobRotationAlwabpEvaluation(
                (constraint.evaluate(sol, cache) for constraint in self._constraints),
                sol.calculate_total_distinct_tasks(),
                sol.get_average_cycle_time(),
                max_possible_task
            )
        else:
            return JobRotationAlwabpEvaluation((), int(0), float("inf"), int(1))

    def get_solution_type(self) -> Type[JobRotationAlwabpSolution]:
        return JobRotationAlwabpSolution
