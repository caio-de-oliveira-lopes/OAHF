import os

from oahf.Base import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.AlwabpWorkerOrientedInsertNS import AlwabpWorkerOrientedInsertNS
from oahf.ImplementedBase.CompleteAssignmentStopCriteria import CompleteAssignmentStopCriteria
from oahf.ImplementedBase.MaxCycleTimeConstraint import MaxCycleTimeConstraint
from oahf.ImplementedBase.AlwabpEvaluator import AlwabpEvaluator
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation, MaxPositionalWeightType
from oahf.ImplementedBase.BetterOrSameAcceptanceCriteria import BetterOrSameAcceptanceCriteria
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.StopTimeIterationCriteria import StopTimeIterationCriteria
from oahf.ImplementedBase.StopNoImprovement import StopNoImprovement
from oahf.ImplementedBase.WorkersUnassignedStopCriteria import WorkersUnassignedStopCriteria
from oahf.ImplementedBase.AlwaysAcceptAcceptanceCriteria import AlwaysAcceptAcceptanceCriteria
from oahf.ImplementedBase.ExecutedByAvailableWorkersAcceptanceCriteria import ExecutedByAvailableWorkersAcceptanceCriteria

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
    original_solution: Optional[Solution] = Util.read_input(input_file, input_type)
    
    if not original_solution or not isinstance(original_solution, AlwabpSolution): return None
    
    solution = original_solution.copy()
    random_seed = 1
    thread = 0
    ThreadManager.initialize(1, random_seed)     
    positional_weight_types = list(EnumUtil.get_values(MaxPositionalWeightType))
    ns_greediness = 0
    grc_greedness = 1
    graph_orientation = GraphOrientation.FORWARD    
    
    pw = positional_weight_types[thread - 1]
    if not isinstance(pw, MaxPositionalWeightType): return None
        
    evaluator = AlwabpEvaluator(True, MaxCycleTimeConstraint())
    acceptance_criteria = BetterOrSameAcceptanceCriteria()
        
    cycle_time_limit = Util.get_recommeded_maximum_mean_cycle_time(cycle_time_path, file_name)
    solution.cycle_time_limit = cycle_time_limit
        
    # Must add UB calculation and use it as stop criteria too (to avoid infinite loop)
    # 500 is defined in the article as "obtained through an increase of the best results obtained in the literature"
    while not len(solution.unassigned_workers) == 0 or cycle_time_limit >= 500:
        stop_criteria = WorkersUnassignedStopCriteria(1)
        ns = ListSelection(False, AlwabpWorkerOrientedInsertNS(pw, graph_orientation, ns_greediness, None))
            
        grc = GRC(thread, grc_greedness, stop_criteria, evaluator, acceptance_criteria, ns, order_moves=False)
        new_solution = grc.run(solution)
        
        if isinstance(new_solution, AlwabpSolution):
            if new_solution == solution or len(new_solution.unassigned_tasks) > 0:
                cycle_time_limit += 1
                original_solution.cycle_time_limit = cycle_time_limit
                solution = original_solution.copy()
                print(f'Increase cycle time to {str(cycle_time_limit)}')
            else:
                solution = new_solution
            
    print(solution)


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
