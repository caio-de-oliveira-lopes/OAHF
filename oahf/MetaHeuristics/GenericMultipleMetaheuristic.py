from typing import List, Optional
import gc

from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.ListPool import ListPool
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import AlwaysAcceptAcceptanceCriteria
from oahf.Utils.Util import Util

class GenericMultipleMetaheuristic(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop_criteria: StopCriteria,
        evaluator,
        metaheuristics: List[MetaHeuristic],
        origin_pool: Optional[Pool] = None,
        destination_pool: Optional[Pool] = None,
    ):
        """
        A wrapper MH that sequentially executes a list of metaheuristics
        until stop criteria is met.
        """

        super().__init__(
            thread_id,
            stop_criteria,
            evaluator,
            AlwaysAcceptAcceptanceCriteria(),
            neighborhood_selection=None,
            meta_heuristics_used=metaheuristics,
            origin_pool=origin_pool,
            destination_pool=destination_pool,
        )

    def copy(self, thread: int) -> "GenericMultipleMetaheuristic":
        return GenericMultipleMetaheuristic(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            [mh.copy(thread) for mh in self.meta_heuristics_used],
            self.origin_pool.copy() if self.origin_pool else None,
            self.destination_pool.copy() if self.destination_pool else None,
        )

    def run(self, sol):
        """
        Optional single solution interface: just wrap it in a ListPool.
        """
        pool = ListPool([sol], None, self.evaluator)
        out = ListPool([], None, self.evaluator)
        return self.run_operation(pool, out).get_best(self.evaluator)

    def run_operation(
        self,
        origin_pool: Pool,
        destination_pool: Optional[Pool] = None,
        parent: Optional[MetaHeuristic] = None,
    ) -> Pool:
        """
        Sequentially invokes each MH in metaheuristics_used until stopping.
        """
        self.parent_metaheuristic = parent

        # Set up destination pool
        dest = destination_pool if destination_pool else ListPool([], None, self.evaluator)

        # Reset stop criteria
        self.stop_criteria.reset()

        last_name = None
        first = True

        # Loop until any stop criterion trips
        while not self.stop_on_evaluations([]):
            for mh in self.meta_heuristics_used:
                # Only log when MH changes
                if mh.name != last_name:
                    if not first:
                        Util.logger().info(
                            f"Finished {last_name} at {Util.get_duration_from_start_timestamp()}."
                        )
                    Util.logger().info(Util.line())
                    Util.logger().info(
                        f"Starting {mh.name} at {Util.get_duration_from_start_timestamp()}."
                    )
                    first = False
                    last_name = mh.name

                # Optional: Include this mh as its named on for loggin purposes
                #mh.named_parent = self

                current_origin_pool = (
                    mh.origin_pool
                    if mh.origin_pool is not None
                    else origin_pool
                )

                # Execute and get new pool
                mh.run_operation(current_origin_pool, mh.destination_pool, self)

                # Force Python to reclaim temporary objects
                gc.collect()

                # If at any point we met our stopping criterion, bail out
                if self.stop_on_evaluations([]):
                    break

            # Optionally increment a counter for composite iterations
            self.stop_criteria.increment_counter()

        # Final logging
        if last_name is not None:
            Util.logger().info(
                f"Ending execution of {last_name} at {Util.get_duration_from_start_timestamp()}."
            )

        return dest