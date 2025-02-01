from oahf.Base.Entity import Entity


class LpExecutionData(Entity):
    def __init__(
        self,
        simplex_iterations: float,
        nodes_explored: float,
        optimality_gap: float,
        solve_seconds: float,
    ):
        """
        Initializes the LpExecutionData object with solver statistics.

        Args:
            simplex_iterations (float): Number of simplex iterations performed.
            nodes_explored (float): Number of branch-and-bound nodes explored.
            optimality_gap (float): Optimality gap of the solution.
            solve_seconds (float): Time taken to solve the problem.
        """
        super().__init__()  # Call the constructor of the Entity class
        self.name = "LpExecutionData"
        self.simplex_iterations = simplex_iterations
        self.nodes_explored = nodes_explored
        self.optimality_gap = optimality_gap
        self.solve_seconds = solve_seconds

    def __str__(self) -> str:
        """Gets a string representation of the PulpExecutionData object."""

        from oahf.Utils.Util import Util

        result = [Util.line()]
        result.append(f"{self.name} - Solver Statistics:")
        result.append(f"ID: {self.id}")
        result.append(f"Simplex Iterations: {self.simplex_iterations}")
        result.append(f"Nodes Explored: {self.nodes_explored}")
        result.append(f"Optimality Gap: {self.optimality_gap:.4f}")
        result.append(f"Solution Time: {self.solve_seconds:.2f} seconds")
        result.append(Util.line())

        return "\n".join(result)

    def to_dict(self) -> dict:
        """
        Converts the LpExecutionData object into a dictionary.

        Returns:
            dict: A dictionary representation of the solver statistics.
        """
        pulp_execution_dict = super().to_dict()

        pulp_execution_dict.update(
            {
                "simplex_iterations": self.simplex_iterations,
                "nodes_explored": self.nodes_explored,
                "optimality_gap": self.optimality_gap,
                "solve_seconds": self.solve_seconds,
            }
        )

        return pulp_execution_dict

    @classmethod
    def from_dict(cls, data: dict) -> "LpExecutionData":
        """
        Reconstructs an LpExecutionData instance from a dictionary.

        Args:
            data (dict): A dictionary containing solver statistics.

        Returns:
            LpExecutionData: A reconstructed instance of LpExecutionData.
        """
        return cls(
            simplex_iterations=data.get("simplex_iterations", 0.0),
            nodes_explored=data.get("nodes_explored", 0.0),
            optimality_gap=data.get("optimality_gap", 0.0),
            solve_seconds=data.get("solve_seconds", 0.0),
        )
