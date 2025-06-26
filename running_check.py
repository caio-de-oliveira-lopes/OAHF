#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import fnmatch
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
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

# Regex to match folders named like: output_MM-DD-YYYY_Hh-Mm-Ss
ts_pattern = re.compile(r"^output_(\d{2}-\d{2}-\d{4})_(\d{1,2})h-(\d{1,2})m-(\d{1,2})s$")


def find_latest_output_folder(inst_folder: Path):
    """
    Given a directory, return the subdirectory with the latest timestamp
    matching ts_pattern, or None if none found.
    """
    candidates = []
    for sub in inst_folder.iterdir():
        if not sub.is_dir():
            continue
        m = ts_pattern.match(sub.name)
        if not m:
            continue
        date_str, hh, mm, ss = m.groups()
        dt = datetime.strptime(f"{date_str} {hh}:{mm}:{ss}", "%m-%d-%Y %H:%M:%S")
        candidates.append((dt, sub))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


def main():
    # missing[algo][seed] = list of "inst_family" that failed
    missing = {algo: {seed: [] for seed in seeds} for algo in algorithms}
    # success_both[seed] = list of "inst_family" that succeeded for both algos
    success_both = {seed: [] for seed in seeds}

    for seed in seeds:
        for fam in families:
            for inst in instance_range:
                id_str = f"{inst}_{fam}"
                # track success per algorithm for this (seed, fam, inst)
                success = {}

                for algo_key, algo_dir in algorithms.items():
                    inst_folder = base_path / algo_dir / f"seed_{seed}" / id_str
                    if not inst_folder.is_dir():
                        success[algo_key] = False
                    else:
                        latest = find_latest_output_folder(inst_folder)
                        if latest is None:
                            success[algo_key] = False
                        else:
                            # match any JSON starting with the base name + wildcard
                            names = fnmatch.filter(
                                [f.name for f in latest.iterdir() if f.is_file()],
                                "output_job_rotation_alwabp_solution*.json"
                            )
                            final_json = (latest / names[0]) if names else None
                            success[algo_key] = bool(final_json and final_json.is_file())

                    if not success[algo_key]:
                        missing[algo_key][seed].append(id_str)

                # if both algorithms succeeded, record this instance
                if all(success.values()):
                    success_both[seed].append(id_str)

    # Reporting
    print("==== Missing or Failed Runs ====")
    for algo_key in algorithms:
        print(f"\nAlgorithm {algo_key}:")
        for seed in seeds:
            lst = missing[algo_key][seed]
            print(f"  Seed {seed}: {len(lst)} failures => {lst}")

    print("\n==== Instances Completed by Both Algorithms ====")
    for seed, lst in success_both.items():
        print(f"  Seed {seed}: {len(lst)} successful => {lst}")

    # Intersection across all seeds
    all_both = set(success_both[seeds[0]])
    for s in seeds[1:]:
        all_both &= set(success_both[s])
    all_both_list = sorted(all_both)

    print("\n==== Instances Completed by Both Algorithms in ALL Seeds ====")
    print(f"  Total: {len(all_both_list)} => {all_both_list}")


if __name__ == "__main__":
    main()
