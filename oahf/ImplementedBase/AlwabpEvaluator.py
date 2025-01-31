from typing import Optional, Type

from oahf.Base.Constraint import Constraint
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpEvaluation import AlwabpEvaluation
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation


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
            dgo = sol.default_graph_orientation

            sol.default_graph_orientation = GraphOrientation.FORWARD

            solution_eval = AlwabpEvaluation(
                (constraint.evaluate(sol) for constraint in self._constraints),
                sol.get_max_cycle_time(),
                sol.cycle_time_limit,
                len(sol.unassigned_tasks),
                len(sol.unassigned_workers),
                sol.get_number_of_critical_workstations(),
            )

            sol.default_graph_orientation = dgo

            return solution_eval
        else:
            return AlwabpEvaluation(
                (), float("inf"), None, int("inf"), int("inf"), int("inf")
            )

    def get_solution_type(self) -> Type[Solution]:
        return AlwabpSolution
