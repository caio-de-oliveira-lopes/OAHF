import gc
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from oahf.Base import AcceptanceCriteria, Evaluation
from oahf.Base.Constraint import Constraint
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.MultipleStopCriteria import MultipleStopCriteria
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.Commons.ProblemData import ProblemData
from oahf.ImplementedBase.AlwabpEvaluator import AlwabpEvaluator
from oahf.ImplementedBase.AlwabpSolution import GraphOrientation, TaskOrderingRule
from oahf.ImplementedBase.AlwabpTaskDiversificationNS import AlwabpTaskDiversificationNS
from oahf.ImplementedBase.AlwabpTaskIntensificationNS import AlwabpTaskIntensificationNS
from oahf.ImplementedBase.AlwabpWorkerDiversificationNS import (
    AlwabpWorkerDiversificationNS,
)
from oahf.ImplementedBase.AlwabpWorkerIntensificationNS import (
    AlwabpWorkerIntensificationNS,
)
from oahf.ImplementedBase.AlwabpWorkerOrientedInsertNS import (
    AlwabpWorkerOrientedInsertNS,
)
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import (
    AlwaysAcceptAcceptanceCriteria,
)
from oahf.ImplementedBase.BetterAcceptanceCriteria import BetterAcceptanceCriteria
from oahf.ImplementedBase.BetterOrSameAcceptanceCriteria import (
    BetterOrSameAcceptanceCriteria,
)
from oahf.ImplementedBase.ConsecutiveTaskSwapNS import ConsecutiveTaskSwapNS
from oahf.ImplementedBase.JobRotationAlwabpEvaluator import JobRotationAlwabpEvaluator
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.MaxCycleTimeConstraint import MaxCycleTimeConstraint
from oahf.ImplementedBase.MaxCycleTimeStopCriteria import MaxCycleTimeStopCriteria
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.ImplementedBase.PrecedenceConstraint import PrecedenceConstraint
from oahf.ImplementedBase.RearrangeCriticalTaskNS import RearrangeCriticalTaskNS
from oahf.ImplementedBase.StopNoImprovement import StopNoImprovement
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.ImplementedBase.TasksUnassignedStopCriteria import TasksUnassignedStopCriteria
from oahf.ImplementedBase.TaskSwapNS import TaskSwapNS
from oahf.ImplementedBase.WorkersUnassignedStopCriteria import (
    WorkersUnassignedStopCriteria,
)
from oahf.ImplementedBase.WorkerSwapNS import WorkerSwapNS
from oahf.ImplementedBase.WorkerSwapReconstructNS import WorkerSwapReconstructNS
from oahf.ImplementedBase.WorkerTaskConstraint import WorkerTaskConstraint
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.BestImprovement import BestImprovement
from oahf.MetaHeuristics.BRKGA import BRKGA
from oahf.MetaHeuristics.FirstImprovement import FirstImprovement
from oahf.MetaHeuristics.GRASP import GRASP
from oahf.MetaHeuristics.GRC import GRC
from oahf.MetaHeuristics.JobRotationLPSelector import JobRotationLPSelector
from oahf.MetaHeuristics.MultipleBestImprovement import MultipleBestImprovement
from oahf.MetaHeuristics.TabuSearch import TabuSearch
from oahf.Utils.EnumUtil import EnumUtil
from oahf.Utils.Util import Util


class HeuristicParser:
    """
    Parses heuristic definitions from a configuration file and initializes
    associated components such as neighborhoods, neighborhood selections,
    solution pools, and metaheuristics.
    """

    def __init__(self, problem_data: ProblemData):
        """
        Initializes the parser with problem data.

        Args:
            data (ProblemData): The data required to configure the heuristic components.
        """
        self.problem_data: ProblemData = problem_data
        self.definition: Dict = {}
        self.neighborhoods: Dict[int, Neighborhood] = {}
        self.neighborhood_selections: Dict[int, NeighborhoodSelection] = {}
        self.solution_pools: Dict[int, Pool] = {}
        self.metaheuristics: Dict[int, MetaHeuristic] = {}
        self.ordered_metaheuristics: List[MetaHeuristic] = []

    def parse_file(
        self, path: Union[Path, str], original_solution: Solution
    ) -> Optional[Evaluator]:
        """
        Reads and parses the configuration file at the given path.

        Args:
            path (str): Path to the configuration file.
            eval (Evaluator): Evaluation function for configuring solution pools.
        """
        with open(path, "r") as file:
            self.definition = json.load(file)

        evaluator: Optional[Evaluator] = self.parse_evaluator(
            self.definition["default_evaluator"]
        )
        if evaluator:
            self.parse_neighborhoods(evaluator)
            self.parse_neighborhood_selections()
            self.parse_solution_pools(evaluator, original_solution)
            self.parse_metaheuristics(evaluator)

            self.fill_ordered_metaheuristics()

        return evaluator

    def fill_ordered_metaheuristics(self):
        """
        Order metaheuristics based on the "execution_order" in self.definition["metaheuristics"].
        Only include metaheuristics with a defined "execution_order".
        """
        # Filter and sort definitions based on "execution_order"
        sorted_definitions = sorted(
            (d for d in self.definition["metaheuristics"] if "execution_order" in d),
            key=lambda d: d["execution_order"],
        )

        # Match the sorted definitions by "id" to the corresponding MetaHeuristic
        self.ordered_metaheuristics = [
            self.metaheuristics[definition["id"]]
            for definition in sorted_definitions
            if definition["id"] in self.metaheuristics
        ]

    def run_definition(
        self, initial_sol: Solution, evaluator: Evaluator
    ) -> Optional[Solution]:
        # Record the start time
        start_time = time.time()
        Util.set_start_timestamp(start_time)
        last_mh = None
        first = True

        for mh in self.ordered_metaheuristics:
            changed_mh = mh.name != last_mh
            if changed_mh:
                if not first:
                    Util.logger().info(
                        f"Ending execution at {Util.get_duration_from_start_timestamp()}"
                    )
                print(Util.line())
                Util.logger().info(
                    f"Started {mh.name} at {Util.get_duration_from_start_timestamp()}"
                )
                first = False
                last_mh = mh.name

            origin_pool = (
                mh.origin_pool
                if mh.origin_pool is not None
                else ListPool([initial_sol], None, evaluator)
            )
            mh.run_operation(origin_pool, mh.destination_pool)

            # Use garbage collector
            gc.collect()

        print(Util.line())
        Util.logger().info(
            f"Total Execution Time: {Util.get_duration_from_start_timestamp()}"
        )

        self.fix_all_solutions_in_pools()

        ordered_mh_size = len(self.ordered_metaheuristics)
        if self.ordered_metaheuristics:
            final_pool = self.ordered_metaheuristics[
                ordered_mh_size - 1
            ].destination_pool or ListPool(evaluator=evaluator)
            if final_pool.count() == 0:
                for pool in list(self.solution_pools.values()):
                    if not final_pool.evaluator or (
                        pool.evaluator
                        and pool.evaluator.get_solution_type()
                        == final_pool.evaluator.get_solution_type()
                    ):
                        final_pool.add_solution(pool.get_best(), None)

            return final_pool.get_best()

    def write_pools(self) -> None:
        for pool in list(self.solution_pools.values()):
            pool.write_json()

    def fix_all_solutions_in_pools(self) -> None:
        """
        Fixes all solutions in the solution pools efficiently.

        Iterates through each pool in the dictionary of solution pools,
        retrieves the list of solutions using `get_list()`, and directly
        applies `fix_solution()` to each solution using a generator expression.
        """
        # Avoid nested loops by iterating over all solutions in all pools
        for solution in (
            solution
            for pool in self.solution_pools.values()
            for solution in pool.get_list()
        ):
            solution.fix_solution()

    def get_best_solution_from_pools(
        self, original_solution: "Solution", evaluator: Evaluator
    ) -> "Solution":
        result_pool = ListPool([original_solution])

        for pool in list(self.solution_pools.values()):
            result_pool.add_solution(pool.get_best(evaluator), None)

        return result_pool.get_best(evaluator)  # type: ignore

    def parse_neighborhoods(self, evaluator: Evaluator):
        """
        Parses neighborhood definitions from the configuration and initializes instances.
        """
        try:
            self.definition["neighborhoods"] = sorted(
                self.definition["neighborhoods"], key=lambda x: x["id"]
            )

            for n in self.definition["neighborhoods"]:
                if n["name"].lower() == "alwabp_worker_oriented_insert":
                    task_ordering_rule = TaskOrderingRule(
                        EnumUtil.get_enum_from_string(
                            TaskOrderingRule, n["parameters"]["task_ordering_rule"]
                        )
                    )
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    greediness = float(n["parameters"].get("greediness", 0.0))
                    neighborhood = AlwabpWorkerOrientedInsertNS(
                        task_ordering_rule, graph_orientation, greediness
                    )
                elif n["name"].lower() == "rearrange_critical_task":
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    neighborhood = RearrangeCriticalTaskNS(graph_orientation)
                elif n["name"].lower() == "task_swap":
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    neighborhood = TaskSwapNS(graph_orientation)
                elif n["name"].lower() == "consecutive_task_swap":
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    neighborhood = ConsecutiveTaskSwapNS(graph_orientation)
                elif n["name"].lower() == "worker_swap":
                    neighborhood = WorkerSwapNS()
                elif n["name"].lower() == "worker_swap_reconstruct":
                    thread_id = 0
                    greediness = float(
                        n["parameters"]["reconstruct"].get("greediness", 0.0)
                    )
                    stop_criteria = self.parse_stop_criteria(
                        n["parameters"]["reconstruct"]["stop_criteria"]
                    )

                    if not stop_criteria:
                        raise ValueError(
                            f"No stop criteria for neighborhood: {n['name']}"
                        )

                    acceptance_criteria = self.parse_acceptance_criteria(
                        n["parameters"]["reconstruct"]["acceptance_criteria"]
                    )
                    neighborhoods = [
                        self.neighborhoods[id]
                        for id in n["parameters"]["reconstruct"]["neighborhood_ids"]
                    ]
                    ns = ListSelection(False, *neighborhoods)
                    order_moves = (
                        str(n["parameters"]["reconstruct"]["order_moves"]).lower()
                        == "true"
                    )

                    grc = GRC(
                        thread_id,
                        greediness,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                        order_moves,
                    )
                    neighborhood = WorkerSwapReconstructNS(grc, evaluator)
                elif n["name"].lower() == "alwabp_task_intensification":
                    neighborhood = AlwabpTaskIntensificationNS()
                elif n["name"].lower() == "alwabp_task_diversification":
                    neighborhood = AlwabpTaskDiversificationNS()
                elif n["name"].lower() == "alwabp_worker_intensification":
                    neighborhood = AlwabpWorkerIntensificationNS()
                elif n["name"].lower() == "alwabp_worker_diversification":
                    neighborhood = AlwabpWorkerDiversificationNS()
                else:
                    raise ValueError(f"Unavailable neighborhood: {n['name']}")
                self.neighborhoods[n["id"]] = neighborhood
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

    def parse_neighborhood_selections(self):
        """
        Parses neighborhood selection definitions from the configuration and initializes instances.
        """
        try:
            self.definition["neighborhood_selections"] = sorted(
                self.definition["neighborhood_selections"], key=lambda x: x["id"]
            )

            for n in self.definition["neighborhood_selections"]:
                if n["name"].lower() == "list_selection":
                    circular = n["parameters"]["circular"].lower() == "true"
                    neighborhoods = [
                        self.neighborhoods[id] for id in n["neighborhood_ids"]
                    ]
                    selection = ListSelection(circular, *neighborhoods)
                else:
                    raise ValueError(f"Unavailable neighborhood selection: {n['name']}")
                self.neighborhood_selections[n["id"]] = selection
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

    def parse_solution_pools(self, evaluator: Evaluator, original_solution: Solution):
        """
        Parses solution pool definitions from the configuration and initializes instances.

        Args:
            evaluator (Evaluator): Evaluation function for configuring solution pools.
        """
        try:
            if "solution_pools" not in self.definition:
                return
            for p in self.definition["solution_pools"]:
                if p["name"].lower() == "list_pool":
                    pool_evaluator = self.parse_evaluator(p["parameters"]["evaluator"])

                    solutions_file_path = p.get("solutions_file_path", None)
                    parsed_solutions = []

                    if solutions_file_path:
                        with open(solutions_file_path, "r") as file:
                            data = json.load(file)

                        solutions = data.get("solutions", [])
                        solution_type = (
                            pool_evaluator.get_solution_type()
                            if pool_evaluator
                            else evaluator.get_solution_type()
                        )
                        parsed_solutions = [
                            solution_type.from_dict(sol, original_solution)
                            for sol in solutions
                        ]

                    pool = ListPool(parsed_solutions, p["id"], evaluator=pool_evaluator)
                else:
                    raise ValueError(f"Unavailable solution pool: {p['name']}")

                self.solution_pools[p["id"]] = pool
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

    def parse_evaluator(self, evaluator_dict: dict) -> Optional[Evaluator]:
        """
        Parses evaluator configurations from a dictionary and initializes instances.

        Args:
            evaluator_dict (dict): Dictionary with evaluator definitions.

        Returns:
            Evaluator: Configured evaluator instance.
        """
        try:
            if "alwabp_evaluator" in evaluator_dict:
                config = evaluator_dict["alwabp_evaluator"]
                stop_on_first = config.get("stop_on_first", "true").lower() == "true"
                constraints = self.parse_constraints(config.get("constraints", {}))
                return AlwabpEvaluator(stop_on_first, *constraints)

            elif "job_rotation_alwabp_evaluator" in evaluator_dict:
                config = evaluator_dict["job_rotation_alwabp_evaluator"]
                stop_on_first = config.get("stop_on_first", "true").lower() == "true"
                constraints = self.parse_constraints(config.get("constraints", {}))
                return JobRotationAlwabpEvaluator(stop_on_first, *constraints)
            else:
                raise ValueError(f"Unavailable evaluator: {evaluator_dict}")
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

    def parse_constraints(self, constraints_dict: dict) -> List[Constraint]:
        """
        Parses constraints configurations from a dictionary.

        Args:
            constraints_dict (dict): Dictionary with constraint definitions.

        Returns:
            list: List of constraint instances.
        """
        constraints = []
        try:
            if "max_cycle_time" in constraints_dict:
                constraints.append(MaxCycleTimeConstraint())
            if "precedence" in constraints_dict:
                constraints.append(PrecedenceConstraint())
            if "worker_task" in constraints_dict:
                constraints.append(WorkerTaskConstraint())
            return constraints
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)
            return []

    def parse_metaheuristics(self, evaluator: Evaluator):
        """
        Parses metaheuristic definitions from the configuration and initializes instances.

        Args:
            eval (Evaluator): Evaluation function for configuring metaheuristics.
        """
        try:
            self.definition["metaheuristics"] = sorted(
                self.definition["metaheuristics"], key=lambda x: x["id"]
            )

            for m in self.definition["metaheuristics"]:
                if m["name"].lower() == "grc":
                    thread_id = 0
                    greediness = float(m["parameters"].get("greediness", 0.0))
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    ns = self.neighborhood_selections[m["neighborhood_selection"]]
                    order_moves = m["parameters"]["order_moves"].lower() == "true"
                    destination_pool = (
                        self.solution_pools[m["destination_pool"]]
                        if "destination_pool" in m
                        else None
                    )

                    meta = GRC(
                        thread_id,
                        greediness,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                        order_moves,
                        destination_pool,
                    )
                elif m["name"].lower() == "grasp":
                    thread_id = 0
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    constructions = self.metaheuristics[m["metaheuristics_used"][0]]
                    local_search = self.metaheuristics[m["metaheuristics_used"][1]]
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    origin_pool = (
                        self.solution_pools[m["origin_pool"]]
                        if "origin_pool" in m
                        else None
                    )
                    destination_pool = (
                        self.solution_pools[m["destination_pool"]]
                        if "destination_pool" in m
                        else None
                    )

                    meta = GRASP(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        constructions,
                        local_search,
                        acceptance_criteria,  # type: ignore
                        origin_pool,
                        destination_pool,
                    )
                elif m["name"].lower() == "first_improvement":
                    thread_id = 0
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    ns = self.neighborhood_selections[m["neighborhood_selection"]]

                    meta = FirstImprovement(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                    )
                elif m["name"].lower() == "best_improvement":
                    thread_id = 0
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    ns = self.neighborhood_selections[m["neighborhood_selection"]]

                    meta = BestImprovement(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                    )
                elif m["name"].lower() == "multiple_best_improvement":
                    thread_id = 0
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    ns = self.neighborhood_selections[m["neighborhood_selection"]]
                    destination_pool = (
                        self.solution_pools[m["destination_pool"]]
                        if "destination_pool" in m
                        else None
                    )

                    meta = MultipleBestImprovement(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                        destination_pool,
                    )
                elif m["name"].lower() == "job_rotation_lp_selector":
                    thread_id = 0
                    number_of_periods = int(m["parameters"].get("number_of_periods", 1))
                    gurobi_path = Path(m["parameters"].get("gurobi_path", None))
                    origin_pool = (
                        self.solution_pools[m["origin_pool"]]
                        if "origin_pool" in m
                        else None
                    )
                    destination_pool = (
                        self.solution_pools[m["destination_pool"]]
                        if "destination_pool" in m
                        else None
                    )
                    tolerance_percentage: Optional[float] = (
                        float(m["parameters"].get("tolerance_percentage", None))
                        if m["parameters"].get("tolerance_percentage", None)
                        else None
                    )

                    meta = JobRotationLPSelector(
                        thread_id,
                        number_of_periods,
                        gurobi_path,
                        self.problem_data,
                        tolerance_percentage,
                        origin_pool,
                        destination_pool,
                    )
                elif m["name"].lower() == "brkga":
                    thread_id = 0
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    origin_pool = (
                        self.solution_pools[m["origin_pool"]]
                        if "origin_pool" in m
                        else None
                    )
                    destination_pool = (
                        self.solution_pools[m["destination_pool"]]
                        if "destination_pool" in m
                        else None
                    )

                    population_size: int = m["parameters"].get("population_size", 100)
                    elite_fraction: float = m["parameters"].get("elite_fraction", 0.2)
                    mutant_fraction: float = m["parameters"].get("mutant_fraction", 0.1)
                    bias: float = m["parameters"].get("bias", 0.7)

                    meta = BRKGA(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        population_size,
                        elite_fraction,
                        mutant_fraction,
                        bias,
                        origin_pool,
                        destination_pool,
                    )
                elif m["name"].lower() == "tabu":
                    thread_id = 0
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    ns = self.neighborhood_selections[m["neighborhood_selection"]]
                    intensification_criteria = self.parse_stop_criteria(
                        m["parameters"]["intensification_criteria"]
                    )
                    second_level_ns = self.neighborhood_selections[
                        m["parameters"]["second_neighborhood_selection"]
                    ]
                    intensification_ns = self.neighborhood_selections[
                        m["parameters"]["intensification_neighborhood_selection"]
                    ]
                    diversification_ns = self.neighborhood_selections[
                        m["parameters"]["diversification_neighborhood_selection"]
                    ]

                    if not isinstance(
                        intensification_criteria, StopTimeIterationCriteria
                    ):
                        raise ValueError(
                            f"Intensification Criteria must be StopTimeIterationCriteria. Metaheuristic {m['id']}: {m['name']}"
                        )

                    intensification_ls = self.metaheuristics[
                        int(m["parameters"]["intensification_local_search"])
                    ]
                    diversification_ls = self.metaheuristics[
                        int(m["parameters"]["diversification_local_search"])
                    ]

                    meta = TabuSearch(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                        intensification_criteria,
                        second_level_ns,
                        intensification_ns,
                        diversification_ns,
                        intensification_ls,
                        diversification_ls,
                    )
                else:
                    raise ValueError(f"Unavailable metaheuristic: {m['name']}")
                self.metaheuristics[m["id"]] = meta
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

    def parse_stop_criteria(self, criteria: dict) -> Optional[StopCriteria]:
        """
        Parses stop criteria from a criteria dictionary.

        Args:
            criteria (dict): Dictionary with stopping conditions.

        Returns:
            Optional[StopCriteria]: Configured StopCriteria instance or None if not available.
        """
        try:
            if not criteria:
                return None
            elif "time_iteration" in criteria:
                seconds = (
                    float(criteria["time_iteration"].get("seconds"))
                    if "seconds" in criteria["time_iteration"]
                    else None
                )
                iterations = (
                    int(criteria["time_iteration"].get("iterations"))
                    if "iterations" in criteria["time_iteration"]
                    else None
                )
                return StopTimeIterationCriteria(seconds, iterations)
            elif "workers_unassigned" in criteria:
                num_unassigned_workers = int(
                    criteria["workers_unassigned"]["num_unassigned_workers"]
                )
                return WorkersUnassignedStopCriteria(num_unassigned_workers)
            elif "tasks_unassigned" in criteria:
                num_unassigned_tasks = int(
                    criteria["tasks_unassigned"]["num_unassigned_tasks"]
                )
                return TasksUnassignedStopCriteria(num_unassigned_tasks)
            elif "max_cycle_time" in criteria:
                cycle_time_limit = int(criteria["max_cycle_time"]["cycle_time_limit"])
                return MaxCycleTimeStopCriteria(cycle_time_limit)
            elif "no_stop" in criteria:
                return NoStopCriteria()
            elif "multiple_stop_criteria" in criteria:
                stop_when_any = (
                    criteria["multiple_stop_criteria"]["stop_when_any"].lower()
                    == "true"
                )
                multiple_criterias = [
                    parsed
                    for other_criteria in criteria["multiple_stop_criteria"][
                        "stop_criterias"
                    ]
                    if (parsed := self.parse_stop_criteria(other_criteria)) is not None
                ]
                return MultipleStopCriteria(stop_when_any, *multiple_criterias)
            elif "no_improvement" in criteria:
                iterations_no_improv = int(
                    criteria["no_improvement"]["iterations_no_improv"]
                )
                seconds = (
                    float(criteria["no_improvement"].get("seconds"))
                    if "seconds" in criteria["no_improvement"]
                    else None
                )
                iterations = (
                    int(criteria["no_improvement"].get("iterations"))
                    if "iterations" in criteria["no_improvement"]
                    else None
                )
                perc_improv = (
                    int(criteria["no_improvement"].get("perc_improv"))
                    if "perc_improvement" in criteria["no_improvement"]
                    else None
                )
                return StopNoImprovement(
                    iterations_no_improv, seconds, iterations, perc_improv
                )
            else:
                raise ValueError(f"Unavailable stop criteria: {criteria}")
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

    def parse_acceptance_criteria(self, criteria: dict) -> Optional[AcceptanceCriteria]:
        """
        Parses acceptance criteria from a criteria dictionary.

        Args:
            criteria (dict): Dictionary with acceptance conditions.

        Returns:
            Optional[AcceptanceCriteria]: Configured AcceptanceCriteria instance or None if not available.
        """
        try:
            if not criteria:
                return None
            elif "better_or_same" in criteria:
                return BetterOrSameAcceptanceCriteria()
            elif "better" in criteria:
                return BetterAcceptanceCriteria()
            elif "always" in criteria:
                return AlwaysAcceptAcceptanceCriteria()
            else:
                raise ValueError(f"Unavailable acceptance criteria: {criteria}")
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)
