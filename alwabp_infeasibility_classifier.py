import os
from pathlib import Path

# Configuration: thresholds for infeasibility percentages
THRESHOLD_10 = 10.0
THRESHOLD_20 = 20.0


def classify_instance(file_path):
    """
    Reads an ALWABP instance file and computes the percentage of infeasible entries ('Inf')
    Returns a tuple: (percentage_infeasible: float, category: str)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        # Read number of tasks
        first_line = f.readline().strip()
        try:
            num_tasks = int(first_line)
        except ValueError:
            raise ValueError(f"Invalid number of tasks in file: {file_path}")

        # Read task-time lines
        total_entries = 0
        infeasible_count = 0
        for _ in range(num_tasks):
            line = f.readline().strip()
            if not line:
                break
            tokens = line.split()
            total_entries += len(tokens)
            infeasible_count += sum(1 for t in tokens if t.lower() == 'inf')

    if total_entries == 0:
        percentage = 0.0
    else:
        percentage = (infeasible_count / total_entries) * 100

    # Classify based on thresholds
    if percentage <= THRESHOLD_10:
        category = 'up to 10%'
    elif percentage <= THRESHOLD_20:
        category = 'up to 20%'
    else:
        category = 'above 20%'
        print(f"Instance {file_path} is above 20% with {percentage}")

    return percentage, category


def scan_and_classify_instances(root_dir):
    """
    Scans the given directory (non-recursively), processes all files,
    and collects instances into two lists based on infeasibility.
    """
    root = Path(root_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"Provided path is not a directory: {root_dir}")

    up_to_10 = []
    up_to_20 = []

    for file_path in root.iterdir():
        if file_path.is_file():
            try:
                percentage, category = classify_instance(file_path)
                # Append file names to corresponding lists
                if percentage <= THRESHOLD_10:
                    up_to_10.append(file_path.name)
                #elif percentage <= THRESHOLD_20:
                else: # This will add all instances that are above 20% as the 20% threshold
                    up_to_20.append(file_path.name)
                # Instances above 20% are ignored in this output
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

    # Print the two lists in Python syntax
    print(f"10: {up_to_10}")
    print(f"20: {up_to_20}")


if __name__ == '__main__':
    # Replace the path below with your instances directory
    instances_dir = r"C:\Projetos\OAHF\Instances\alwabp"
    scan_and_classify_instances(instances_dir)
