from collections import defaultdict
from typing import Dict
from oahf.Base.Entity import Entity
from oahf.Base.Evaluation import Evaluation

class SharedMemory(Entity):
    def __init__(self):
        """Initialize the shared memory with a thread-safe dictionary for solution nodes."""        
        super().__init__()
        self.solution_nodes: Dict[str, Evaluation] = defaultdict(Evaluation)

    def add_solution_node(self, key: str, evaluation: Evaluation) -> bool:
        """Add a solution node to the shared memory."""
        # Adding to a regular dictionary; thread safety can be managed as needed
        self.solution_nodes[key] = evaluation
        return True

    def get_solution_node(self, key: str) -> Evaluation:
        """Retrieve a solution node from the shared memory."""
        return self.solution_nodes.get(key)

    def remove_solution_node(self, key: str) -> bool:
        """Remove a solution node from the shared memory."""
        if key in self.solution_nodes:
            del self.solution_nodes[key]
            return True
        return False
