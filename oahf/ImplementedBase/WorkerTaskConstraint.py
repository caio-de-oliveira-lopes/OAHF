from typing import Dict

from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class WorkerTaskConstraint(Constraint):
    _penalty = 60.0  # Default penalty value; can be adjusted.
    _worker_task_violations_memo: Dict[int, int] = {}

    def evaluate(self, solution: "Solution") -> "ConstraintEvaluation":
        """
        Method to evaluate the worker-task constraint based on a solution.
        :param solution: A Solution object (AlwabpSolution).
        :return: A ConstraintEvaluation object.
        """
        if isinstance(solution, AlwabpSolution):
            number_of_violations = self.count_worker_task_violations(solution)
            penalty = WorkerTaskConstraint._penalty * number_of_violations

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

    def count_worker_task_violations(self, solution: "AlwabpSolution") -> int:
        """
        Counts the number of worker-task violations in the current solution.

        Worker-task violations occur when a task is assigned to a worker who cannot execute it.

        :param solution: A Solution object (AlwabpSolution).

        Returns:
            int: The total number of worker-task violations.
        """
        sol_hash = solution.solution_hash
        memo = WorkerTaskConstraint._worker_task_violations_memo

        # Return cached result if already computed
        if (cached_result := memo.get(sol_hash)) is not None:
            return cached_result

        violation_count = 0
        station_worker_assignment = solution.station_worker_assignment
        task_executable_by_worker = solution.tasks_executed_by_worker
        station_tasks_assignment = solution.station_tasks_assignment

        # Iterate through all stations
        for station, tasks in station_tasks_assignment.items():
            worker = station_worker_assignment.get(station)

            if worker is not None:
                executable_tasks = task_executable_by_worker[worker]

                # Use set difference for faster violation counting
                violation_count += sum(
                    1 for task in tasks if task not in executable_tasks
                )

        # Store result in memoization dictionary
        memo[sol_hash] = violation_count
        return violation_count

    def infeasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        """
        Creates an infeasible evaluation object with a penalty.
        :param penalty: The penalty for the constraint violation.
        :return: A ConstraintEvaluation object.
        """
        return ConstraintEvaluation(self, True, WorkerTaskConstraint._penalty, penalty)

    def feasible_evaluation(self, penalty: float = 0) -> "ConstraintEvaluation":
        """
        Creates a feasible evaluation object with a penalty.
        :param penalty: The penalty for the constraint violation.
        :return: A ConstraintEvaluation object.
        """
        return ConstraintEvaluation(self, False, WorkerTaskConstraint._penalty, penalty)
