# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
import re
from datetime import datetime

# ------- Configuration -------
base_path = Path(r"C:\Projetos\OAHF\Outputs")
algorithms = {
    'HAJR1': 'HAJR',
    'HAJR2': 'Iterative_HAJR'
}
seeds = [
    "144911535910197828289965286135314374916",
    "294165949277890002569088467705991431954",
    "34707186982903718312397416735273231795"
]
families = ["hes", "ros", "ton", "wee"]
instance_range = range(1, 81)

# Map substrings to heuristic categories
categories = {
    'IterativeConstruction': 'IterativeConstruction',
    'GRASP': 'GRASP',
    'PILS': 'Local Searches',
    'SinglePeriodJobRotationLocalSearch': 'Local Searches',
    'SubperiodJobRotationLocalSearch': 'Local Searches',
    'TabuSearch': 'TabuSearch',
    'HGA': 'HGA'
}
all_categories = set(categories.values()) | {'Unmatched'}

# Regex for timestamped folders
ts_pattern = re.compile(r"^output_(\d{2}-\d{2}-\d{4})_(\d{1,2})h-(\d{1,2})m-(\d{1,2})s$")

# Accumulators
sum_ratios = {algo: {fam: {cat: 0.0 for cat in all_categories} for fam in families} for algo in algorithms}
run_counts = {algo: {fam: 0 for fam in families} for algo in algorithms}

# Helper to canonicalize a period solution structure (excluding 'id')
def canonical_structure(sol):
    # Remove the 'id' key and sort the remaining items for consistent representation
    struct = {k: sol[k] for k in sol if k != 'id' and k!= 'name'}
    for i in range(len(struct["task_allocations_per_station"])):
        struct["task_allocations_per_station"][i]["tasks"] = list(sorted(struct["task_allocations_per_station"][i]["tasks"]))

    return json.dumps(struct, sort_keys=False)

# Loop through runs
for algo_key, algo_dir in algorithms.items():
    for seed in seeds:
        for inst in instance_range:
            for fam in families:
                inst_folder = base_path / algo_dir / f"seed_{seed}" / f"{inst}_{fam}"
                if not inst_folder.is_dir():
                    continue

                # Find latest timestamped output folder
                candidates = []
                for sub in inst_folder.iterdir():
                    if sub.is_dir() and sub.name.startswith('output_'):
                        m = ts_pattern.match(sub.name)
                        if m:
                            date_str, h, mnt, s = m.groups()
                            dt = datetime.strptime(f"{date_str} {h}:{mnt}:{s}", "%m-%d-%Y %H:%M:%S")
                            candidates.append((dt, sub))
                if not candidates:
                    continue
                latest_folder = max(candidates, key=lambda x: x[0])[1]

                # Locate JSON files
                final_json = next(
                    (f for f in latest_folder.iterdir()
                     if f.is_file() and f.name.startswith('output_job_rotation_alwabp_solution') and f.suffix == '.json'),
                    None
                )
                pool_json = latest_folder / 'output_list_pool_0.json'
                if not final_json or not pool_json.is_file():
                    continue

                # Load JSON data
                with open(final_json, 'r', encoding='utf-8') as f:
                    final_data = json.load(f)
                with open(pool_json, 'r', encoding='utf-8') as f:
                    pool_data = json.load(f)

                # Build a map from canonical structure to metaheuristic
                struct_map = {}
                for item in pool_data.get('solutions', []):
                    canon = canonical_structure(item)
                    struct_map[canon] = pool_data['solution_info'][str(item['id'])].get('metaheuristic', '')

                period_solutions = final_data.get('period_solutions', [])
                num_periods = len(period_solutions)
                if num_periods == 0:
                    raise Exception()

                # Count by category using structure comparison
                run_counts_per_cat = {cat: 0 for cat in all_categories}
                for period in period_solutions:
                    canon = canonical_structure(period)
                    meta_label = struct_map.get(canon, '')
                    matched = False
                    for key, cat in categories.items():
                        if key in meta_label:
                            run_counts_per_cat[cat] += 1
                            matched = True
                            break
                    if not matched:
                        run_counts_per_cat['Unmatched'] += 1
                        print(f"Unmatched structure: {final_json}")
                        print(canon)
                        raise Exception()

                # Accumulate ratios and run count
                for cat, cnt in run_counts_per_cat.items():
                    sum_ratios[algo_key][fam][cat] += cnt / num_periods
                run_counts[algo_key][fam] += 1

# Compute average percentages
percentages = {
    algo: {
        fam: {cat: (sum_ratios[algo][fam][cat] / (run_counts[algo][fam] or 1)) * 100
              for cat in all_categories}
        for fam in families
    }
    for algo in algorithms
}

# Output results
import pprint
print("Processed runs per family (out of 240 expected):")
pprint.pprint(run_counts)
print("Average heuristic contributions (% of periods per run):")
pprint.pprint(percentages)
