import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from oahf.Base import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.MultipleStopCriteria import MultipleStopCriteria
from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.Pool import Pool
from oahf.Base.Solution import Solution
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpSolution import (
    GraphOrientation,
    MaxPositionalWeightType,
)
from oahf.ImplementedBase.AlwabpWorkerOrientedInsertNS import (
    AlwabpWorkerOrientedInsertNS,
)
from oahf.ImplementedBase.BetterAcceptanceCriteria import BetterAcceptanceCriteria
from oahf.ImplementedBase.BetterOrSameAcceptanceCriteria import (
    BetterOrSameAcceptanceCriteria,
)
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.MaxCycleTimeStopCriteria import MaxCycleTimeStopCriteria
from oahf.ImplementedBase.NoStopCriteria import NoStopCriteria
from oahf.ImplementedBase.RearrangeCriticalTaskNS import RearrangeCriticalTaskNS
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.ImplementedBase.TaskSwapNS import TaskSwapNS
from oahf.ImplementedBase.WorkersUnassignedStopCriteria import (
    WorkersUnassignedStopCriteria,
)
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.BestImprovement import BestImprovement
from oahf.MetaHeuristics.FirstImprovement import FirstImprovement
from oahf.MetaHeuristics.GRASP import GRASP
from oahf.MetaHeuristics.GRC import GRC
from oahf.MetaHeuristics.MultipleBestImprovement import MultipleBestImprovement
from oahf.Utils.EnumUtil import EnumUtil
from oahf.Utils.Util import Util


class HeuristicParser:
    """
    Parses heuristic definitions from a configuration file and initializes
    associated components such as neighborhoods, neighborhood selections,
    solution pools, and metaheuristics.
    """

    def __init__(self):
        """
        Initializes the parser with problem data.

        Args:
            data (ProblemData): The data required to configure the heuristic components.
        """
        self.definition: Dict = {}
        self.neighborhoods: Dict[int, Neighborhood] = {}
        self.neighborhood_selections: Dict[int, NeighborhoodSelection] = {}
        self.solution_pools: Dict[int, Pool] = {}
        self.metaheuristics: Dict[int, MetaHeuristic] = {}
        self.ordered_metaheuristics: List[MetaHeuristic] = []

    def parse_file(self, path: Union[Path, str], evaluator: Evaluator):
        """
        Reads and parses the configuration file at the given path.

        Args:
            path (str): Path to the configuration file.
            eval (Evaluator): Evaluation function for configuring solution pools.
        """
        with open(path, "r") as file:
            self.definition = json.load(file)

        self.parse_neighborhoods()
        self.parse_neighborhood_selections()
        self.parse_solution_pools(evaluator)
        self.parse_metaheuristics(evaluator)

        self.fill_ordered_metaheuristics()

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
        for mh in self.ordered_metaheuristics:
            origin_pool = (
                mh.origin_pool
                if mh.origin_pool is not None
                else ListPool([initial_sol])
            )
            mh.run_operation(origin_pool, mh.destination_pool)

        final_pool = ListPool()
        for pool in list(self.solution_pools.values()):
            final_pool.add_solution(pool.get_best(evaluator))

        return final_pool.get_best(evaluator)

    def parse_neighborhoods(self):
        """
        Parses neighborhood definitions from the configuration and initializes instances.
        """
        try:
            self.definition["neighborhoods"] = sorted(
                self.definition["neighborhoods"], key=lambda x: x["id"]
            )

            for n in self.definition["neighborhoods"]:
                if n["name"].lower() == "alwabp_worker_oriented_insert":
                    pw = MaxPositionalWeightType(
                        EnumUtil.get_enum_from_string(
                            MaxPositionalWeightType, n["parameters"]["pw"]
                        )
                    )
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    greediness = float(n["parameters"].get("greediness", 0.0))
                    fixed_workers = (
                        n["parameters"].get("fixed_workers", "false").lower() == "true"
                    )
                    neighborhood = AlwabpWorkerOrientedInsertNS(
                        pw, graph_orientation, greediness, None, fixed_workers
                    )
                elif n["name"].lower() == "rearrange_critical_task":
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    neighborhood = RearrangeCriticalTaskNS(graph_orientation, None)
                elif n["name"].lower() == "task_swap":
                    graph_orientation = GraphOrientation(
                        EnumUtil.get_enum_from_string(
                            GraphOrientation, n["parameters"]["graph_orientation"]
                        )
                    )
                    neighborhood = TaskSwapNS(graph_orientation, None)
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

    def parse_solution_pools(self, evaluator: Evaluator):
        """
        Parses solution pool definitions from the configuration and initializes instances.

        Args:
            eval (Evaluator): Evaluation function for configuring solution pools.
        """
        try:
            if "solution_pools" not in self.definition:
                return
            for p in self.definition["solution_pools"]:
                if p["name"].lower() == "list_pool":
                    pool = ListPool()
                else:
                    raise ValueError(f"Unavailable solution pool: {p['name']}")
                self.solution_pools[p["id"]] = pool
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)

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

                    meta = GRC(
                        thread_id,
                        greediness,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
                        order_moves,
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
                    meta = MultipleBestImprovement(
                        thread_id,
                        stop_criteria,  # type: ignore
                        evaluator,
                        acceptance_criteria,  # type: ignore
                        ns,
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
            else:
                raise ValueError(f"Unavailable acceptance criteria: {criteria}")
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)
