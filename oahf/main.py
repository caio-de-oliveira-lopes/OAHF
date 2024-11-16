import os
from datetime import datetime
from typing import Optional

from oahf.Base import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.Commons.ProblemData import ProblemData
from oahf.ImplementedBase.AlwabpEvaluator import AlwabpEvaluator
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution
from oahf.ImplementedBase.MaxCycleTimeConstraint import MaxCycleTimeConstraint
from oahf.MetaHeuristicsParser.HeuristicParser import HeuristicParser
from oahf.Utils import Util


def main():
    problem_data = ProblemData("C:\\Projetos\\OAHF\\Parameters\\oahf_parameters.json")
    Util.set_optimization_start_time(datetime.now())
    Util.set_input_name(problem_data.file_name)

    Util.logger().info(
        "Welcome to the Open Algorithm and Heuristic Framework (OAHF). "
        "Initializing the system and preparing the environment."
    )

    heuristic_parser = HeuristicParser()
    evaluator = AlwabpEvaluator(True, MaxCycleTimeConstraint())
    heuristic_parser.parse_file(problem_data.heuristic_definition_file, evaluator)
    original_solution: Optional[Solution] = Util.read_input(problem_data.input_file, problem_data.input_type)  # type: ignore

    if not original_solution or not isinstance(original_solution, AlwabpSolution):
        return None

    solution = original_solution.copy()
    ThreadManager.initialize(1, problem_data.random_seed)

    solution.cycle_time_limit = Util.get_recommeded_maximum_mean_cycle_time(
        problem_data.cycle_time_path, problem_data.file_name
    )

    print(
        f"Starting instance {problem_data.file_name} with cycle time = {str(solution.cycle_time_limit)}"
    )

    print(heuristic_parser.run_definition(solution, evaluator))


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
