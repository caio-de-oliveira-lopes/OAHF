from typing import List, Optional
import gurobipy as gp
from abc import ABC, abstractmethod
from gurobipy import GRB
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Commons.ProblemData import AlwabpSolution
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import AlwaysAcceptAcceptanceCriteria
from oahf.ImplementedBase.JobRotationAlwabpSolution import JobRotationAlwabpSolution
from oahf.Base.Pool import Pool
from oahf.ImplementedBase.ListPool import ListPool
from oahf.Logger.LogManager import LogManager

class JobRotationLPLocalSearch(MetaHeuristic, ABC):
    """
    Abstract class to be used in MIP Local Searches considering Job Rotation Solutions.
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
            AlwaysAcceptAcceptanceCriteria(),
            None,
            [],
            origin_pool,
            destination_pool
        )
        self.alwabp_solution_pool = alwabp_solution_pool
        

    def copy(self, thread_id: int) -> "JobRotationLPLocalSearch":
        return JobRotationLPLocalSearch(
            thread_id,
            self.stop_criteria.copy(),
            self.evaluator,
            self.alwabp_solution_pool.copy() if self.alwabp_solution_pool is not None else None,
            self.origin_pool.copy() if self.origin_pool is not None else None,
            self.destination_pool.copy() if self.destination_pool is not None else None,
        )

    def run_operation(
        self,
        origin_pool: Pool,
        destination_pool: Optional[Pool],
        parent: Optional["MetaHeuristic"] = None,
    ) -> Pool:
        """Run the heuristic on a given pool of solutions."""
        try:
            JobRotationAlwabpSolution.update_max_tolerance()

            self.parent_metaheuristic = parent
            self.stop_criteria.reset()
            if self.neighborhood_selection:
                self.neighborhood_selection.reset(self.thread_id)

            result = destination_pool if destination_pool else ListPool()
            self.start_time = self._current_milliseconds()

            sol = origin_pool.get_best()

            if sol:
                result.add_solution(self.run(sol), self)

            self.end_time = self._current_milliseconds()
            return result
        except Exception as ex:
            LogManager.something_went_wrong(self.__class__.__name__, ex)
            raise

    @abstractmethod
    def run(self, sol: Solution) -> Solution:
        """Runs the meta-heuristic on a single solution. Not implemented in this class."""
        raise NotImplementedError(
            "Abstract Method: must be implemented by child classes."
        )

    def build_model(self, solution: JobRotationAlwabpSolution) -> gp.Model:
        """
        Build the MIP model for the job rotation planning problem as described
        in Moreira and Costa (2013), initializing variables based on the provided solution.

        Args:
            solution: an instance of JobRotationAlwabpSolution containing period-specific solutions.
        Returns:
            A gp.Model object configured with variables, constraints, and initial values,
            ready for optimization.
        """

        from oahf.Utils.Util import Util

        # Create a new Gurobi model
        grb_model = gp.Model('JobRotationAlwabpSolution')

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
        timeout = self.get_min_timeout_milliseconds()
        if timeout:
            grb_model.setParam("TimeLimit", timeout)

        T = solution.number_of_periods
        periods = range(T)

        # Use the first period solution to extract reference sets
        base = solution.period_solutions[0]
        stations = base.stations
        workers  = base.workers
        tasks    = base.tasks
        N        = base._number_of_tasks
        cycle_time_limit = JobRotationAlwabpSolution._max_tolerance

        # Decision variables
        # x[s, w, i, t] = 1 if task i is assigned to worker w at station s during period t
        x = {}
        for t in periods:
            sol_t = solution.period_solutions[t]
            for s in stations:
                for w in workers:
                    for i in sol_t.tasks_executed_by_worker[w]:
                        x[s, w, i, t] = grb_model.addVar(
                            vtype=GRB.BINARY,
                            name=f"x_{s}_{w}_{i}_{t}"
                        )
                        x[s, w, i, t].Start = 0

        # y[s, w, t] = 1 if worker w is assigned to station s during period t
        y = {}
        for t in periods:
            for s in stations:
                for w in workers:
                    y[s, w, t] = grb_model.addVar(
                        vtype=GRB.BINARY,
                        name=f"y_{s}_{w}_{t}"
                    )
                    y[s, w, t].Start = 0

        # z[w, i] = 1 if worker w performs task i in at least one period
        z = {}
        for w in workers:
            for i in solution.period_solutions[0].tasks_executed_by_worker[w]:
                z[w, i] = grb_model.addVar(
                    vtype=GRB.BINARY,
                    name=f"z_{w}_{i}"
                )

        # Continuous variables for cycle times
        # Ct[t] = cycle time for period t
        Ct = {}
        for t in periods:
            sol_t = solution.period_solutions[t]
            Ct[t] = grb_model.addVar(
                vtype=GRB.CONTINUOUS,
                name=f"C_{t}"
            )
            Ct[t].Start = sol_t.get_max_cycle_time()

        # C = maximum allowed average cycle time across all periods
        C = grb_model.addVar(
            ub=cycle_time_limit,
            vtype=GRB.CONTINUOUS,
            name="C"
        )

        # Objective: maximize the total number of distinct tasks performed by all workers
        grb_model.setObjective(
            gp.quicksum(z[w, i] for w in workers for i in tasks if (w, i) in z),
            GRB.MAXIMIZE
        )

        # Constraints

        # (12) Each task i must be assigned exactly once in each period t
        for t in periods:
            sol_t = solution.period_solutions[t]
            for i in tasks:
                expr = gp.quicksum(
                    x[s, w, i, t]
                    for s in stations
                    for w in workers
                    if (s, w, i, t) in x
                )
                grb_model.addConstr(
                    expr == 1,
                    name=f"assign_task_{i}_{t}"
                )

        # (13) Each station s must handle at least one task in each period t
        for t in periods:
            sol_t = solution.period_solutions[t]
            for s in stations:
                expr = gp.quicksum(
                    x[s, w, i, t]
                    for w in workers
                    for i in sol_t.tasks_executed_by_worker[w]
                    if (s, w, i, t) in x
                )
                grb_model.addConstr(expr >= 1, name=f"station_load_{s}_{t}")

        # (14) Each worker w is assigned to exactly one station per period
        for t in periods:
            for w in workers:
                grb_model.addConstr(
                    gp.quicksum(y[s, w, t] for s in stations) == 1,
                    name=f"one_station_{w}_{t}"
                )

        # (15) Each station s has exactly one worker per period
        for t in periods:
            for s in stations:
                grb_model.addConstr(
                    gp.quicksum(y[s, w, t] for w in workers) == 1,
                    name=f"one_worker_{s}_{t}"
                )

        # (16) Precedence constraints: if i immediately precedes j, station(i) <= station(j) each period
        for t in periods:
            sol_t = solution.period_solutions[t]
            for j, pre_list in sol_t.immediate_task_precedences[sol_t.default_graph_orientation].items():
                for i in pre_list:
                    lhs = gp.quicksum(
                        s * x[s, w, i, t]
                        for s in stations
                        for w in workers
                        if (s, w, i, t) in x
                    )
                    rhs = gp.quicksum(
                        s * x[s, w, j, t]
                        for s in stations
                        for w in workers
                        if (s, w, j, t) in x
                    )
                    grb_model.addConstr(lhs <= rhs, name=f"precedence_{i}_{j}_{t}")

        # (17) Cycle time constraint per station and period
        for t in periods:
            sol_t = solution.period_solutions[t]
            for s in stations:
                expr = gp.quicksum(
                    sol_t.get_task_execution_time(i, w) * x[s, w, i, t]
                    for i in tasks
                    for w in workers
                    if (s, w, i, t) in x
                )
                grb_model.addConstr(expr <= Ct[t], name=f"cycle_time_{s}_{t}")

        # (18) Link x and y: tasks only if the worker is assigned to the station
        for t in periods:
            for s in stations:
                for w in workers:
                    expr = gp.quicksum(
                        x[s, w, i, t]
                        for i in tasks
                        if (s, w, i, t) in x
                    )
                    grb_model.addConstr(expr <= N * y[s, w, t], name=f"link_x_y_{s}_{w}_{t}")

        # (19) Average cycle time across periods must not exceed C
        grb_model.addConstr(
            gp.quicksum(Ct[t] for t in periods) <= T * C,
            name="avg_cycle_time"
        )

        # (20) Activation of z: z[w,i] <= sum of x over all periods and stations
        for w in workers:
            for i in tasks:
                if (w, i) in z:
                    expr = gp.quicksum(
                        x[s, w, i, t]
                        for s in stations
                        for t in periods
                        if (s, w, i, t) in x
                    )
                    grb_model.addConstr(expr >= z[w, i], name=f"activate_z_{w}_{i}")

        # Warm start: set initial values for x and y based on the provided solution
        for t, sol_t in enumerate(solution.period_solutions):
            for s in stations:
                w_assigned = sol_t.station_worker_assignment[s]
                y[s, w_assigned, t].Start = 1
                for i in sol_t.station_tasks_assignment[s]:
                    if (s, w_assigned, i, t) in x:
                        x[s, w_assigned, i, t].Start = 1

        # ONLY A FEW ACTIONS AUTO-UPDATE THE MODEL (like optimizing), since we are not running it immediatelly, we must update!
        grb_model.update()
        return grb_model

    def gather_alwabp_model_data(self, grb_model: gp.Model, period: int, output_sol: AlwabpSolution) -> AlwabpSolution:
        from oahf.ImplementedBase.AlwabpInsertionMovement import AlwabpInsertionMovement
        from oahf.Base.MultipleMovement import MultipleMovement
        from oahf.Utils.Util import Util

        # Reset solution to receive new assignments
        output_sol.reset()

        movements = []
        workers_added = set()

        # Iterate over all variables in the Gurobi model
        for var in grb_model.getVars():
            name = var.VarName
            # Select only x_ variables and those matching this period
            if not name.startswith("x_"):
                continue
            parts = name.split("_")  # expected format: x_{station}_{worker}_{task}_{period}
            if len(parts) != 5:
                continue
            _, s_str, w_str, i_str, t_str = parts
            try:
                t_idx = int(t_str)
            except ValueError:
                continue
            if t_idx != period:
                continue
            # Only consider selected variables
            if var.X <= Util.eps():
                continue

            # Parse identifiers (will match types used in solution)
            station = int(s_str)  # cast to station type
            worker = int(w_str)
            task = int(i_str)

            # Insert worker assignment movement once per worker
            if worker not in workers_added:
                movements.append(AlwabpInsertionMovement(None, worker, station, output_sol))
                workers_added.add(worker)
            # Insert task assignment movement
            movements.append(AlwabpInsertionMovement(task, None, station, output_sol))

        # Group all movements into a single multiple movement
        multiple_move = MultipleMovement(output_sol, movements)
        if not multiple_move.apply():
            raise Exception("Error applying movements generated through the result of the mathematical model.")

        # Adjust solution bounds after construction
        output_sol.narrow_bounds()
        return output_sol


    def evaluate_and_add_to_alwabp_pool(self, solutions: List[AlwabpSolution]) -> None:
        if self.alwabp_solution_pool:
            evaluator = self.alwabp_solution_pool.evaluator
            for solution in solutions:
                curr_eval = evaluator.evaluate(solution)
                if not (curr_eval.infeasible() or curr_eval.has_penalty()):
                    self.alwabp_solution_pool.add_solution(solution, self)
                else:
                    raise Exception("Local Search Generated Infeasible Alwabp Solution, please check!")
                    