import os
import re
import json
import statistics
from datetime import datetime
from pathlib import Path

# Configuration
infeasibilities = {
    10: ['1_hes', '21_ros', '21_ton', '22_hes', '22_ros', '22_ton', '23_hes', '23_ros', '23_ton', '25_hes', '25_ros', '25_ton', '26_hes', '26_ros', '27_hes', '27_ros', '28_ros', '29_hes', '2_hes', '2_ros', '2_wee', '30_hes', '30_ros', '32_hes', '32_ros', '32_ton', '33_hes', '33_ros', '33_wee', '34_hes', '35_ros', '36_hes', '37_ros', '37_ton', '39_hes', '39_wee', '3_hes', '3_ros', '3_ton', '40_hes', '40_ros', '41_ros', '42_ros', '44_hes', '44_ros', '45_ros', '46_ros', '47_hes', '48_hes', '4_hes', '50_hes', '5_hes', '5_ros', '61_hes', '62_hes', '62_ros', '62_ton', '63_hes', '63_ros', '65_hes', '65_ros', '66_ros', '67_ros', '69_ros', '6_hes', '6_ros', '70_hes', '70_ros', '71_hes', '71_ros', '72_hes', '72_ros', '73_ros', '74_ros', '75_ros', '76_ros', '78_hes', '78_ros', '79_hes', '79_ros', '80_ros', '8_hes', '8_ros', '9_hes', '9_ton'],
    20: ['10_hes', '10_ros', '10_ton', '10_wee', '11_hes', '11_ros', '11_ton', '11_wee', '12_hes', '12_ros', '12_ton', '12_wee', '13_hes', '13_ros', '13_ton', '13_wee', '14_hes', '14_ros', '14_ton', '14_wee', '15_hes', '15_ros', '15_ton', '15_wee', '16_hes', '16_ros', '16_ton', '16_wee', '17_hes', '17_ros', '17_ton', '17_wee', '18_hes', '18_ros', '18_ton', '18_wee', '19_hes', '19_ros', '19_ton', '19_wee', '1_ros', '1_ton', '1_wee', '20_hes', '20_ros', '20_ton', '20_wee', '21_hes', '21_wee', '22_wee', '23_wee', '24_hes', '24_ros', '24_ton', '24_wee', '25_wee', '26_ton', '26_wee', '27_ton', '27_wee', '28_hes', '28_ton', '28_wee', '29_ros', '29_ton', '29_wee', '2_ton', '30_ton', '30_wee', '31_hes', '31_ros', '31_ton', '31_wee', '32_wee', '33_ton', '34_ros', '34_ton', '34_wee', '35_hes', '35_ton', '35_wee', '36_ros', '36_ton', '36_wee', '37_hes', '37_wee', '38_hes', '38_ros', '38_ton', '38_wee', '39_ros', '39_ton', '3_wee', '40_ton', '40_wee', '41_hes', '41_ton', '41_wee', '42_hes', '42_ton', '42_wee', '43_hes', '43_ros', '43_ton', '43_wee', '44_ton', '44_wee', '45_hes', '45_ton', '45_wee', '46_hes', '46_ton', '46_wee', '47_ros', '47_ton', '47_wee', '48_ros', '48_ton', '48_wee', '49_hes', '49_ros', '49_ton', '49_wee', '4_ros', '4_ton', '4_wee', '50_ros', '50_ton', '50_wee', '51_hes', '51_ros', '51_ton', '51_wee', '52_hes', '52_ros', '52_ton', '52_wee', '53_hes', '53_ros', '53_ton', '53_wee', '54_hes', '54_ros', '54_ton', '54_wee', '55_hes', '55_ros', '55_ton', '55_wee', '56_hes', '56_ros', '56_ton', '56_wee', '57_hes', '57_ros', '57_ton', '57_wee', '58_hes', '58_ros', '58_ton', '58_wee', '59_hes', '59_ros', '59_ton', '59_wee', '5_ton', '5_wee', '60_hes', '60_ros', '60_ton', '60_wee', '61_ros', '61_ton', '61_wee', '62_wee', '63_ton', '63_wee', '64_hes', '64_ros', '64_ton', '64_wee', '65_ton', '65_wee', '66_hes', '66_ton', '66_wee', '67_hes', '67_ton', '67_wee', '68_hes', '68_ros', '68_ton', '68_wee', '69_hes', '69_ton', '69_wee', '6_ton', '6_wee', '70_ton', '70_wee', '71_ton', '71_wee', '72_ton', '72_wee', '73_hes', '73_ton', '73_wee', '74_hes', '74_ton', '74_wee', '75_hes', '75_ton', '75_wee', '76_hes', '76_ton', '76_wee', '77_hes', '77_ros', '77_ton', '77_wee', '78_ton', '78_wee', '79_ton', '79_wee', '7_hes', '7_ros', '7_ton', '7_wee', '80_hes', '80_ton', '80_wee', '8_ton', '8_wee', '9_ros', '9_wee']
}

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

# Regex to extract timestamp from output directory name (MM-DD-YYYY)
timestamp_pattern = re.compile(
    r"^output_(\d{2}-\d{2}-\d{4})_(\d{1,2})h-(\d{1,2})m-(\d{1,2})s$"
)

def parse_timestamp(folder_name: str):
    match = timestamp_pattern.match(folder_name)
    if not match:
        return None
    date_str, hour, minute, second = match.groups()
    return datetime.strptime(
        f"{date_str} {hour}:{minute}:{second}",
        "%m-%d-%Y %H:%M:%S"
    )

# Collect raw observations per family
observations = {fam: [] for fam in families}

# Traverse outputs to gather metrics
for algo_key, algo_dir in algorithms.items():
    for seed in seeds:
        for inst in instance_range:
            for fam in families:
                inst_key = f"{inst}_{fam}"
                # determine infeasibility %
                perc = next((p for p, lst in infeasibilities.items() if inst_key in lst), None)
                if perc is None:
                    continue
                folder = base_path / algo_dir / f"seed_{seed}" / inst_key
                if not folder.is_dir():
                    continue
                # find latest output dir
                candidates = []
                for subdir in folder.iterdir():
                    if subdir.is_dir() and subdir.name.startswith("output_"):
                        ts = parse_timestamp(subdir.name)
                        if ts:
                            candidates.append((ts, subdir))
                if not candidates:
                    continue
                latest = max(candidates, key=lambda x: x[0])[1]
                # find JSON
                for file in latest.iterdir():
                    if file.is_file() and file.name.startswith("output_job_rotation_alwabp_solution") and file.suffix == ".json":
                        data = json.load(open(file, 'r', encoding='utf-8'))
                        # get metrics
                        ndt = data.get('total_distinct_tasks')
                        workers = len(data.get('distinct_tasks_per_worker', {}))
                        cycle = data.get('average_cycle_time')
                        observations[fam].append({
                            'infeasibility': perc,
                            'algorithm': algo_key,
                            'workers': workers,
                            'ndt': ndt,
                            'cycle': cycle
                        })

# Aggregate by family, workers count, infeasibility %, algorithm
results = {}
for fam, obs_list in observations.items():
    results[fam] = {}
    # group observations
    grouped = {}
    for obs in obs_list:
        key = (obs['workers'], obs['infeasibility'], obs['algorithm'])
        grouped.setdefault(key, []).append(obs)
    # compute summaries
    for (workers, perc, algo), group in grouped.items():
        ndt_vals = [o['ndt'] for o in group]
        cycle_vals = [o['cycle'] for o in group]
        summary = {
            'mean_ndt': statistics.mean(ndt_vals),
            'std_ndt': statistics.stdev(ndt_vals) if len(ndt_vals) > 1 else 0.0,
            'mean_cycle': statistics.mean(cycle_vals),
            'std_cycle': statistics.stdev(cycle_vals) if len(cycle_vals) > 1 else 0.0
        }
        results[fam].setdefault(workers, {}).setdefault(perc, {})[algo] = summary

# Display results dictionary
import pprint
pprint.pprint(results)
