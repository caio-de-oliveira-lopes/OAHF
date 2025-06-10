
## Open Algorithm and Heuristic Framework (OAHF)

---

### 🚀 Overview

The **Open Algorithm and Heuristic Framework (OAHF)** is an extensible Python library designed to streamline the development, evaluation, and deployment of algorithms and metaheuristics for combinatorial optimization. Whether you need to prototype a new neighborhood move, benchmark heuristics on custom instances, or package your solution for distribution, OAHF provides:

- **Modular Architecture**: Plug in problem definitions, neighborhoods, and metaheuristics.
- **Cross-Platform Compatibility**: Runs on Linux, macOS, and Windows with Python ≥3.12.
- **Configuration-Driven**: Define experiments via JSON parameter files.
- **Performance-Optimized**: Optional Cython compilation and native extensions.

---

### 📋 Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Building & Packaging](#building--packaging)
7. [Contributors](#contributors)
8. [License](#license)
9. [Acknowledgements](#acknowledgements)

---

### ⚙️ Features

- **Customizable Heuristics**: Define neighborhoods, selection strategies, and metaheuristics.
- **Experiment Automation**: Batch-run multiple instances with different seeds and parameters.
- **Logging & Outputs**: Structured folders for results, logs, and statistics.
- **Extension-Friendly**: Add new solvers or problem types with minimal code.
- **Cython Integration**: Speed up critical components.

---

### 📦 Requirements

- **Operating System**: Linux, Windows, or macOS
- **Python**: 3.12 or higher
- **Dependencies**: Listed in `requirements.txt`

---

### 🔧 Installation

#### 1. Clone the repository

```bash
git clone https://github.com/<username>/OAHF.git
cd OAHF
```

#### 2. (Optional) Create a virtual environment

```bash
# Using conda
echo "Creating conda environment..."
conda create --name oahf-env python=3.12 -y
conda activate oahf-env

# Or using venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
```

#### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 🔧 Configuration

All runtime settings are driven by a **parameter JSON** (e.g., `oahf_parameters.json`). Below is a sample structure:

```json
{
  "file_name": "12_ros",
  "input_path": ["C:\\", "Projetos", "OAHF", "Instances", "alwabp"],
  "output_path": ["C:\\", "Projetos", "OAHF", "Outputs", "HAJR"],
  "cycle_time_path": ["C:\\", "Projetos", "OAHF", "Parameters", "recommeded_maximum_mean_cycle_time.json"],
  "heuristic_definition_file": ["C:\\", "Projetos", "OAHF", "Parameters", "heuristic_definition_hajr.json"],
  "input_type": "AlwabpSolution",
  "random_seed": 294165949277890002569088467705991431954
}
```

- **file_name**: Identifier for the instance or experiment.
- **input_path / output_path**: List of path segments for OS-agnostic file handling.
- **cycle_time_path**: Reference for cycle-time constraints.
- **heuristic_definition_file**: Contains neighborhood and metaheuristic settings.
- **input_type**: Specifies the problem solver type.
- **random_seed**: Ensures reproducibility.

Additional parameter files may include:

- `recommended_maximum_mean_cycle_time.json`
---

### ▶️ Usage

#### Run the Framework

```bash
python -m oahf --params path/to/oahf_parameters.json
```

This will:

1. Load the instance and parameters.
2. Initialize the problem and heuristic.
3. Execute the search/metaheuristic.
4. Save results and logs in the specified output directory.

#### Common Workflows

- **Single Experiment**: Run one parameter file.
- **Batch Experiments**: Use a shell script or Makefile to iterate over multiple JSON configs.

---

### 📦 Building & Packaging

#### Generate a Distributable Package

```bash
./oahf.bat  # Windows
# or
./oahf.sh   # Unix-like systems
```

#### Compile with Cython

```bash
python setup.py build_ext --inplace
```

---

### 🤝 Contributors

A special thanks to all the people who have contributed to this project:

<table>
  <tr>
    <td align="center">
      <a href="#">
        <img src="https://avatars.githubusercontent.com/u/27699897?v=4" width="100px;" alt="Mayron César de Oliveira Moreira no GitHub"/><br>
        <sub>
          <b>Mayron César de Oliveira Moreira</b>
        </sub>
      </a>
    </td>
  </tr>
</table>

---

### ⚖️ License

This project is licensed under the [MIT License](LICENSE).

---

### 🙏 Acknowledgements

- **Federal University of Lavras (UFLA)** – Computer Science Postgraduate Program.
- **CAPES, CNPq & FAPEMIG** – Funding agencies supporting research in Brazil.
- **All Contributors** who have helped evolve OAHF.
