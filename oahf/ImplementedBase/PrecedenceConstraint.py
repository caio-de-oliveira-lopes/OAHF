from typing import Dict

from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class PrecedenceConstraint(Constraint):
    _penalty = 60.0  # Default penalty value; can be adjusted.
    _precedence_violations_memo: Dict[int, int] = {}

    def evaluate(self, solution: "Solution") -> "ConstraintEvaluation":
        """
        Method to evaluate the precedence constraint based on a solution.
        :param solution: A Solution object (AlwabpSolution).
        :return: A ConstraintEvaluation object.
        """

        if isinstance(solution, AlwabpSolution):
            number_of_violations = self.count_precedence_violations(solution)
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
        cls._penalty *= multiplier

    @classmethod
    def set_penalty(cls, value: float) -> None:
        """
        Set the penalty value for the constraint violations.
        :param value: Penalty value.
        """
        cls._penalty = value

    def count_precedence_violations(self, solution: AlwabpSolution) -> int:
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

        # Return cached result if already computed
        if (cached_result := memo.get(sol_hash)) is not None:
            return cached_result

        # Cache frequently accessed attributes
        precedence_graph = solution.immediate_task_precedences[
            solution.default_graph_orientation
        ]
        task_station_assignment = solution.task_station_assignment

        violation_count = 0

        # Iterate through all stations
        for station, tasks in solution.station_tasks_assignment.items():
            for task in tasks:
                precedences = precedence_graph.get(task, [])

                # Check if any precedent task is in a later station
                for preceding_task in precedences:
                    preceding_task_station = task_station_assignment.get(preceding_task)

                    if preceding_task_station and preceding_task_station > station:
                        violation_count += 1

        # Store result in memoization dictionary
        memo[sol_hash] = violation_count
        return violation_count

    def infeasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, True, PrecedenceConstraint._penalty, penalty)

    def feasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        return ConstraintEvaluation(self, False, PrecedenceConstraint._penalty, penalty)
