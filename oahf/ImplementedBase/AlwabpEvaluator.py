from typing import Optional
from oahf.Base.Constraint import Constraint
from oahf.Base.Evaluator import Evaluator
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.Base.Evaluation import Evaluation
from oahf.ImplementedBase.AlwabpEvaluation import AlwabpEvaluation


class AlwabpEvaluator(Evaluator):
    def __init__(self, stop_on_first: bool = True, *constraints: "Constraint"):
        """
        Initializes an AlwabpEvaluator with the option to stop on the first infeasibility.
        :param stop_on_first: Boolean indicating whether to stop on first infeasibility.
        :param constraints: Variable-length list of Constraint objects.
        """
        super().__init__(stop_on_first, *constraints)

    def evaluate(self, sol: Optional["AlwabpSolution"]) -> "Evaluation":
        """
        Abstract method to evaluate a Solution.
        :param sol: A Solution object to evaluate.
        :return: An Evaluation object.
        """
        if sol:
            return AlwabpEvaluation((constraint.evaluate(sol) for constraint in self._constraints), 
                                    sol.get_max_cycle_time(), len(sol.unassigned_tasks), len(sol.unassigned_workers))
        else:
            return AlwabpEvaluation((), float('inf'), int('inf'), int('inf'))