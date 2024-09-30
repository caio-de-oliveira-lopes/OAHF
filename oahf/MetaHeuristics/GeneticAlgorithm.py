from oahf.Base.AcceptanceCriteria import AcceptanceCriteria
from oahf.Base.CrossOver import CrossOver
from oahf.Base.Evaluator import Evaluator
from oahf.Base.MetaHeuristic import MetaHeuristic
from oahf.Base.Pool import Pool
from oahf.Base.Selection import Selection
from oahf.Base.StopCriteria import StopCriteria
from oahf.ImplementedBase.ListPool import ListPool
from oahf.MetaHeuristics.Pertubation import Pertubation


class GeneticAlgorithm(MetaHeuristic):
    def __init__(
        self,
        thread_id: int,
        stop: StopCriteria,
        evaluator: Evaluator,
        mutations: Pertubation,
        construction: MetaHeuristic,
        selection: Selection,
        crossover: CrossOver,
        criteria: AcceptanceCriteria,
    ) -> None:
        """Initialize the Genetic Algorithm meta-heuristic.

        Args:
            thread_id (int): The ID of the thread.
            stop (StopCriteria): The stopping criteria.
            evaluator (Evaluator): The evaluator for solutions.
            mutations (Pertubation): The mutation strategy.
            construction (MetaHeuristic): The construction meta-heuristic.
            selection (Selection): The selection strategy.
            crossover (CrossOver): The crossover strategy.
            criteria (AcceptanceCriteria): The acceptance criteria for solutions.
        """
        super().__init__(thread_id, stop, evaluator, criteria, mutations, construction)
        self.construction = construction
        self.selection = selection
        self.crossover = crossover
        self.mutations = mutations

    def copy(self, thread: int) -> "GeneticAlgorithm":
        """Create a copy of the GeneticAlgorithm instance.

        Args:
            thread (int): The thread ID for the copied instance.

        Returns:
            GeneticAlgorithm: A new instance of GeneticAlgorithm.
        """
        return GeneticAlgorithm(
            thread,
            self.stop_criteria.copy(),
            self.evaluator,
            self.mutations.copy(thread),
            self.construction.copy(thread),
            self.selection.copy(thread),
            self.crossover.copy(thread),
            self.acceptance_criteria.copy(),
        )

    def run(self, population: Pool) -> Pool:
        """Run the genetic algorithm on a population of solutions.

        Args:
            population (Pool): The initial population of solutions.

        Returns:
            Pool: The final population after evolution.
        """
        if not population:
            raise Exception(
                "GeneticAlgorithm assumes the population will be filled with empty solutions at the start."
            )

        curr_pop = ListPool()
        generation = 0

        # Construct the initial population using the construction heuristic
        for sol in population:
            curr_pop.add(self.construction.run_operation(sol, self), self.evaluator)

        new_pop = ListPool()
        evaluations = []

        self.stop_criteria.reset()

        while not self.stop():
            generation += 1
            self.stop_criteria.increment_counter()
            evaluations.clear()

            # Evaluate the current population
            for sol in curr_pop:
                evaluations.append(self.evaluator.evaluate(sol))

            # Check stopping condition based on evaluations
            if self.stop_on_evaluations(evaluations):
                break

            # Generate new population using selection, crossover, and mutation
            while new_pop.count() < curr_pop.count():
                selection1 = self.selection.run(curr_pop)
                selection2 = self.selection.run(curr_pop)
                new_sol = self.crossover.cross_operation(selection1, selection2)
                new_pop.add(new_sol, self.evaluator)

            # Mutate the new population and update the current population
            curr_pop.clear()
            for sol in new_pop:
                curr_pop.add(self.mutations.run_operation(sol), self.evaluator)

        return curr_pop
