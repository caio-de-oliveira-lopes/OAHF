# target_runner.py
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Union


def modify_heuristic_iterations(
    iterations_value: int, heuristic_file: Union[str, Path], heuristic_id: int
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
    params["file_name"] = candidate_instance
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
    json_files = list(output_dir.glob("*output_job_rotation_alwabp*.json"))
    if not json_files:
        raise FileNotFoundError(
            f"No output JSON file found in {output_dir} with expected pattern"
        )
    output_file = json_files[0]
    with open(output_file, "r", encoding="utf-8") as f:
        output_data = json.load(f)
    # Extract the primary objective value from the key "total_distinct_tasks"
    objective_value = output_data.get("total_distinct_tasks")
    if objective_value is None:
        raise KeyError(f"'total_distinct_tasks' key not found in {output_file}")
    return float(objective_value)


def run_target_tabu():
    """
    // Uses the candidate values passed via command-line to modify the heuristic file
    // and update the instance selection in the parameters file, then calls main.py and
    // reads the objective value for irace.
    """
    # Expect two candidate values: one for iterations and one for instance
    if len(sys.argv) < 3:
        print("Error: Candidate values for iterations and instance not provided.")
        sys.exit(1)
    candidate_iterations = sys.argv[1]  # e.g., "3000"
    candidate_instance = sys.argv[2]  # e.g., "instance2.json"
    heuristic_id = 97  # Candidate heuristic id for modification

    # Define the path to the original heuristic file
    heuristic_file = "C:/Projetos/OAHF/Parameters/heuristic_definition_v3.json"

    # Update the heuristic file with the candidate iterations value
    modified_heuristic = modify_heuristic_iterations(
        int(candidate_iterations), heuristic_file, heuristic_id
    )
    print("Modified heuristic file:", modified_heuristic)

    # Update the parameter file to change the 'file_name' field based on the candidate instance
    params_file = "C:/Projetos/OAHF/Parameters/oahf_parameters_copy.json"
    updated_instance = update_instance_in_parameters(params_file, candidate_instance)
    print("Updated instance in parameters file:", updated_instance)

    # Run main.py with the updated parameters file
    subprocess.run(["python", "main.py", params_file], check=True)

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
    print("Latest output directory:", latest_output_dir)

    # Extract the objective value from the output file in the latest directory
    objective_value = extract_objective_from_output(latest_output_dir)
    print("Objective value:", objective_value)

    # Since the goal is to maximize the number of different tasks executed, we return the negative value
    return -objective_value


if __name__ == "__main__":
    run_target_tabu()
