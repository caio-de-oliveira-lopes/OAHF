from pathlib import Path
from typing import Optional

from pulp import COIN_CMD, LpMaximize, LpProblem, LpVariable, lpSum

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.ImplementedBase.ListPool import ListPool
from oahf.Logger.LogManager import LogManager


class JobRotationLPSelector(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        number_of_periods: int,
        solver_path: Path,
    ):
        super().__init__(thread_id, stop_criteria, evaluator, acceptance_criteria)
        self.number_of_periods = number_of_periods
        self.solver_path = solver_path

    def copy(self, thread: int) -> "JobRotationLPSelector":
        """Creates a copy of the current BestImprovement instance."""
        return JobRotationLPSelector(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.number_of_periods,
            self.solver_path,  # type: ignore
        )

    def run(self, sol: Solution) -> Solution:
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    def run_operation(
        self,
        origin_pool: Pool,
        destination_pool: Optional[Pool],
        parent: Optional["MetaHeuristic"] = None,
    ) -> Pool:
        try:
            # Filter only AlwabpSolutions from the origin pool
            alwabp_solutions = [
                solution
                for solution in origin_pool.get_list()
                if isinstance(solution, AlwabpSolution)
            ]
            result = destination_pool or ListPool()

            if alwabp_solutions:
                # Extract problem dimensions
                number_of_solutions = len(alwabp_solutions)
                workers = alwabp_solutions[0].workers
                tasks = alwabp_solutions[0].tasks

                # Initialize the model
                model = LpProblem("JobRotationLPSelector", LpMaximize)

                # Decision variables
                solution = LpVariable.dicts(
                    "solution",
                    (
                        (i, j)
                        for i in range(self.number_of_periods)
                        for j in range(number_of_solutions)
                    ),
                    cat="Binary",
                )
                z = LpVariable.dicts(
                    "z", ((w, t) for w in workers for t in tasks), cat="Binary"
                )

                # Objective function: Maximize unique tasks performed by workers across periods
                model += lpSum(z[w, t] for w in workers for t in tasks)

                # Constraints

                # Each period is assigned exactly one solution
                for i in range(self.number_of_periods):
                    model += (
                        lpSum(solution[i, j] for j in range(number_of_solutions)) == 1,
                        f"PeriodAssignment_{i}",
                    )

                # Linking constraints for tasks executed by workers
                for w in workers:
                    for t in tasks:
                        model += (
                            z[w, t]
                            <= lpSum(
                                solution[i, j]
                                * int(
                                    t in alwabp_solutions[j].tasks_executed_by_worker[w]
                                )
                                for i in range(self.number_of_periods)
                                for j in range(number_of_solutions)
                            ),
                            f"TaskExecution_{w}_{t}",
                        )

                # Build solver
                solver = COIN_CMD(
                    mip=False, msg=True, path=self.solver_path
                )  # Can also set "threads" and "gapRel"

                # Solve the problem
                model.solve(solver)

                # Check Infeasibility
                if model.status == -1:
                    raise Exception("Job rotation solution is infeasible")

                # Instantiate JobRotationAlwabpSolution
                job_rotation_solution = JobRotationAlwabpSolution(
                    self.number_of_periods
                )

                for i in range(self.number_of_periods):
                    # Find the selected solution for each period
                    for j in range(number_of_solutions):
                        if solution[i, j].value() == 1:
                            job_rotation_solution.assign_solution_to_period(
                                i, alwabp_solutions[j]
                            )
                            break

                # Add the resulting solution to the result pool
                result.add_solution(job_rotation_solution)

            return result
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            raise
