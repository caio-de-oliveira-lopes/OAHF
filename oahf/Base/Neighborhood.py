from abc import ABC, abstractmethod

from oahf.Base.Entity import Entity
from oahf.Base.Movement import Movement
from oahf.Base.Solution import Solution


class Neighborhood(Entity, ABC):
    def __init__(
        self,
        is_perturbation: bool = False,
    ) -> None:
        """
        Initializes the Neighborhood object with the specified stop criteria and perturbation flag.

        Args:
            is_perturbation (bool): A flag indicating if the neighborhood is a perturbation. Default is False.
        """
        super().__init__()
        self.is_perturbation: bool = is_perturbation
        self._allow_infeasible_movements: bool = False

    @property
    def allow_infeasible_movements(self) -> bool:
        return self._allow_infeasible_movements

    @allow_infeasible_movements.setter
    def allow_infeasible_movements(self, value: bool) -> None:
        self._allow_infeasible_movements = value

    @abstractmethod
    def copy(self) -> "Neighborhood":
        """Abstract method to create a copy of the neighborhood."""
        raise NotImplementedError

    def build_neighborhood_operation(
        self, thread_id: int, solution: "Solution"
    ) -> bool:
        """
        Builds the neighborhood operation for the given solution and thread ID.

        Args:
            thread_id (int): The ID of the thread.
            solution (Solution): The solution to operate on.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        self.clear_related_keys()
        return self.build_neighborhood(thread_id, solution)

    @abstractmethod
    def build_neighborhood(self, thread_id: int, solution: "Solution") -> bool:
        """Abstract method to build the neighborhood. To be implemented in subclasses."""
        raise NotImplementedError

    @abstractmethod
    def get_move(self) -> "Movement":
        """Abstract method to get a movement. To be implemented in subclasses."""
        raise NotImplementedError

    def reset(self, solution: "Solution") -> None:
        """Resets the neighborhood for the given solution. Can be overridden by subclasses."""
        pass

    def accept_movement(self) -> None:
        """Accepts the movement and clears related keys."""
        self.clear_related_keys()

    def clear_related_keys(self) -> None:
        """Clears related keys. Can be overridden by subclasses."""
        pass