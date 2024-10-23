from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.Evaluation import Evaluation
from oahf.Base.Solution import Solution
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class ExecutedByAvailableWorkersAcceptanceCriteria(AcceptanceCriteria):
    def accept(
        self, curr_eval: Evaluation, next_eval: Evaluation, next_sol: AlwabpSolution
    ) -> bool:
        """
        Determines whether to accept the next solution based on the evaluation.
        Accept if at least one available worker can execute the open stations.

        :param curr_eval: The current evaluation.
        :param next_eval: The next evaluation.
        :param next_sol (AlwabpSolution): The next solution.
        :return: True if the next solution is better or equal, False otherwise.
        """
        stations = next_sol.get_open_stations()
        num_stations = len(stations)
        feasible = 0

        for station in stations:
            for worker in next_sol.unassigned_workers:
                if next_sol.station_would_be_feasible(station, worker):
                    feasible += 1
                    break

        if feasible == num_stations:
            return True

        return False

    def copy(self) -> "ExecutedByAvailableWorkersAcceptanceCriteria":
        """
        Creates a copy of the current instance.

        :return: A new instance of BetterOrSameAcceptanceCriteria.
        """
        return self

    def reset(self) -> None:
        """
        Resets the acceptance criteria state.
        """
        pass
