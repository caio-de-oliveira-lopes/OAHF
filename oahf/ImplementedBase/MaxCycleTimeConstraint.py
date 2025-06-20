from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Solution import Solution


class MaxCycleTimeConstraint(Constraint):

    def evaluate(self, solution: "Solution", cache: bool) -> "ConstraintEvaluation":
        """
        Method to evaluate the max cycle time constraint based on a solution.
        :param solution: A Solution object (Alwabp).
        :return: A ConstraintEvaluation object.
        """
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

        if isinstance(solution, AlwabpSolution):
            penalty = 0.0

            if solution.unassigned_tasks:
                penalty = sum(
                    solution.get_task_execution_time(task) + 1
                    for task in solution.unassigned_tasks
                )

            if (
                solution.cycle_time_limit
                and solution.get_max_cycle_time() > solution.cycle_time_limit
            ):
                return self.infeasible_evaluation(penalty)
            else:
                return self.feasible_evaluation(penalty)
        else:
            return self.infeasible_evaluation()

    def infeasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, True, 0.0, penalty)

    def feasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, False, 0.0, penalty)

    @classmethod
    def multiply_penalty(cls, multiplier: float) -> None:
        """
        Adjust the penalty multiplier for the constraint violations.
        :param multiplier: Multiplier for the penalty value.
        """
        pass

    @classmethod
    def reset_penalty(cls) -> None:
        pass

    @classmethod
    def set_penalty(cls, value: float) -> None:
        """
        Set the penalty value for the constraint violations.
        :param value: Penalty value.
        """
        pass
