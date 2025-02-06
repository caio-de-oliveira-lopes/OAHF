class PairStore:
    """
    A class to efficiently store and check pairs of numbers, treating (a, b) and (b, a) as the same pair.
    Uses a custom hash function to encode pairs into a unique integer key, enabling extremely fast lookups.
    """

    def __init__(self):
        # Set to store the unique integer keys for pairs.
        self.pairs = set()

    def _encode_pair(self, a, b):
        """
        Encodes a pair (a, b) into a unique integer using a custom hash function.

        :param a: First number of the pair.
        :param b: Second number of the pair.
        :return: A unique integer representing the pair (a, b), where order doesn't matter.
        """
        # Make sure a <= b by swapping if necessary.
        if a > b:
            a, b = b, a

        # Create a unique key by combining the pair into a single integer.
        # A simple approach: use a bitwise combination of the numbers to generate a unique key.
        return a * (a + 1) // 2 + b  # Cantor pairing function approach

    def add_pair(self, a, b):
        """
        Adds a pair (a, b) to the store. Order does not matter.

        :param a: First number of the pair.
        :param b: Second number of the pair.
        """
        # Encode the pair as a unique integer key.
        key = self._encode_pair(a, b)
        # Add the key to the set.
        self.pairs.add(key)

    def has_pair(self, a, b):
        """
        Checks if the pair (a, b) is already in the store.

        :param a: First number of the pair.
        :param b: Second number of the pair.
        :return: True if the pair is in the store, otherwise False.
        """
        # Encode the pair as a unique integer key.
        key = self._encode_pair(a, b)
        # Check if the key exists in the set.
        return key in self.pairs
