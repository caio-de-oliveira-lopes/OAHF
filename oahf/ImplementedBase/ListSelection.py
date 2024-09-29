from typing import Iterable, List

from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection


class ListSelection(NeighborhoodSelection):
    def __init__(self, circular: bool, *neighborhoods: Neighborhood):
        """
        Initializes a ListSelection with the provided neighborhoods.
        :param circular: If True, the selection will wrap around.
        :param neighborhoods: A list of Neighborhood instances.
        """
        self.circular = circular
        self.neighborhoods = list(neighborhoods)
        self.enumerator = iter(self.neighborhoods)

    def copy(self) -> "ListSelection":
        """Creates a copy of the current ListSelection instance."""
        return ListSelection(
            self.circular, *(neighborhood.copy() for neighborhood in self.neighborhoods)
        )

    def get_all(self) -> Iterable[Neighborhood]:
        """Returns all neighborhoods."""
        return self.neighborhoods

    def get_next(self, thread_id: int) -> Neighborhood:
        """Returns the next neighborhood, cycling if necessary."""
        try:
            return next(self.enumerator)
        except StopIteration:
            if self.circular:
                self.reset(thread_id)
                return next(self.enumerator)
            else:
                raise

    def reset(self, thread_id: int) -> None:
        """Resets the enumerator."""
        self.enumerator = iter(self.neighborhoods)

    def remove(self, neighborhood: Neighborhood) -> None:
        """Removes a neighborhood from the selection."""
        self.neighborhoods.remove(neighborhood)
        self.enumerator = iter(self.neighborhoods)
