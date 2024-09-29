from abc import ABC
import threading

class Entity(ABC):
    """Represents a base entity with an auto-generated id and class name as the default name."""
    
    # Class-level counter for automatically assigning IDs
    _instance_counter = 0
    _lock = threading.Lock()  # Lock for thread-safe ID generation

    def __init__(self, entity_id: int = None, name: str = None) -> None:
        """Initializer that sets the id and name. The id is auto-generated, and the name defaults to the class name."""
        
        # Increment the class-level counter for the ID
        with Entity._lock:
            if entity_id is None:
                Entity._instance_counter += 1
                self.__id = Entity._instance_counter
            else:
                self.__id = entity_id
        
        # Set the name to the class name if not provided
        if name is None:
            self.__name = self.__class__.__name__.upper()
        else:
            self.__name = name
    
    @property
    def id(self) -> int:
        """Getter for the entity ID."""
        return self.__id
    
    @id.setter
    def id(self, entity_id: int) -> None:
        """Setter for the entity ID."""
        self.__id = entity_id
    
    @property
    def name(self) -> str:
        """Getter for the entity name."""
        return self.__name
    
    @name.setter
    def name(self, name: str) -> None:
        """Setter for the entity name."""
        self.__name = name
    
    def __str__(self) -> str:
        """String representation of the entity in the format 'name_id'."""
        return f'{self.__name}_{self.__id}'
