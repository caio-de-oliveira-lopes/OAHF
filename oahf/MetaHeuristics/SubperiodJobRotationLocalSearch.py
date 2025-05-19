from typing import List, Optional
import gurobipy as gp
from gurobipy import GRB
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import ListPool
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.LpExecutionData import LpExecutionData
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.JobRotationLPLocalSearch import JobRotationLPLocalSearch

class SubperiodJobRotationLocalSearch(JobRotationLPLocalSearch):
    """
    LSJR2: Subperiod-Based Job Rotation Local Search
    - For each subperiod b, rebuilds the MIP fixing:
        (36) x_s_w_i_t == original value for all t != b
        (37) y_s_w_t == original value for all t
    - Solves and updates only the variables of period b.
    """
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        alwabp_solution_pool: Optional[Pool] = None,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None
    ):
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            alwabp_solution_pool,
            origin_pool,
            destination_pool
        )

    def copy(self, thread_id: int) -> "SubperiodJobRotationLocalSearch":
        return SubperiodJobRotationLocalSearch(
            thread_id,
            self.stop_criteria.copy(),
            self.evaluator,
            self.alwabp_solution_pool.copy() if self.alwabp_solution_pool is not None else None,
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run(self, solution: Solution) -> Solution:
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
        from oahf.Utils.Util import Util

        if not isinstance(solution, JobRotationAlwabpSolution):
            raise Exception("Solution must be a JobRotationAlwabpSolution.")

        total_periods = solution.number_of_periods
        output_pool = ListPool()
        current_solution = solution

        # Iterate over each subperiod to apply LSJR2
        for b in range(total_periods):
            # Build the base model for the current solution
            grb_model: gp.Model = self.build_model(current_solution)

            # Apply constraints (36) and (37):
            #    Fix x variables for all periods except b, and fix all y variables
            for var in grb_model.getVars():
                name = var.VarName

                if name.startswith("x_"):
                    # Format: x_s_w_i_t
                    _, s, w, i, t = name.split("_")
                    s, w, i, t = map(int, (s, w, i, t))
                    original_x = int(var.Start > Util.eps())
                    if t != b:
                        # (36) Fix x_s_w_i_t to its original value for t != b
                        grb_model.addConstr(var == original_x, name=f"lsjr2_fix_x_{name}")

                elif name.startswith("y_"):
                    # Format: y_s_w_t
                    _, s, w, t = name.split("_")
                    s, w, t = map(int, (s, w, t))
                    original_y = int(var.Start > Util.eps())
                    # (37) Fix y_s_w_t to its original value for all t
                    grb_model.addConstr(var == original_y, name=f"lsjr2_fix_y_{name}")

            # Reset StopCriteria in case of using StopTimeIterationCriteria
            self.stop_criteria.reset()

            # Adding the timeout
            timeout = self.get_min_timeout_milliseconds() / 1000.0
            if timeout:
                grb_model.setParam("TimeLimit", timeout)

            # Optimize
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
                    solve_seconds
                )
            else:
                LogManager.something_went_wrong(
                    self.name,
                    f"Gurobi failed to solve the problem. Status: {grb_model.status}",
                )
                grb_model.dispose()  # Dispose the model when done
                continue

            try:
                # Extract Alwabp data and build new solutions
                period_solutions: List[AlwabpSolution] = [self.gather_alwabp_model_data(grb_model, period, solution.period_solutions[0].copy()) for period in range(solution.number_of_periods)]
                self.evaluate_and_add_to_alwabp_pool(period_solutions)
            except Exception as ex:
                LogManager.something_went_wrong(self.__class__.__name__, ex)
                continue

            # Instantiate JobRotationAlwabpSolution
            job_rotation_solution = JobRotationAlwabpSolution(
                solution.number_of_periods, pulp_execution_data
            )
            for i in range(solution.number_of_periods):
                job_rotation_solution.assign_solution_to_period(
                    i, period_solutions[i]
                )

            output_pool.add_solution(job_rotation_solution, self)
            if self.destination_pool:
                self.destination_pool.add_solution(job_rotation_solution, self)

            current_solution = job_rotation_solution
        
        best_job_rotation_solution_found = output_pool.get_best()
        return best_job_rotation_solution_found
