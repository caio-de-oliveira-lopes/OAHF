# target_runner.py
import json
import os
import shutil
import subprocess
import sys


def modify_heuristic(iterations_value, heuristic_file):
    # Create a copy of the heuristic file for modification
    new_file = heuristic_file.replace(".json", "_modified.json")
    shutil.copyfile(heuristic_file, new_file)
    # Load the heuristic configuration
    with open(new_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    # Update the metaheuristic with id 99: set its "iterations" parameter
    found = False
    for heuristic in config.get("metaheuristics", []):
        if heuristic.get("id") == 99:
            # Update iterations candidate value
            heuristic["parameters"]["iterations"] = int(iterations_value)
            found = True
            break
    if not found:
        print("Metaheuristic id 99 not found!")
    # Save the modified configuration
    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    return new_file


def run_target():
    """
    // Uses the candidate value passed via command-line to modify the heuristic file,
    // then calls main.py with the updated parameters.
    """
    # The candidate value for iterations is passed by irace as an argument
    if len(sys.argv) < 2:
        print("Error: Candidate value not provided.")
        sys.exit(1)
    candidate_value = sys.argv[1]  # e.g., "3000"

    # Define the path to the original heuristic file
    heuristic_file = "C:/Projetos/OAHF/Parameters/heuristic_definition_v3.json"

    # Update the heuristic file with the candidate value
    modified_heuristic = modify_heuristic(candidate_value, heuristic_file)
    print("Modified heuristic file:", modified_heuristic)

    subprocess.run(
        ["python", "main.py", "C:/Projetos/OAHF/Parameters/oahf_parameters_copy.json"],
        check=True,
    )

    with open("output.txt", "r") as f:
        result_value = f.read().strip()
    print(result_value)


if __name__ == "__main__":
    run_target()
