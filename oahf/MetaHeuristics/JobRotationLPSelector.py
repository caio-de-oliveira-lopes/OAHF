from pathlib import Path
from typing import Optional

import gurobipy as gp
from gurobipy import GRB

from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Commons.ProblemData import ProblemData
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import (
    AlwaysAcceptAcceptanceCriteria,
)
from oahf.ImplementedBase.JobRotationAlwabpEvaluator import JobRotationAlwabpEvaluator
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.LpExecutionData import LpExecutionData
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.Logger.LogManager import LogManager
from oahf.Utils.Util import Util


class JobRotationLPSelector(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        number_of_periods: int,
        gurobi_path: Path,
        problem_data: ProblemData,
        tolerance_percentage: Optional[float] = None,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
        super().__init__(
            thread_id,
            NoStopCriteria(),
            JobRotationAlwabpEvaluator(),
            AlwaysAcceptAcceptanceCriteria(),
            origin_pool=origin_pool,
            destination_pool=destination_pool,
        )
        self.number_of_periods = number_of_periods
        self.gurobi_path = gurobi_path
        self.problem_data = problem_data
        self.cycle_time_limit = Util.get_recommeded_maximum_mean_cycle_time(
            self.problem_data.cycle_time_path, self.problem_data.file_name
        )
        self.tolerance_percentage = tolerance_percentage

    def copy(self, thread: int) -> "JobRotationLPSelector":
        """Creates a copy of the current BestImprovement instance."""
        return JobRotationLPSelector(
            thread,
            self.number_of_periods,
            self.gurobi_path,
            self.problem_data,
            self.tolerance_percentage,
            origin_pool=self.origin_pool.copy() if self.origin_pool else None,
            destination_pool=(
                self.destination_pool.copy() if self.destination_pool else None
            ),
        )

    def run(self, sol: Solution) -> Solution:
        raise NotImplementedError("Use run_operation() method for this class.")

    def run_operation(
        self,
        origin_pool: Pool,
        destination_pool: Optional[Pool],
        parent: Optional["MetaHeuristic"] = None,
    ) -> Pool:
        try:
            self.parent_metaheuristic = parent
            result = destination_pool or ListPool()
            alwabp_solutions = []
            best_alwabp_sol = self.origin_pool.get_best()

            # Filter only AlwabpSolutions from the origin pool
            for solution in origin_pool:
                if isinstance(solution, AlwabpSolution):
                    alwabp_solutions.append(solution)
                    solution.default_graph_orientation = GraphOrientation.FORWARD

            if alwabp_solutions:
                number_of_solutions = len(alwabp_solutions)
                workers = alwabp_solutions[0].workers
                tasks = alwabp_solutions[0].tasks

                # Initialize the Gurobi model directly
                grb_model = gp.Model("JobRotationLPSelector")

                # SECTION TO AVOID MULTIPLE OUTPUTS REGARDING PRECISION
                import sys, os

                # Mute stdout
                old_stdout = sys.stdout
                sys.stdout = open(os.devnull, "w")

                grb_model.setParam("MIPGap", Util.eps())

                # Restore
                sys.stdout.close()
                sys.stdout = old_stdout
                grb_model.setParam("OutputFlag", 0)
                # ENDING SPECIAL SPECTION

                # adding timeout to respect StopTimeIterationCriteria
                timeout = self.get_min_timeout_milliseconds() / 1000.0
                if timeout:
                    grb_model.setParam("TimeLimit", timeout)

                # Decision variables
                solution = {}
                for i in range(self.number_of_periods):
                    for j in range(number_of_solutions):
                        solution[i, j] = grb_model.addVar(
                            vtype=GRB.BINARY, name=f"solution_{i}_{j}"
                        )

                z = {}
                for w in workers:
                    for t in tasks:
                        z[w, t] = grb_model.addVar(vtype=GRB.BINARY, name=f"z_{w}_{t}")

                cycle_time_average = grb_model.addVar(
                    vtype=GRB.CONTINUOUS, name="cycle_time_average"
                )

                # Set the objective function
                grb_model.setObjective(
                    gp.quicksum(z[w, t] for w in workers for t in tasks),
                    GRB.MAXIMIZE,
                )

                # Constraints
                for i in range(self.number_of_periods):
                    grb_model.addConstr(
                        gp.quicksum(solution[i, j] for j in range(number_of_solutions))
                        == 1
                    )

                for w in workers:
                    for t in tasks:
                        grb_model.addConstr(
                            z[w, t]
                            <= gp.quicksum(
                                solution[i, j]
                                * int(
                                    t
                                    in alwabp_solutions[j].station_tasks_assignment[
                                        alwabp_solutions[j].find_station_for_worker(w)
                                    ]
                                )
                                for i in range(self.number_of_periods)
                                for j in range(number_of_solutions)
                            )
                        )

                grb_model.addConstr(
                    cycle_time_average
                    == gp.quicksum(
                        solution[i, j]
                        * (
                            alwabp_solutions[j].get_max_cycle_time()
                            / self.number_of_periods
                        )
                        for i in range(self.number_of_periods)
                        for j in range(number_of_solutions)
                    )
                )

                if best_alwabp_sol is not None and isinstance(best_alwabp_sol, AlwabpSolution):
                    self.cycle_time_limit = best_alwabp_sol.get_max_cycle_time()

                # Updating max tolerance allowed for average cycle time
                JobRotationAlwabpSolution._max_tolerance = self.cycle_time_limit * (1 + self.tolerance_percentage)

                if self.tolerance_percentage is not None:
                    grb_model.addConstr(
                        cycle_time_average
                        <= JobRotationAlwabpSolution._max_tolerance,
                        name="cycle_time_tolerance_constraint",
                    )

                # Reset StopCriteria in case of using StopTimeIterationCriteria
                self.stop_criteria.reset()

                # Optimize the model
                grb_model.optimize()

                # Check if the solution is valid (could be OPTIMAL, SUBOPTIMAL or TIME_LIMIT)
                valid_status_codes = {GRB.OPTIMAL, GRB.SUBOPTIMAL, GRB.TIME_LIMIT}

                if grb_model.status in valid_status_codes and grb_model.SolCount > 0:
                    solve_seconds = grb_model.Runtime
                    optimality_gap = grb_model.MIPGap
                    simplex_iterations = grb_model.IterCount
                    nodes_explored = grb_model.NodeCount

                    pulp_execution_data = LpExecutionData(
                        simplex_iterations,
                        nodes_explored,
                        optimality_gap,
                        solve_seconds,
                    )
                else:
                    LogManager.something_went_wrong(
                        self.name,
                        f"Gurobi failed to solve the problem. Status: {grb_model.status}",
                    )
                    grb_model.dispose()  # Dispose the model when done
                    return ListPool()

                # Instantiate JobRotationAlwabpSolution
                job_rotation_solution = JobRotationAlwabpSolution(
                    self.number_of_periods, pulp_execution_data
                )
                for i in range(self.number_of_periods):
                    for j in range(number_of_solutions):
                        if solution[i, j].x > Util.eps():  # type: ignore
                            job_rotation_solution.assign_solution_to_period(
                                i, alwabp_solutions[j]
                            )
                            break

                result.add_solution(job_rotation_solution, self)

            grb_model.dispose()  # Dispose the model when done
            return result
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            return result
