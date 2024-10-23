from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Entity import Entity
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria


class MaxCycleTimeConstraint(Constraint):

    def evaluate(self, solution: "Solution") -> "ConstraintEvaluation":
        """
        Method to evaluate the max cycle time constraint based on a solution.
        :param solution: A Solution object (Alwabp).
        :return: A ConstraintEvaluation object.
        """
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

        if isinstance(solution, AlwabpSolution):
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
        return ConstraintEvaluation(self, True, penalty)

    def feasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, False, penalty)
