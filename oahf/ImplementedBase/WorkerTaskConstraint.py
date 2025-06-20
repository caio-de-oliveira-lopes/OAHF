from typing import Dict

from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class WorkerTaskConstraint(Constraint):
    _original_penalty = 60.0
    _penalty = 60.0  # Default penalty value; can be adjusted.
    _worker_task_violations_memo: Dict[int, int] = {}

    def evaluate(self, solution: "Solution", cache: bool) -> "ConstraintEvaluation":
        """
        Method to evaluate the worker-task constraint based on a solution.
        :param solution: A Solution object (AlwabpSolution).
        :return: A ConstraintEvaluation object.
        """
        if isinstance(solution, AlwabpSolution):
            number_of_violations = self.count_worker_task_violations(solution, cache)
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
        if multiplier < 1 and cls._penalty < 1:
            return

        cls._penalty *= multiplier

    @classmethod
    def reset_penalty(cls) -> None:
        cls._penalty = cls._original_penalty

    @classmethod
    def set_penalty(cls, value: float) -> None:
        """
        Set the penalty value for the constraint violations.
        :param value: Penalty value.
        """
        cls._penalty = value

    def count_worker_task_violations(self, solution: "AlwabpSolution", cache: bool) -> int:
        """
        Counts the number of worker-task violations in the current solution.

        Worker-task violations occur when a task is assigned to a worker who cannot execute it.

        :param solution: A Solution object (AlwabpSolution).

        Returns:
            int: The total number of worker-task violations.
        """
        sol_hash = solution.solution_hash
        memo = WorkerTaskConstraint._worker_task_violations_memo

        # Return cached result if available
        if cache and (cached := memo.get(sol_hash)) is not None:
            return cached

        # Local bindings for speed
        sta_to_worker = solution.station_worker_assignment
        station_tasks = solution.station_tasks_assignment
        tasks_by_worker = solution.tasks_executed_by_worker
        _get_worker = sta_to_worker.get

        # Batch all assigned tasks by worker
        worker_to_tasks: dict = {}
        for station, tasks in station_tasks.items():
            worker = _get_worker(station)
            if worker is not None:
                worker_to_tasks.setdefault(worker, []).extend(tasks)

        # Count violations using set-difference per worker
        violations = 0
        for worker, assigned_tasks in worker_to_tasks.items():
            executable = tasks_by_worker[worker]
            # Convert to set once
            assigned_set = set(assigned_tasks)
            # All non-executable tasks
            violations += len(assigned_set - executable)

        # Memoize and return
        memo[sol_hash] = violations
        return violations

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
