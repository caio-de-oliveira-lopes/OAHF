class PairStore:
    """
    A class to efficiently store and check pairs of numbers, treating (a, b) and (b, a) as the same pair.
    """

    def __init__(self):
        self.pairs = set()

    def add_pair(self, a, b):
        """
        Adds a pair (a, b) to the store. Order does not matter.

        :param a: First number of the pair.
        :param b: Second number of the pair.
        """
        self.pairs.add((min(a, b), max(a, b)))

    def has_pair(self, a, b):
        """
        Checks if the pair (a, b) is already in the store.

        :param a: First number of the pair.
        :param b: Second number of the pair.
        :return: True if the pair is in the store, otherwise False.
        """
        return (min(a, b), max(a, b)) in self.pairs
