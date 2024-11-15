import json
from pathlib import Path
from typing import Optional, Union

from oahf.Base import AcceptanceCriteria
from oahf.Base.Evaluator import Evaluator
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.AlwabpSolution import (
    GraphOrientation,
    MaxPositionalWeightType,
)
from oahf.ImplementedBase.AlwabpWorkerOrientedInsertNS import (
    AlwabpWorkerOrientedInsertNS,
)
from oahf.ImplementedBase.BetterOrSameAcceptanceCriteria import (
    BetterOrSameAcceptanceCriteria,
)
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.WorkersUnassignedStopCriteria import (
    WorkersUnassignedStopCriteria,
)
from oahf.Logger.LogManager import LogManager
from oahf.MetaHeuristics.GRC import GRC
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
        self.definition = {}
        self.neighborhoods = {}
        self.neighborhood_selections = {}
        self.solution_pools = {}
        self.metaheuristics = {}
        self.ordered_metaheuristics = []
        self.metaheuristics_flow = {}

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

    def parse_neighborhoods(self):
        """
        Parses neighborhood definitions from the configuration and initializes instances.
        """
        try:
            for n in self.definition["neighborhoods"]:
                if n["name"].lower() == "alwabp_worker_oriented_insert_ns":
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
                    greediness = int(n["parameters"]["greediness"])

                    neighborhood = AlwabpWorkerOrientedInsertNS(
                        pw, graph_orientation, greediness
                    )
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
            for m in self.definition["metaheuristics"]:
                if m["name"].lower() == "grc":
                    thread_id = 0
                    greediness = int(m["parameters"]["greediness"])
                    stop_criteria = self.parse_stop_criteria(m["stop_criteria"])
                    acceptance_criteria = self.parse_acceptance_criteria(
                        m["acceptance_criteria"]
                    )
                    ns = self.neighborhood_selections[m["neighborhood_selection"]]
                    order_moves = m["parameters"]["order_moves"].lower() == "true"

                    meta = GRC(
                        thread_id,
                        greediness,
                        stop_criteria,
                        evaluator,  # type: ignore
                        acceptance_criteria,
                        ns,
                        order_moves,
                    )  # type: ignore
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
            elif "workers_unassigned" in criteria:
                num_unassigned_workers = int(
                    criteria["workers_unassigned"]["num_unassigned_workers"]
                )
                return WorkersUnassignedStopCriteria(num_unassigned_workers)
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
            else:
                raise ValueError(f"Unavailable acceptance criteria: {criteria}")
        except Exception as e:
            LogManager.something_went_wrong(Util.get_current_method_name(), e)
