from abc import ABC, abstractmethod
from typing import Iterable, List, Optional

from oahf.Base.Entity import Entity
from oahf.Base.Neighborhood import Neighborhood


class NeighborhoodSelection(Entity, ABC):
    def __init__(self):
        super().__init__()
        self.neighborhoods: List[Neighborhood] = []
        self.circular: bool = False

    @abstractmethod
    def get_next(self, thread_id: int) -> Optional[Neighborhood]:
        """Retrieve the next neighborhood based on the thread ID."""
        pass

    @abstractmethod
    def get_all(self) -> Iterable[Neighborhood]:
        """Retrieve all neighborhoods."""
        pass

    @abstractmethod
    def reset(self, thread_id: int):
        """Reset the selection of neighborhoods based on the thread ID."""
        pass

    @abstractmethod
    def copy(self) -> "NeighborhoodSelection":
        """Create a copy of the current neighborhood selection."""
        pass

    @abstractmethod
    def remove(self, neighborhood: Neighborhood):
        """Remove a specific neighborhood from the selection."""
        pass

    def set_circular(self, circular: bool):
        """Set whether the neighborhood selection is circular."""
        self.circular = circular
