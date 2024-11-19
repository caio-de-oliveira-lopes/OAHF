import json
from pathlib import Path
from typing import Type, Union

# Must import solution types here in order for globals() to work
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution


class ProblemData:
    def __init__(self, json_path: Union[str, Path]):
        """
        Initializes the ProblemData object by reading the JSON file.

        Args:
            json_path (str): Path to the JSON file containing problem parameters.
        """

        # Read and load the JSON data
        with open(json_path, "r") as file:
            data = json.load(file)

        # Assign each value to the corresponding class attribute
        self.file_name = data["file_name"]
        self.input_path = Path(data["input_path"])
        self.input_file = self.input_path.joinpath(self.file_name)
        self.output_path = Path(data["output_path"])
        self.cycle_time_path = Path(data["cycle_time_path"])
        self.heuristic_definition_file = Path(data["heuristic_definition_file"])
        self.input_type = Type[eval(data["input_type"])]
        self.random_seed = data["random_seed"]

    def __str__(self):
        """Provide a string representation of the ProblemData object."""
        return (
            f"ProblemData(file_name={self.file_name}, input_path={self.input_path}, "
            f"cycle_time_path={self.cycle_time_path}, heuristic_definition_file={self.heuristic_definition_file}, "
            f"input_type={self.input_type}, random_seed={self.random_seed})"
        )
