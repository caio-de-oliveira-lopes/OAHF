import os

from oahf.Base import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.MaxCycleTimeConstraint import MaxCycleTimeConstraint
from oahf.ImplementedBase.AlwabpEvaluator import AlwabpEvaluator
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, MaxPositionalWeightType
from oahf.ImplementedBase.AlwabpInsertOrderNS import AlwabpInsertOrderNS
from oahf.ImplementedBase.BetterOrSameAcceptanceCriteria import BetterOrSameAcceptanceCriteria
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.MetaHeuristics.GRC import GRC
from oahf.Utils import EnumUtil, Util
from typing import Optional, Type
from pathlib import Path


def main():
    input_path = Path(r'C:\Projetos\OAHF\Instances\alwabp')
    file_name = '1_hes'
    input_file = input_path.joinpath(file_name)
    cycle_time_path = Path(fr'C:\Projetos\OAHF\Parameters\recommeded_maximum_mean_cycle_time.json')
    
    input_type = Type[AlwabpSolution]
    solution: Optional[Solution] = Util.read_input(input_file, input_type)
    
    if not solution or not isinstance(solution, AlwabpSolution): return None
    
    random_seed = 1
    num_threads = 1
    ThreadManager.initialize(num_threads, random_seed)     
    positional_weight_types = list(EnumUtil.get_values(MaxPositionalWeightType))
    greediness = 0
    
    for thread in range(num_threads):
        pw = positional_weight_types[thread]
        if not isinstance(pw, MaxPositionalWeightType): continue
        
        stop_criteria = StopTimeIterationCriteria(iterations = len(solution.tasks))
        evaluator = AlwabpEvaluator(True, MaxCycleTimeConstraint())
        acceptance_criteria = BetterOrSameAcceptanceCriteria()
        
        solution.cycle_time_limit = Util.get_recommeded_maximum_mean_cycle_time(cycle_time_path, file_name) - 1
        
        for station in solution.stations:
            ns = ListSelection(False, AlwabpInsertOrderNS(pw, station, greediness, stop_criteria))
            constructed_solution1: Optional[Solution] = None
            
            while not constructed_solution1:
                solution.cycle_time_limit += 1
                grc = GRC(thread, greediness, stop_criteria, evaluator, acceptance_criteria, ns)
                constructed_solution1 = grc.run(solution)
                
            constructed_solution2: Optional[Solution] = None
            if constructed_solution2:
                while not constructed_solution2:
                

            
        print(constructed_solution1)


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

            print(f"Created and updated: {init_path}")
        else:
            # Create __init__.py if no Python files exist
            init_path = os.path.join(dirpath, "__init__.py")
            if not os.path.exists(init_path):
                open(init_path, "w").close()
                print(f"Created: {init_path}")


if __name__ == "__main__":
    project_root = "."  # Root directory of the project
    create_init_files(project_root)
    main()
