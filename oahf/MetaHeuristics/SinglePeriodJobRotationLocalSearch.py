from typing import List, Optional
import gurobipy as gp
from gurobipy import GRB
from oahf.Base.Evaluator import Evaluator
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.LpExecutionData import LpExecutionData
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.JobRotationLPLocalSearch import JobRotationLPLocalSearch

class SinglePeriodJobRotationLocalSearch(JobRotationLPLocalSearch):
    """
    LSJR1: Single-Period Job Rotation Local Search
    - Rebuilds a restricted MIP for a given JobRotationAlwabpSolution.
    - Applies LSJR1 constraints directly in model construction.
    - Solves and updates solution based on y variables.
    """
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator: Evaluator,
        tasks_executed_factor: float,
        alwabp_solution_pool: Optional[Pool] = None,
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None
    ):
        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            tasks_executed_factor,
            alwabp_solution_pool,
            origin_pool,
            destination_pool
        )

    def copy(self, thread_id: int) -> "SinglePeriodJobRotationLocalSearch":
        return SinglePeriodJobRotationLocalSearch(
            thread_id,
            self.stop_criteria.copy(),
            self.evaluator,
            self.tasks_executed_factor,
            self.alwabp_solution_pool.copy() if self.alwabp_solution_pool is not None else None,
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run(self, solution: Solution) -> Solution:
        """
        1. Build base model for current JobRotationAlwabpSolution using build_model().
        2. Add LSJR1 neighborhood constraints:
           x_s_w_i_t <= xbar + neighbors;  y_s_w_t == ybar
        3. Optimize and extract new y allocations.
        """
        
        from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
        from oahf.Utils.Util import Util

        if not isinstance(solution, JobRotationAlwabpSolution):
            raise Exception("Solution must be a JobRotationAlwabpSolution.")

        # Build the base model
        grb_model: gp.Model = self.build_model(solution)
        last_station = solution.period_solutions[0]._number_of_stations

        # Add LSJR1 constraints using warm-start values in model
        for var in grb_model.getVars():
            name = var.VarName

            # (33) Neighborhood relaxation for x variables
            if name.startswith("x_"):
                # name format: x_s_w_i_t
                _, s, w, i, t = name.split("_")
                s, w, i, t = map(int, (s, w, i, t))
                # original value from warm start
                xbar = int(var.Start > Util.eps())
                # compute neighbor sum from start values of adjacent x-vars
                neighbor_sum = 0

                # predecessor station
                if s > 1:
                    # the worker assigned in station s-1 at period t
                    wp = solution.period_solutions[t].station_worker_assignment[s-1]
                    nb_var = grb_model.getVarByName(f"x_{s-1}_{wp}_{i}_{t}")
                    if nb_var is not None:
                        neighbor_sum += int(nb_var.Start > Util.eps())

                # successor station
                if s < last_station:
                    wp = solution.period_solutions[t].station_worker_assignment[s+1]
                    nb_var = grb_model.getVarByName(f"x_{s+1}_{wp}_{i}_{t}")
                    if nb_var is not None:
                        neighbor_sum += int(nb_var.Start > Util.eps())

                # limit new x by original plus neighbor copies
                grb_model.addConstr(var <= xbar + neighbor_sum, name=f"lsjr1_{name}")

            # (34) Fix all y variables
            elif name.startswith("y_"):
                # name format: y_s_w_t
                _, s, w, t = name.split("_")
                s, w, t = map(int, (s, w, t))

                # original y from warm start
                ybar = int(var.Start > Util.eps())
                grb_model.addConstr(var == ybar, name=f"fix_{name}")  
                
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
            #grb_model.computeIIS()
            #grb_model.write(fr"C:\Projetos\OAHF\Outputs\{grb_model.ModelName}_single_period_conflicts.ilp")
            #grb_model.dispose()  # Dispose the model when done
            return solution

        try:
            # Extract Alwabp data and build new solutions
            period_solutions: List[AlwabpSolution] = [self.gather_alwabp_model_data(grb_model, period, solution.period_solutions[0].copy()) for period in range(solution.number_of_periods)]
            self.evaluate_and_add_to_alwabp_pool(period_solutions)
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            return solution

        # Instantiate JobRotationAlwabpSolution
        job_rotation_solution = JobRotationAlwabpSolution(
            solution.number_of_periods, pulp_execution_data
        )
        for i in range(solution.number_of_periods):
            job_rotation_solution.assign_solution_to_period(
                i, period_solutions[i]
            )

        return job_rotation_solution
