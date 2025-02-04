from oahf.Base.Constraint import Constraint
from oahf.Base.ConstraintEvaluation import ConstraintEvaluation
from oahf.Base.Solution import Solution


class WorkerTaskConstraint(Constraint):
    _penalty = 60.0  # Default penalty value; can be adjusted.

    def evaluate(self, solution: "Solution") -> "ConstraintEvaluation":
        """
        Method to evaluate the worker-task constraint based on a solution.
        :param solution: A Solution object (AlwabpSolution).
        :return: A ConstraintEvaluation object.
        """
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

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
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution

        violation_count = 0

        if not isinstance(solution, AlwabpSolution):
            return violation_count

        # Iterate through all stations
        for station, tasks in solution.station_tasks_assignment.items():
            # Get the worker assigned to the current station
            worker = solution.station_worker_assignment.get(station)

            if worker is not None:
                # Retrieve tasks executable by the worker
                executable_tasks = solution.tasks_executed_by_worker[worker]

                # Check each task in the current station
                for task in tasks:
                    # Count as a violation if the worker cannot execute the task
                    if task not in executable_tasks:
                        violation_count += 1

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
