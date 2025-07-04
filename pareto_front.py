import json
import matplotlib.pyplot as plt

def load_solutions(file_path):
    """Load solutions from a JSON file and extract objectives."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return [(sol["total_distinct_tasks"], sol["average_cycle_time"]) for sol in data["solutions"]]

def dominates(a, b):
    """
    Check if solution a dominates solution b.
    Objective 1: maximize a[0], Objective 2: minimize a[1].
    """
    return (a[0] >= b[0] and a[1] <= b[1]) and (a[0] > b[0] or a[1] < b[1])

def pareto_front(points):
    """Compute the Pareto front for a list of points."""
    front = []
    for p in points:
        if not any(dominates(other, p) for other in points if other != p):
            front.append(p)
    return sorted(front, key=lambda x: x[0])

# Dictionary mapping dataset names to file paths
datasets = {
    "Wee_80_s1": "C:\Projetos\Outputs\Iterative_HAJR\seed_144911535910197828289965286135314374916\80_wee\output_06-19-2025_20h-30m-05s\output_list_pool_1.json",
    "Wee_80_s2": "C:\Projetos\Outputs\Iterative_HAJR\seed_294165949277890002569088467705991431954\80_wee\output_06-19-2025_19h-54m-39s\output_list_pool_1.json",
    "Wee_80_s3": "C:\Projetos\Outputs\Iterative_HAJR\seed_34707186982903718312397416735273231795\80_wee\output_06-19-2025_21h-05m-13s\output_list_pool_1.json"
}

plt.figure(figsize=(10, 7))

for name, path in datasets.items():
    # Load and process each dataset
    points = load_solutions(path)
    pareto = pareto_front(points)
    all_x, all_y = zip(*points)
    pf_x, pf_y = zip(*pareto)

    print("First 5 points:", points[:5])
    print("Pareto front points:", pareto)

    # Plot all solutions and Pareto front
    #plt.scatter(all_x, all_y, label=f'All: {name}', alpha=0.5)
    plt.plot(pf_x, pf_y, marker='o', label=f'Pareto: {name}')

plt.xlabel('Total Distinct Tasks (to maximize)')
plt.ylabel('Average Cycle Time (to minimize)')
plt.title('Pareto Fronts Comparison Across Experiments')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
