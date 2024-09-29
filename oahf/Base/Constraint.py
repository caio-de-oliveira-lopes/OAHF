from abc import ABC, abstractmethod
from oahf.Base.Entity import Entity

class Constraint(ABC):
    
    @abstractmethod
    def evaluate(self, solution: 'Solution') -> 'ConstraintEvaluation':
        """
        Abstract method to evaluate the constraint based on a solution.
        :param solution: A Solution object.
        :return: A ConstraintEvaluation object.
        """
        pass

    def evaluate_with_stop_criteria(self, solution: 'Solution', stop_criteria: 'StopCriteria') -> 'ConstraintEvaluation':
        """
        Virtual method to evaluate the constraint, optionally considering stop criteria.
        :param solution: A Solution object.
        :param stop_criteria: A StopCriteria object.
        :return: A ConstraintEvaluation object (default behavior is to ignore stop criteria).
        """
        return self.evaluate(solution)
