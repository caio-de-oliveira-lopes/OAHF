import random
import time
from typing import Callable, Dict, Iterable, TypeVar

TSource = TypeVar('TSource')

class ThreadManager:
    _random_keys: Dict[int, random.Random] = {}
    _watch: float = 0.0

    @classmethod
    def initialize(cls, num_threads: int, seed: int = None) -> None:
        """Initializes the ThreadManager with a specified number of threads and an optional seed for randomness."""
        cls._watch = time.time()
        cls._random_keys = {}
        for i in range(num_threads):
            if seed is None:
                cls._random_keys[i] = random.Random()
            else:
                cls._random_keys[i] = random.Random(seed + i)

    @classmethod
    def get_next_double(cls, thread_id: int) -> float:
        """Gets the next random double for the specified thread ID."""
        return cls._random_keys[thread_id].random()

    @classmethod
    def get_next(cls, thread_id: int, min_value: int, max_value: int) -> int:
        """Gets the next random integer between min_value and max_value for the specified thread ID."""
        return cls._random_keys[thread_id].randint(min_value, max_value)

    @classmethod
    def for_each(cls, thread_id: int, source: Iterable[TSource], action: Callable[[TSource], None]) -> None:
        """Executes an action for each element in the source iterable using the specified thread ID."""
        for item in source:
            action(item)

    @classmethod
    def for_range(cls, thread_id: int, from_index: int, to_index: int, action: Callable[[int], None]) -> None:
        """Executes an action for each integer in the specified range using the specified thread ID."""
        for i in range(from_index, to_index):
            action(i)

    @classmethod
    def main_for(cls, num_threads: int, action: Callable[[int], None]) -> None:
        """Executes the specified action for each thread in parallel."""
        if not cls._random_keys:
            cls.initialize(num_threads)
        cls.for_range(0, num_threads, action)
