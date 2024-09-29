from typing import List

from oahf.Base.Neighborhood import Neighborhood
from oahf.Base.NeighborhoodSelection import NeighborhoodSelection
from oahf.Base.ThreadManager import ThreadManager


class RandomListSelection(NeighborhoodSelection):
    def __init__(self, circular: bool, *neighborhoods: Neighborhood):
        """
        Initializes a RandomListSelection with a list of neighborhoods.
        :param circular: Indicates whether the selection is circular.
        :param neighborhoods: Neighborhood instances to include in the selection.
        """
        super().__init__()
        self.randomized: bool = False
        self.circular: bool = circular
        self.neighborhoods: List[Neighborhood] = list(neighborhoods)
        self.enumerator = iter(self.neighborhoods)

    def copy(self) -> "RandomListSelection":
        """
        Creates a copy of the current RandomListSelection instance.
        :return: A new RandomListSelection instance with copied neighborhoods.
        """
        return RandomListSelection(
            self.circular, *(neighborhood.copy() for neighborhood in self.neighborhoods)
        )

    def get_all(self) -> List[Neighborhood]:
        """
        Returns all neighborhoods in the selection.
        :return: A list of all Neighborhood instances.
        """
        return self.neighborhoods

    def get_next(self, thread_id: int) -> Neighborhood:
        """
        Gets the next neighborhood from the selection.
        :param thread_id: The ID of the current thread.
        :return: The next Neighborhood instance.
        """
        if not self.randomized:
            self.reset(thread_id)
        worked = self.enumerator.move_next()
        if not worked and self.circular:
            self.reset(thread_id)
            worked = self.enumerator.move_next()
        return self.enumerator.current

    def reset(self, thread_id: int) -> None:
        """
        Resets the neighborhood selection, shuffling the neighborhoods.
        :param thread_id: The ID of the current thread.
        """
        self.neighborhoods.sort(key=lambda x: ThreadManager.get_next_double(thread_id))
        self.enumerator = iter(self.neighborhoods)
        self.randomized = True

    def remove(self, neighborhood: Neighborhood) -> None:
        """
        Removes a neighborhood from the selection.
        :param neighborhood: The Neighborhood instance to remove.
        """
        self.neighborhoods.remove(neighborhood)
        self.enumerator = iter(self.neighborhoods)
