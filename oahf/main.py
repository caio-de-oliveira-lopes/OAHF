import os

from oahf.Base import Solution
from oahf.Base.ThreadManager import ThreadManager
from oahf.ImplementedBase.AlwabpWorkerInsertOrderNS import AlwabpWorkerInsertOrderNS
from oahf.ImplementedBase.CompleteAssignmentStopCriteria import CompleteAssignmentStopCriteria
from oahf.ImplementedBase.MaxCycleTimeConstraint import MaxCycleTimeConstraint
from oahf.ImplementedBase.AlwabpEvaluator import AlwabpEvaluator
from oahf.ImplementedBase.AlwabpSolution import AlwabpSolution, GraphOrientation, MaxPositionalWeightType
from oahf.ImplementedBase.AlwabpTaskInsertOrderNS import AlwabpTaskInsertOrderNS
from oahf.ImplementedBase.BetterOrSameAcceptanceCriteria import BetterOrSameAcceptanceCriteria
from oahf.ImplementedBase.ListSelection import ListSelection
from oahf.ImplementedBase.MultipleStopCriteria import MultipleStopCriteria
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
    task_greediness = 0
    worker_greediness = 0
    graph_orientation = GraphOrientation.FORWARD
    
    
    pw = positional_weight_types[thread - 1]
    if not isinstance(pw, MaxPositionalWeightType): return None
        
    evaluator = AlwabpEvaluator(True, MaxCycleTimeConstraint())
    task_acceptance_criteria = ExecutedByAvailableWorkersAcceptanceCriteria()
    worker_acceptance_criteria = BetterOrSameAcceptanceCriteria()
        
    cycle_time_limit = Util.get_recommeded_maximum_mean_cycle_time(cycle_time_path, file_name)
    solution.cycle_time_limit = cycle_time_limit
        
    # Must add UB calculation and use it as stop criteria too (to avoid infinite loop)
    while not len(solution.unassigned_workers) == 0:
        for station in solution.get_open_stations():
            task_stop_criteria = StopNoImprovement(len(solution.unassigned_tasks))
            worker_stop_criteria = WorkersUnassignedStopCriteria(len(solution.unassigned_workers))
            task_ns = ListSelection(False, AlwabpTaskInsertOrderNS(pw, graph_orientation, station, True, task_greediness, None))
            worker_ns = ListSelection(False, AlwabpWorkerInsertOrderNS(station, True, task_greediness, None))
            worker_assignment_solution: Optional[Solution] = None
            
            grc_task = GRC(thread, task_greediness, task_stop_criteria, evaluator, task_acceptance_criteria, task_ns, order_moves=True)
            task_assignment_solution = grc_task.run(solution)
            
            if task_assignment_solution == solution or (isinstance(task_assignment_solution, AlwabpSolution) and station == len(task_assignment_solution.stations) and len(task_assignment_solution.unassigned_tasks) > 0):
                cycle_time_limit += 1
                original_solution.cycle_time_limit = cycle_time_limit
                solution = original_solution
                print(f'Increase cycle time to {str(cycle_time_limit)}')
                break
            
            while not worker_assignment_solution:
                grc_worker = GRC(thread, worker_greediness, worker_stop_criteria, evaluator, worker_acceptance_criteria, worker_ns, order_moves=False)
                worker_assignment_solution = grc_worker.run(task_assignment_solution)
                
            if task_assignment_solution == worker_assignment_solution:  
                cycle_time_limit += 1
                original_solution.cycle_time_limit = cycle_time_limit
                solution = original_solution
                print(f'Increase cycle time to {str(cycle_time_limit)}')
                break
            
            if isinstance(worker_assignment_solution, AlwabpSolution):
                solution = worker_assignment_solution
            
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
