from pathlib import Path
from typing import List
import subprocess
import os
import json
import secrets

def run_tests(seeds: List[int]):
    # Define paths
    instances_dir = Path("/home/caio/OAHF/Instances/alwabp")
    parameters_path = Path("/home/caio/OAHF/Parameters/oahf_parameters.json")
    modified_path = Path("/home/caio/OAHF/Parameters/oahf_parameters_modified.json")
    heuristic_definition_files = [
        Path("/home/caio/OAHF/Parameters/heuristic_definition_hajr.json"),
        Path("/home/caio/OAHF/Parameters/heuristic_definition_iterative_hajr.json")
    ]
    optimization_output_paths = [
        Path("/home/caio/OAHF/Outputs/HAJR"),
        Path("/home/caio/OAHF/Outputs/Iterative_HAJR")
    ]

    # Load the original JSON once
    with open(parameters_path, "r", encoding="utf-8") as f:
        parameters = json.load(f)

    # Iterate over all entries in the instances directory
    for entry in os.listdir(instances_dir):
        entry_path = os.path.join(instances_dir, entry)

        # Skip anything that is not a file
        if not os.path.isfile(entry_path):
            continue

        # Extract just the filename (including extension)
        filename = os.path.basename(entry_path)

        # Update the "file_name" key in the parameters dict
        parameters["file_name"] = filename

        print("------------------------------------------------------------------------")

        for seed in seeds:
            # Updating random seed
            parameters["random_seed"] = seed

            for algorithm in range(2):
                # Updating according to the algorithms, 0 being 2013 HAJR and 1 being the Iterative HAJR (new proposal)
                parameters["output_path"] = str(optimization_output_paths[algorithm])
                parameters["heuristic_definition_file"] = str(heuristic_definition_files[algorithm])

                # Write out the modified JSON to the new file
                with open(modified_path, "w", encoding="utf-8") as out_f:
                    json.dump(parameters, out_f, ensure_ascii=False, indent=4)

                print(f"Instance: {filename} || Seed: {seed} || Heuristic: {heuristic_definition_files[algorithm]}.")
                # CALL THE MAIN FILE TO INITIALIZE THE OPTIMIZATION
                command = [
                    "/home/caio/miniconda3/condabin/conda",
                    "run", "--no-capture-output",
                    "-n", "oahf", "python", "-u",
                    r"C:\Projetos\OAHF\oahf\main.py",
                    modified_path
                ]

                subprocess.run(
                    command,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    check=True
                )
                print("Step finished.")
                print("------------------------------------------------------------------------")

def generate_seeds(seed_path: Path, num_seeds: int, seed_size_bytes: int):
    # If the output file already exists, do nothing and exit
    if os.path.exists(seed_path):
        print(f"'{seed_path}' already exists. No new seeds were generated.")
    else:
        # Open the file in write mode (this will overwrite any existing content)
        with open(seed_path, "w") as f:
            for _ in range(num_seeds):
                # secrets.token_hex(n) returns a hex string of length 2*n,
                # where n is the number of random bytes
                hex_seed = secrets.token_hex(seed_size_bytes)
                f.write(hex_seed + "\n")

        print(f"Generated {num_seeds} seeds, each {seed_size_bytes} bytes long, in '{seed_path}'.")

def read_seeds(seed_path: Path) -> List[int]:
    """
    Reads hexadecimal seeds from 'seeds.txt' (one per line) and returns them as a list of integers.
    
    Raises:
        FileNotFoundError: If 'seeds.txt' does not exist.
        ValueError: If any line in the file is not a valid hexadecimal string.
    """
    
    if not os.path.exists(seed_path):
        raise FileNotFoundError(f"'{seed_path}' does not exist.")
    
    seeds: List[int] = []
    with open(seed_path, "r") as f:
        for line in f:
            hex_str = line.strip()
            if not hex_str:
                continue  # skip empty lines (if any)
            # Convert hex string to integer; raises ValueError on invalid hex
            seed_int = int(hex_str, 16)
            seeds.append(seed_int)
    
    return seeds

if __name__ == "__main__":
    seed_path = Path("/home/caio/OAHF/Parameters/seeds.txt")
    generate_seeds(seed_path, 3, 16)
    seeds = read_seeds(seed_path)

    run_tests(seeds)