# target_runner.py
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union


def modify_heuristic_iterations(
    iterations_value: int, intensification_value: Optional[int], heuristic_file: Union[str, Path], heuristic_id: int
):
    # Create a copy of the heuristic file for modification
    new_file = str(heuristic_file).replace(".json", "_modified.json")
    shutil.copyfile(heuristic_file, new_file)
    # Load the heuristic configuration
    with open(new_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    # Update the metaheuristic with id equal to heuristic_id: set its "iterations" parameter
    found = False
    for heuristic in config.get("metaheuristics", []):
        if heuristic.get("id") == heuristic_id:
            # Update iterations candidate value
            heuristic["parameters"]["iterations"] = iterations_value
            found = True
            if intensification_value is not None:
                heuristic["parameters"]["intensification_criteria"]["time_iteration"]["iterations"] = intensification_value
            break
    if not found:
        print(f"Metaheuristic id {heuristic_id} not found!")
    # Save the modified configuration
    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    return new_file


def update_instance_in_parameters(
    params_file: Union[str, Path], candidate_instance: str
):
    # Load the parameter file copy
    with open(params_file, "r", encoding="utf-8") as pf:
        params = json.load(pf)
    # Update the "file_name" key with the candidate instance provided by irace
    params["file_name"] = candidate_instance.split('/')[-1]
    # Save the updated parameters file
    with open(params_file, "w", encoding="utf-8") as pf:
        json.dump(params, pf, indent=4)
    return candidate_instance


def get_latest_output_dir(base_output_path: str, instance_name: str):
    # Construct the output directory path using output_path and file_name
    output_dir = Path(base_output_path) / instance_name
    # Retrieve subdirectories inside the output directory
    subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
    if not subdirs:
        raise FileNotFoundError(f"No output subdirectories found in {output_dir}")
    # Select the subdirectory with the most recent modification time
    latest_dir = max(subdirs, key=lambda d: d.stat().st_mtime)
    return latest_dir


def extract_objective_from_output(output_dir: Path) -> float:
    # Look for the JSON output file with the expected pattern
    json_files = list(output_dir.glob("output_solution*.json"))
    if not json_files:
        raise FileNotFoundError(
            f"No output JSON file found in {output_dir} with expected pattern"
        )
    output_file = json_files[0]
    with open(output_file, "r", encoding="utf-8") as f:
        output_data = json.load(f)
    # Extract the primary objective value from the key "total_distinct_tasks"
    objective_value = output_data.get("max_cycle_time")
    if objective_value is None:
        raise KeyError(f"'max_cycle_time' key not found in {output_file}")
    return float(objective_value)


def run_target_tabu():
    """
    // Uses the candidate values passed via command-line to modify the heuristic file
    // and update the instance selection in the parameters file, then calls main.py and
    // reads the objective value for irace.
    """
    # Expect two candidate values: one for iterations and one for instance
    candidate_iterations = sys.argv[6]  # e.g., "3000"
    candidate_intensification = sys.argv[8]
    candidate_instance = sys.argv[4]  # e.g., "instance2.json"
    heuristic_id = 97  # Candidate heuristic id for modification

    # Define the path to the original heuristic file
    heuristic_file = "C:/Projetos/OAHF/Parameters/heuristic_definition_tabu.json"

    # Update the heuristic file with the candidate iterations value
    modified_heuristic = modify_heuristic_iterations(
        int(candidate_iterations), int(candidate_intensification), heuristic_file, heuristic_id
    )
    #print("Modified heuristic file:", modified_heuristic)

    # Update the parameter file to change the 'file_name' field based on the candidate instance
    params_file = "C:/Projetos/OAHF/Parameters/oahf_parameters_copy.json"
    updated_instance = update_instance_in_parameters(params_file, candidate_instance)
    #print("Updated instance in parameters file:", updated_instance)

    import subprocess

    command = [
        r"C:\Users\caio.lopes\AppData\Local\miniconda3\Scripts\conda.exe",
        "run", "--no-capture-output",
        "-n", "irace_oahf", "python", "-u",
        r"C:\Projetos\OAHF\oahf\main.py",
        params_file
    ]

    subprocess.run(
        command,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        check=True
    )
    # Read the parameter file to obtain the output_path and file_name
    with open(params_file, "r", encoding="utf-8") as pf:
        params = json.load(pf)
    output_path = params.get("output_path")
    instance_name = params.get("file_name")
    if not output_path or not instance_name:
        print("Output path or instance name not found in parameters file.")
        sys.exit(1)

    # Get the latest output directory using the output_path and instance name
    latest_output_dir = get_latest_output_dir(output_path, instance_name)
    #print("Latest output directory:", latest_output_dir)
    
    # Extract the objective value from the output file in the latest directory
    objective_value = extract_objective_from_output(latest_output_dir)
    #print("Objective value:", objective_value)
    print(objective_value)

    return objective_value

def modify_hga(
    seconds: int, population_size: int, elite_fraction: float, mutant_fraction: float, bias: float, heuristic_file: str, heuristic_id: int
):
    # Create a copy of the heuristic file for modification
    new_file = str(heuristic_file).replace(".json", "_modified.json")
    shutil.copyfile(heuristic_file, new_file)
    # Load the heuristic configuration
    with open(new_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    # Update the metaheuristic with id equal to heuristic_id: set its "iterations" parameter
    found = False
    for heuristic in config.get("metaheuristics", []):
        if heuristic.get("id") == heuristic_id:
            # Update iterations candidate value
            heuristic["stop_criteria"]["time_iteration"]["seconds"] = int(seconds)
            heuristic["parameters"]["population_size"] = float(population_size)
            heuristic["parameters"]["elite_fraction"] = float(elite_fraction)
            heuristic["parameters"]["mutant_fraction"] = float(mutant_fraction)
            heuristic["parameters"]["bias"] = float(bias)
            found = True
            break
    if not found:
        print(f"Metaheuristic id {heuristic_id} not found!")
    # Save the modified configuration
    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    return new_file


def run_target_hga():
    """
    // Uses the candidate values passed via command-line to modify the heuristic file
    // and update the instance selection in the parameters file, then calls main.py and
    // reads the objective value for irace.
    """
    # Expect two candidate values: one for iterations and one for instance   
    instance = sys.argv[4]
    seconds = sys.argv[6]
    population_size = sys.argv[8]
    elite_fraction = sys.argv[10]
    mutant_fraction = sys.argv[12]
    bias = sys.argv[14]
    heuristic_id = 99  # Candidate heuristic id for modification

    # Define the path to the original heuristic file
    heuristic_file = "C:/Projetos/OAHF/Parameters/heuristic_definition_hga.json"

    # Update the heuristic file with the candidate iterations value
    modified_heuristic = modify_hga(
        int(seconds), population_size, elite_fraction, mutant_fraction, bias, heuristic_file, heuristic_id
    )
    #print("Modified heuristic file:", modified_heuristic)

    # Update the parameter file to change the 'file_name' field based on the candidate instance
    params_file = "C:/Projetos/OAHF/Parameters/oahf_parameters_hga_tunning.json"
    updated_instance = update_instance_in_parameters(params_file, instance)
    #print("Updated instance in parameters file:", updated_instance)

    import subprocess

    command = [
        r"C:\Users\caio.lopes\AppData\Local\miniconda3\Scripts\conda.exe",
        "run", "--no-capture-output",
        "-n", "irace_oahf", "python", "-u",
        r"C:\Projetos\OAHF\oahf\main.py",
        params_file
    ]

    subprocess.run(
        command,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        check=True
    )
    # Read the parameter file to obtain the output_path and file_name
    with open(params_file, "r", encoding="utf-8") as pf:
        params = json.load(pf)
    output_path = params.get("output_path")
    instance_name = params.get("file_name")
    if not output_path or not instance_name:
        print("Output path or instance name not found in parameters file.")
        sys.exit(1)

    # Get the latest output directory using the output_path and instance name
    latest_output_dir = get_latest_output_dir(output_path, instance_name)
    #print("Latest output directory:", latest_output_dir)
    
    # Extract the objective value from the output file in the latest directory
    objective_value = extract_objective_from_output(latest_output_dir)
    #print("Objective value:", objective_value)
    print(objective_value)

    return objective_value


if __name__ == "__main__":
    #run_target_tabu()
    run_target_hga()
