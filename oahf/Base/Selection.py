from abc import ABC, abstractmethod

class Selection(ABC):
    def __init__(self, thread_id: int, evaluator: Evaluator):
        """Initialize the Selection with a thread ID and an Evaluator."""
        self.thread_id = thread_id
        self.evaluator = evaluator

    @abstractmethod
    def run(self, pool: Pool) -> Solution:
        """Run the selection process on the given pool."""
        pass

    @abstractmethod
    def copy(self, thread: int) -> 'Selection':
        """Create a copy of the selection for a specified thread."""
        pass
