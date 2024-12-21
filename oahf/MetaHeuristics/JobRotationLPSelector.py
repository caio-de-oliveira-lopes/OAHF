import sys
from pathlib import Path
from typing import Optional

import gurobipy as gp
from gurobipy import GRB

from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.LpExecutionData import LpExecutionData
from oahf.Logger.LogManager import LogManager


class JobRotationLPSelector(MetaHeuristic):

    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        acceptance_criteria: AcceptanceCriteria,
        number_of_periods: int,
        gurobi_path: Path,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            acceptance_criteria,
            origin_pool=origin_pool,
            destination_pool=destination_pool,
        )
        self.number_of_periods = number_of_periods
        self.gurobi_path = gurobi_path

    def copy(self, thread: int) -> "JobRotationLPSelector":
        """Creates a copy of the current BestImprovement instance."""
        return JobRotationLPSelector(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.acceptance_criteria.copy(),
            self.number_of_periods,
            self.gurobi_path,  # type: ignore
            origin_pool=self.origin_pool.copy() if self.origin_pool else None,
            destination_pool=(
                self.destination_pool.copy() if self.destination_pool else None
            ),
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
            result = destination_pool or ListPool()
            alwabp_solutions = []

            # Filter only AlwabpSolutions from the origin pool
            for solution in origin_pool.get_list():
                if isinstance(solution, AlwabpSolution):
                    alwabp_solutions.append(solution)
                    solution.default_graph_orientation = GraphOrientation.FORWARD

            if alwabp_solutions:
                number_of_solutions = len(alwabp_solutions)
                workers = alwabp_solutions[0].workers
                tasks = alwabp_solutions[0].tasks

                # Initialize the Gurobi model directly
                grb_model = gp.Model("JobRotationLPSelector")
                grb_model.setParam(
                    "MIPGap", 1e-6
                )  # Set a very small MIP gap for high precision

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
                epsilon = 1e-6
                grb_model.setObjective(
                    gp.quicksum(z[w, t] for w in workers for t in tasks)
                    - epsilon * cycle_time_average,
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

                # Optimize the model
                grb_model.optimize()

                # Check if the solution is valid (could be OPTIMAL, SUBOPTIMAL)
                valid_status_codes = {GRB.OPTIMAL, GRB.SUBOPTIMAL}

                if grb_model.status in valid_status_codes:
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
                    raise Exception(
                        f"Gurobi failed to solve the problem. Status: {grb_model.status}"
                    )

                # Instantiate JobRotationAlwabpSolution
                job_rotation_solution = JobRotationAlwabpSolution(
                    self.number_of_periods, pulp_execution_data
                )
                for i in range(self.number_of_periods):
                    for j in range(number_of_solutions):
                        if solution[i, j].x > 0.5:  # type: ignore
                            job_rotation_solution.assign_solution_to_period(
                                i, alwabp_solutions[j]
                            )
                            break

                result.add_solution(job_rotation_solution)

            grb_model.dispose()  # Dispose the model when done
            return result
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            raise
