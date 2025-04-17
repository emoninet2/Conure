<img src="./resources/images/logo_nb_large.png" alt="Conure Logo" width="120"/>

# Conure
**Passive Device Artwork Generator, Modeling & Optimization**

Conure is a versatile toolkit for designing, simulating, modeling, and optimizing RFCMOS integrated inductors. It seamlessly integrates artwork generation, EM simulation, surrogate modeling with Artificial Neural Networks (ANN), and multi-objective optimization using NSGA-II. Currently, it supports the Cadence EMX simulator, with plans to add OpenEMS.

---

## 🚀 Features

### 🎨 Artwork Generation
- Generate inductor layouts from JSON templates.
- Customizable via stacking, line widths, spacing, and dummy fills.

<img src="./resources/images/inductorLayout.png" alt="Inductor Layout" width="600"/>

### 🔩 Via & Guard Ring
- Create, stack, and fill vias across layers with precise control.
- Automatically generate guard rings with substrate contacts and dummy fills (checkered pattern).

<div style="display:flex; gap: 1rem;">
  <img src="./resources/images/ViaStacking.png" alt="Via Stacking" width="300"/>
  <img src="./resources/images/GuardRing.png" alt="Guard Ring" width="300"/>
</div>

### 🤖 ANN Surrogate Modeling
- Train and evaluate neural networks to predict inductance (L) and quality factor (Q).
- Hyperparameter tuning for optimal performance.

<div style="display:flex; gap: 1rem;">
  <img src="./resources/images/model_comparision_L.png" alt="Model Comparison L" width="300"/>
  <img src="./resources/images/model_comparision_Q.png" alt="Model Comparison Q" width="300"/>
</div>

### 🏆 Multi-Objective Optimization
- Optimize inductors for target performance using the NSGA-II algorithm.
- Visualize Pareto fronts for trade-off analysis.

<img src="./resources/images/Pareto.png" alt="Pareto Front" width="300"/>

### 🔍 EM Simulation
- Run EM simulations with Cadence EMX.
- Configurable via JSON.

### 🖥️ UiX Interface (Beta)
Conure includes an interactive UiX (User Interaction eXperience) tool combining a Flask backend and a React (Vite) frontend for streamlined artwork description editing and live previews.

<img src="./resources/images/uix_artwork_preview.png" alt="UiX Preview" width="500"/>

#### Starting the UiX
- **`./start.sh`**  
  Launches `start_uix.sh` in the background as a daemon, capturing output in `uix.log`.
- **`./start_uix.sh`**  
  - Loads environment variables from `.env` (if present).
  - Defaults: Backend port 5000 (`VITE_BACKEND_PORT`), Frontend port 5173 (`FRONTEND_PORT`).
  - Starts the Flask backend (`uix/backend`) and the React (Vite) frontend (`uix/frontend`).
  - Writes PIDs to `uix.lock` in the project root.
  - Displays running ports and PIDs.
- **`./stop.sh`**  
  Stops UiX by running `stop_uix.sh` (logging to `stop_uix.log`). Ensure `stop_uix.sh` is present and executable.

#### Logs & Status
- **Logs**:  
  - `uix.log` — Captures both backend and frontend startup output.  
  - `stop_uix.log` — Captures UiX shutdown output.
- **Lockfile**:  
  - `uix.lock` — Stores process names and PIDs. The start script detects existing processes to prevent multiple instances.

---

## 📦 Installation

1. Clone the repository:
   ```bash
   $ git clone https://github.com/<your-org>/conure.git
   $ cd conure
   ```
2. Create a Python virtual environment and install dependencies:
   ```bash
   $ ./setup_venv.sh 
   $ source .venv/bin/activate
   ```
3. Ensure Cadence EMX is installed and configured if you plan to run EM simulations.

---

## ⚙️ Quickstart

*Note*: Replace `OUTPUT_DIR` and `SWEEP_OUTPUT` (in uppercase) with your own desired output directory paths when running the commands.


### Artwork Generation
```bash
$ python artwork_generator.py \
    --artwork artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json \
    --output OUTPUT_DIR \
    --name my_artwork \
    --layout \
    --svg
```

### EM Simulation
```bash
$ python simulator.py \
    --gds OUTPUT_DIR/my_artwork.gds \
    --config simulator/config.json \
    --sim emx \
    --artwork artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json \
    --output OUTPUT_DIR \
    --name my_artwork
```

### Sweep (Batch Generation + Simulation)
```bash
$ python sweep.py \
    --artwork artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json \
    --sweep sweep.json \
    --output SWEEP_OUTPUT \
    --layout \
    --simulate \
    --config simulator/config.json \
    --sim emx
```

---

## 🏗️ Development & Contribution

Contributions are welcome! Please fork the repo, create a feature branch, and submit a pull request. For major changes, open an issue first to discuss your ideas.

1. Fork the repository
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 👥 Team

- **Habibur Rahman** – University of Oslo, Norway
- **Adrian Llop Recha** – University of Oslo, Norway
- **Stefano Fasciani** – University of Oslo, Norway
- **Pål Gunnar Hogganvik** – University of Oslo, Norway
- **Kristian Kjelgård** – University of Oslo, Norway
- **Dag Wisland** – University of Oslo, Norway

---

## 📖 Citation
If you use Conure in your research, please cite:

> H. Rahman, A. L. Recha, S. Fasciani, P. G. Hogganvik, K. G. Kjelgård and D. T. Wisland, "Conure: Surrogate-based Artwork Generator for RFCMOS Integrated Inductors," in *2024 IEEE International Symposium on Circuits and Systems (ISCAS)*, Singapore, May 2024, pp. 1-5. doi: [10.1109/ISCAS58744.2024.10558598](https://ieeexplore.ieee.org/document/10558598)

---

## 📝 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

