import os
import sys
from datetime import datetime
from typing import Optional

from oahf.Base import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.Commons.ProblemData import ProblemData
from oahf.ImplementedBase.AlwabpEvaluator import AlwabpEvaluator
from oahf.ImplementedBase.MaxCycleTimeConstraint import MaxCycleTimeConstraint
from oahf.MetaHeuristicsParser.HeuristicParser import HeuristicParser
from oahf.Utils import Util


def main(args=sys.argv[1:]) -> None:

    if len(args) == 0:
        Util.logger().info("Missing configuration file path. Ending program.")
        return

    problem_data = ProblemData(args[0])
    Util.set_optimization_start_time(datetime.now())
    Util.set_input_name(problem_data.file_name)
    Util.set_default_output_path(problem_data.output_path)

    Util.logger().info(
        "Welcome to the Open Algorithm and Heuristic Framework (OAHF). "
        f"Initializing the system and preparing the environment."
    )

    print(Util.line())
    Util.logger().info(f"Optimizing instance {problem_data.file_name}.")
    print(Util.line())

    heuristic_parser = HeuristicParser()
    evaluator = heuristic_parser.parse_file(problem_data.heuristic_definition_file)
    original_solution: Optional[Solution] = Util.read_input(problem_data)

    if evaluator and original_solution:
        solution = original_solution.copy()
        ThreadManager.initialize(1, problem_data.random_seed)
        final_solution = heuristic_parser.run_definition(solution, evaluator)

        heuristic_parser.write_pools()

        if final_solution:
            final_solution.write_json()
            print(final_solution)


def create_init_files(root_dir):
    # Define the target directory to search for subdirectories
    target_dir = os.path.join(root_dir, "oahf")

    for dirpath, dirnames, filenames in os.walk(target_dir):
        # Skip the target directory itself
        if dirpath == target_dir:
            continue

        py_files = [f for f in filenames if f.endswith(".py") and f != "__init__.py"]

        # If there are Python files in the folder
        if py_files:
            init_path = os.path.join(dirpath, "__init__.py")
            # Create or open the __init__.py file
            with open(init_path, "w") as init_file:
                # Generate imports based on Python files in the folder
                module_names = [os.path.splitext(f)[0] for f in py_files]
                imports = [f"from .{module} import {module}" for module in module_names]
                init_file.write("\n".join(imports) + "\n")

                # Write the __all__ list with module names
                init_file.write("\n__all__ = [\n")
                all_list = ",\n".join([f'    "{module}"' for module in module_names])
                init_file.write(all_list + "\n]\n")

            # print(f"Created and updated: {init_path}")
        else:
            # Create __init__.py if no Python files exist
            init_path = os.path.join(dirpath, "__init__.py")
            if not os.path.exists(init_path):
                open(init_path, "w").close()
                # print(f"Created: {init_path}")


if __name__ == "__main__":
    project_root = "."  # Root directory of the project
    create_init_files(project_root)
    main()
