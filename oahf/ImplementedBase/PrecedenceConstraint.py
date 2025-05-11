from typing import Dict

from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class PrecedenceConstraint(Constraint):
    _penalty = 60.0  # Default penalty value; can be adjusted.
    _precedence_violations_memo: Dict[int, int] = {}

    def evaluate(self, solution: "Solution", cache: bool) -> "ConstraintEvaluation":
        """
        Method to evaluate the precedence constraint based on a solution.
        :param solution: A Solution object (AlwabpSolution).
        :return: A ConstraintEvaluation object.
        """

        if isinstance(solution, AlwabpSolution):
            number_of_violations = self.count_precedence_violations(solution, cache)
            penalty = PrecedenceConstraint._penalty * number_of_violations

            # It's a soft constraint, so it always return feasible
            return self.feasible_evaluation(penalty)
        else:
            raise NotImplementedError()

    @classmethod
    def multiply_penalty(cls, multiplier: float) -> None:
        """
        Adjust the penalty multiplier for the constraint violations.
        :param multiplier: Multiplier for the penalty value.
        """
        if multiplier < 1 and cls._penalty < 1:
            return

        cls._penalty *= multiplier

    @classmethod
    def set_penalty(cls, value: float) -> None:
        """
        Set the penalty value for the constraint violations.
        :param value: Penalty value.
        """
        cls._penalty = value

    def count_precedence_violations(self, solution: AlwabpSolution, cache: bool) -> int:
        """
        Counts the number of precedence violations in the current solution.

        A precedence violation occurs when:
        - A task `B` is executed before another task `A` that it depends on.
        - Task `A` has been allocated but appears in a later station than task `B`.

        :param solution: A Solution object (AlwabpSolution).

        Returns:
            int: The total number of precedence violations.
        """
        sol_hash = solution.solution_hash
        memo = PrecedenceConstraint._precedence_violations_memo
        if cache and (cached := memo.get(sol_hash)) is not None:
            return cached

        # Flatten edges once
        graph = solution.immediate_task_precedences[solution.default_graph_orientation]
        edges = [(u, v) for v, pres in graph.items() for u in pres]

        assign = solution.task_station_assignment.get
        count = 0
        for u, v in edges:
            station_u = assign(u)
            station_v = assign(v)
            # Case 1: Both Allocated: If station_u > station_v, infeasible
            # Case 2: Only task_u allocated: always feasible
            # Case 3: Only task_v allocated: always infeasible
            if (station_u and station_v and station_u > station_v) or (not station_u and station_v):
                count += 1

        memo[sol_hash] = count
        return count

    def infeasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, True, PrecedenceConstraint._penalty, penalty)

    def feasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, False, PrecedenceConstraint._penalty, penalty)
