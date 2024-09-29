from typing import Iterable, List, Tuple

from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.ThreadManager import ThreadManager


class ProbabilityListSelection(NeighborhoodSelection):
    def __init__(self, circular: bool, *neighborhoods: Tuple[Neighborhood, float]):
        """
        Initializes a ProbabilityListSelection with the provided neighborhoods and their probabilities.
        :param circular: If True, the selection will wrap around.
        :param neighborhoods: A list of tuples, each containing a Neighborhood instance and its probability.
        """
        self.circular = circular
        self.neighborhoods_prob = list(neighborhoods)
        self.neighborhoods = []
        self.enumerator = iter(self.neighborhoods)
        self.randomized = False

    def copy(self) -> "ProbabilityListSelection":
        """Creates a copy of the current ProbabilityListSelection instance."""
        return ProbabilityListSelection(
            self.circular,
            *(
                Tuple(neighborhood.copy(), prob)
                for neighborhood, prob in self.neighborhoods_prob
            )
        )

    def get_all(self) -> Iterable[Neighborhood]:
        """Returns all neighborhoods."""
        return (neighborhood for neighborhood, _ in self.neighborhoods_prob)

    def get_next(self, thread_id: int) -> Neighborhood:
        """Returns the next neighborhood, cycling if necessary."""
        if not self.randomized:
            self.reset(thread_id)
        try:
            return next(self.enumerator)
        except StopIteration:
            if self.circular:
                self.reset(thread_id)
                return next(self.enumerator)
            else:
                raise

    def reset(self, thread_id: int) -> None:
        """Resets the enumerator with neighborhoods ordered by their probabilities."""
        self.neighborhoods = sorted(
            self.neighborhoods_prob,
            key=lambda x: ThreadManager.get_next_double(thread_id) * x[1],
            reverse=True,
        )
        self.enumerator = iter(neighborhood for neighborhood, _ in self.neighborhoods)
        self.randomized = True

    def remove(self, neighborhood: Neighborhood) -> None:
        """Removes a neighborhood from the selection."""
        self.neighborhoods_prob = [
            t for t in self.neighborhoods_prob if t[0] != neighborhood
        ]
        self.neighborhoods = [n for n in self.neighborhoods if n != neighborhood]
        self.enumerator = iter(self.neighborhoods)
