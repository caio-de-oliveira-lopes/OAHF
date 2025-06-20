from typing import List, Optional

import gurobipy as gp
from gurobipy import GRB

from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Commons.ProblemData import ProblemData
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import (
    AlwaysAcceptAcceptanceCriteria,
)
from oahf.ImplementedBase.JobRotationAlwabpEvaluator import JobRotationAlwabpEvaluator
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.ImplementedBase.LpExecutionData import LpExecutionData
from oahf.Logger.LogManager import LogManager
from oahf.Utils.Util import Util


class JobRotationLPSelector(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        number_of_periods: int,
        tasks_executed_factor: float,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
        super().__init__(
            thread_id,
            stop_criteria,
            JobRotationAlwabpEvaluator(),
            AlwaysAcceptAcceptanceCriteria(),
            origin_pool=origin_pool,
            destination_pool=destination_pool,
        )
        self.number_of_periods = number_of_periods
        self.tasks_executed_factor = tasks_executed_factor
        self.cycle_time_factor = 1.0 - self.tasks_executed_factor

        JobRotationAlwabpSolution.add_to_alwabp_pools(origin_pool)
        JobRotationAlwabpSolution.add_to_job_rotation_pools(destination_pool)
        JobRotationAlwabpSolution._tasks_executed_factor = self.tasks_executed_factor
        JobRotationAlwabpSolution._cycle_time_factor = self.cycle_time_factor

    def copy(self, thread: int) -> "JobRotationLPSelector":
        """Creates a copy of the current BestImprovement instance."""
        return JobRotationLPSelector(
            thread,
            self.stop_criteria.copy(),
            self.number_of_periods,
            self.tasks_executed_factor,
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
            from oahf.ImplementedBase.ListPool import ListPool

            self.parent_metaheuristic = parent
            result = destination_pool or ListPool()
            alwabp_solutions: List[AlwabpSolution] = []
            JobRotationAlwabpSolution.update_current_alwabp_upper_bound()

            # Filter only AlwabpSolutions from the origin pool
            for solution in origin_pool:
                if isinstance(solution, AlwabpSolution):
                    alwabp_solutions.append(solution)
                    solution.default_graph_orientation = GraphOrientation.FORWARD

            if alwabp_solutions:
                number_of_solutions = len(alwabp_solutions)
                workers = alwabp_solutions[0].workers
                tasks = alwabp_solutions[0].tasks
                upper_bound = JobRotationAlwabpSolution._current_alwabp_upper_bound

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
                # select the first solution from the pool
                sol = alwabp_solutions[0]

                # 1) positive component: normalized sum of task assignments
                sum_z = gp.quicksum(z[w, i] for w in workers for i in tasks)
                total_executed = sum([len(sol.tasks_executed_by_worker[w]) for w in workers])
                part1 = (self.tasks_executed_factor / float(total_executed)) * sum_z

                # 2) negative component: normalized sum of cycle times
                part2 = (self.cycle_time_factor / upper_bound) * cycle_time_average
                # set and maximize the composite objective: part1 minus part2
                grb_model.setObjective(
                    part1 - part2,
                    GRB.MAXIMIZE
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
                    cycle_time_average * self.number_of_periods
                    == gp.quicksum(
                        solution[i, j] * alwabp_solutions[j].get_max_cycle_time()
                        for i in range(self.number_of_periods)
                        for j in range(number_of_solutions)
                    )
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
