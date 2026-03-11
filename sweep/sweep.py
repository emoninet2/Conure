#!/usr/bin/env python3
"""
Sweep script for artwork generation and optional simulation.

Behavior:
- Reads artwork JSON and sweep JSON
- Generates one run folder per permutation
- Writes:
    - parameters.json
    - <run_name>_artwork.json
    - summary.json
    - checkpoint.json
- Optionally generates layout/SVG
- Optionally runs simulation
- Optionally packs simulation results

Important:
- sweep.json contains only:
    {
      "parameters": {
        ...
      }
    }

Path note:
- simulator/simulator.py is resolved as ../simulator/simulator.py relative to this file
"""

import argparse
import copy
import glob
import itertools
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import skrf as rf
from dotenv import load_dotenv


# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",
        logging.INFO: "\033[92m",
        logging.WARNING: "\033[93m",
        logging.ERROR: "\033[91m",
        logging.CRITICAL: "\033[95m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = self.formatTime(record, self.datefmt)
        msg = super().format(record)
        return f"{timestamp} [SWEEP] {color}{msg}{self.RESET}"


logger = logging.getLogger("sweep")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter("%(levelname)s - %(message)s"))
    logger.addHandler(handler)


# ------------------------------------------------------------------------------
# Load .env and build paths
# ------------------------------------------------------------------------------
project_root = Path(__file__).resolve().parents[1]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

conure_path_env = os.getenv("CONURE_PATH")
if not conure_path_env:
    raise ValueError("CONURE_PATH is not set in the .env file!")
conure_path = (project_root / conure_path_env).resolve()

artwork_generator_rel = os.getenv("CONURE_ARTWORK_GENERATOR_PATH")
if not artwork_generator_rel:
    raise ValueError("CONURE_ARTWORK_GENERATOR_PATH is not set in the .env file!")
artwork_generator_path = (conure_path / artwork_generator_rel).resolve()

THIS_DIR = Path(__file__).resolve().parent
SIMULATOR_SCRIPT = (THIS_DIR / "../simulator/simulator.py").resolve()


# ------------------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------------------
def load_json_data(input_arg):
    try:
        return json.loads(input_arg)
    except json.JSONDecodeError:
        try:
            with open(input_arg, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            logger.error("File '%s' not found.", input_arg)
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error("File '%s' does not contain valid JSON.", input_arg)
            sys.exit(1)


def get_timestamp():
    return datetime.now().isoformat()


def _to_number(value, label):
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"{label} must be numeric, got: {value!r}") from exc


def get_sweep_values(param):
    """
    Convert a sweep parameter into a list of values.

    Accepted forms:
    - list: returned directly
    - dict with:
        {
          "from": ...,
          "to": ...,
          "type": "npoints" | "step",
          "value": ...
        }
    """
    if isinstance(param, list):
        return param

    if not isinstance(param, dict):
        raise TypeError("Sweep parameter must be either a list or a dict.")

    required = ["from", "to", "type", "value"]
    missing = [k for k in required if k not in param]
    if missing:
        raise ValueError(f"Missing keys in sweep parameter spec: {missing}")

    start = _to_number(param["from"], "'from'")
    end = _to_number(param["to"], "'to'")
    method = str(param["type"]).lower()
    raw_value = param["value"]

    if method == "npoints":
        try:
            count = int(raw_value)
        except Exception as exc:
            raise ValueError(f"npoints value must be an integer, got: {raw_value!r}") from exc

        if count < 1:
            raise ValueError(f"npoints value must be >= 1, got: {count}")

        values = np.linspace(start, end, count).tolist()

    elif method == "step":
        step = _to_number(raw_value, "'value' for step")

        if step == 0:
            raise ValueError("step value must not be 0")

        if end >= start and step < 0:
            step = abs(step)
        elif end < start and step > 0:
            step = -step

        values = []
        current = start
        eps = 1e-12

        if step > 0:
            while current <= end + eps:
                values.append(current)
                current += step
        else:
            while current >= end - eps:
                values.append(current)
                current += step

        values = [round(v, 12) for v in values]

    else:
        raise ValueError(f"Unknown sweep type: {param['type']}")

    cleaned = []
    for v in values:
        if isinstance(v, float) and float(v).is_integer():
            cleaned.append(int(v))
        else:
            cleaned.append(v)

    return cleaned


# ------------------------------------------------------------------------------
# Checkpoint database
# ------------------------------------------------------------------------------
def load_checkpoint_db(checkpoint_path):
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                data = f.read().strip()
                if not data:
                    return {"runs": {}}
                return json.loads(data)
        except json.JSONDecodeError:
            logger.warning(
                "Checkpoint file %s is empty or corrupted. Resetting checkpoint database.",
                checkpoint_path,
            )
            return {"runs": {}}
    return {"runs": {}}


def save_checkpoint_db(db, checkpoint_path):
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)


def update_checkpoint(run_key, checkpoint_db, checkpoint_path, updates):
    run_record = checkpoint_db.get("runs", {}).get(run_key, {})
    run_record.update(updates)
    checkpoint_db.setdefault("runs", {})[run_key] = run_record
    save_checkpoint_db(checkpoint_db, checkpoint_path)


# ------------------------------------------------------------------------------
# Summary helpers
# ------------------------------------------------------------------------------
def _count_run_states(checkpoint_db, total_runs):
    runs = checkpoint_db.get("runs", {})

    layout_completed = 0
    layout_failed = 0

    svg_completed = 0
    svg_failed = 0

    simulation_completed = 0
    simulation_failed = 0

    for _, rec in runs.items():
        if rec.get("layout_completed") is True:
            layout_completed += 1
        elif "layout_completed" in rec and rec.get("layout_completed") is False:
            layout_failed += 1

        if rec.get("svg_completed") is True:
            svg_completed += 1
        elif "svg_completed" in rec and rec.get("svg_completed") is False:
            svg_failed += 1

        if rec.get("simulation_completed") is True:
            simulation_completed += 1
        elif "simulation_completed" in rec and rec.get("simulation_completed") is False:
            simulation_failed += 1

    layout_pending = max(0, total_runs - layout_completed - layout_failed)
    svg_pending = max(0, total_runs - svg_completed - svg_failed)
    simulation_pending = max(0, total_runs - simulation_completed - simulation_failed)

    return {
        "layout": {
            "completed": layout_completed,
            "failed": layout_failed,
            "pending": layout_pending,
        },
        "svg": {
            "completed": svg_completed,
            "failed": svg_failed,
            "pending": svg_pending,
        },
        "simulation": {
            "completed": simulation_completed,
            "failed": simulation_failed,
            "pending": simulation_pending,
        },
    }


def update_summary(
    summary_file_path,
    total,
    completed,
    run_key,
    current_run_index,
    current_task,
    checkpoint_db,
    current_permutation=None,
    current_run_name=None,
    state="running",
    started_at=None,
    finished_at=None,
):
    progress_percentage = (completed / total) * 100 if total > 0 else 0.0
    counts = _count_run_states(checkpoint_db, total)

    summary = {
        "state": state,
        "total_permutations": total,
        "completed_runs": completed,
        "remaining_runs": max(0, total - completed),
        "current_run_index": current_run_index,
        "current_run": run_key,
        "current_run_name": current_run_name,
        "current_permutation": current_permutation,
        "current_task": current_task,
        "progress_percentage": progress_percentage,
        "counts": counts,
        "started_at": started_at,
        "finished_at": finished_at,
        "last_updated": get_timestamp(),
    }

    os.makedirs(os.path.dirname(summary_file_path), exist_ok=True)
    with open(summary_file_path, "w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, indent=4)


# ------------------------------------------------------------------------------
# Main sweep logic
# ------------------------------------------------------------------------------
def sweep(
    simulator,
    artworkData,
    sweepParam,
    simulatorConfig,
    base_output_dir,
    outputName,
    enableLayoutGeneration,
    generateSVG,
    enableSimulation,
    packSimulationResults,
    force=False,
    verbose=False,
    log_level=None,
):
    sweepPar = list(sweepParam["parameters"].keys())
    sweepData = [get_sweep_values(sweepParam["parameters"][param]) for param in sweepPar]
    permutations = list(itertools.product(*sweepData))

    total_permutations = len(permutations)
    width = max(4, len(str(total_permutations)))

    logger.info("Total number of permutations: %d", total_permutations)

    os.makedirs(base_output_dir, exist_ok=True)

    summary_file_path = os.path.join(base_output_dir, "summary.json")
    checkpoint_file_path = os.path.join(base_output_dir, "checkpoint.json")
    checkpoint_db = load_checkpoint_db(checkpoint_file_path)

    completedRuns = 0

    default_task_status = {
        "layout": {"status": "pending"},
        "svg": {"status": "pending"},
        "simulation": {"status": "pending"},
    }
    update_summary(
        summary_file_path,
        total_permutations,
        completedRuns,
        "N/A",
        -1,
        default_task_status,
        checkpoint_db,
        current_permutation={},
        current_run_name=None,
    )

    for run_index, permutation in enumerate(permutations):
        run_key = f"RunID_{run_index:0{width}d}"
        run_record = checkpoint_db.get("runs", {}).get(run_key, {})

        layout_done = run_record.get("layout_completed", False)
        svg_done = run_record.get("svg_completed", False)
        simulation_done = run_record.get("simulation_completed", False)

        run_artwork = copy.deepcopy(artworkData)
        run_artwork.setdefault("parameters", {})

        run_output_dir = os.path.join(base_output_dir, run_key)
        os.makedirs(run_output_dir, exist_ok=True)

        if outputName is None:
            base_name = run_artwork.get("metadata", {}).get("name", "artwork")
            run_name = f"{base_name}_{run_key}"
        else:
            run_name = f"{outputName}_{run_key}"

        run_artwork.setdefault("metadata", {})
        run_artwork["metadata"]["name"] = run_name

        logger.info("RunID: %d, Permutation: %s, Run Name: %s", run_index, permutation, run_name)

        current_permutation = {}

        # Always apply swept parameters to artwork
        runData = {"runID": run_index, "parameters": {}}
        for i, param in enumerate(sweepPar):
            value = permutation[i]
            run_artwork["parameters"][param] = value
            runData["parameters"][param] = value
            current_permutation[param] = value

        run_parameters_json_path = os.path.join(run_output_dir, "parameters.json")

        # Overwrite on force, otherwise create if missing
        if force or not os.path.exists(run_parameters_json_path):
            with open(run_parameters_json_path, "w", encoding="utf-8") as parfile:
                json.dump(runData, parfile, indent=4)

        update_checkpoint(
            run_key,
            checkpoint_db,
            checkpoint_file_path,
            {
                "parameters": runData["parameters"],
                "run_name": run_name,
            },
        )

        # Always save the actual artwork used for this run
        artwork_json_path = os.path.join(run_output_dir, f"{run_name}_artwork.json")
        with open(artwork_json_path, "w", encoding="utf-8") as f:
            json.dump(run_artwork, f, indent=4)

        # Optional convenience copy
        plain_artwork_json_path = os.path.join(run_output_dir, "artwork.json")
        with open(plain_artwork_json_path, "w", encoding="utf-8") as f:
            json.dump(run_artwork, f, indent=4)

        portCount = len(run_artwork.get("ports", {}).get("config", {}).get("simulatingPorts", []))
        gdsPath = os.path.join(run_output_dir, f"{run_name}.gds")
        svgPath = os.path.join(run_output_dir, f"{run_name}.svg")
        sParamPath = os.path.join(run_output_dir, f"{run_name}.s{portCount}p")

        if enableLayoutGeneration or enableSimulation:
            if os.path.exists(gdsPath) and layout_done and not force:
                logger.warning("GDS file for %s already exists. Skipping layout generation.", run_key)
                needs_layout = False
            else:
                if os.path.exists(gdsPath) and force:
                    logger.warning("Force overwrite of GDS file for %s", run_key)
                needs_layout = True
        else:
            needs_layout = False

        if generateSVG:
            if os.path.exists(svgPath) and svg_done and not force:
                logger.warning("SVG for %s already exists. Skipping SVG generation.", run_key)
                needs_svg = False
            else:
                if os.path.exists(svgPath) and force:
                    logger.warning("Force overwrite of SVG file for %s", run_key)
                needs_svg = True
        else:
            needs_svg = False

        if needs_layout or needs_svg:
            task_status = {
                "layout": {"status": "in progress", "last_updated": get_timestamp()} if needs_layout else {"status": "completed"},
                "svg": {"status": "in progress", "last_updated": get_timestamp()} if needs_svg else {"status": "completed"},
                "simulation": {"status": "pending"},
            }
            update_summary(
                summary_file_path,
                total_permutations,
                completedRuns,
                run_key,
                run_index,
                task_status,
                checkpoint_db,
                current_permutation=current_permutation,
                current_run_name=run_name,
            )

            logger.info(
                "Generating artwork for %s (needs_layout: %s, needs_svg: %s)",
                run_key,
                needs_layout,
                needs_svg,
            )

            command = [
                sys.executable,
                str(artwork_generator_path),
                "-a",
                json.dumps(run_artwork),
                "-o",
                run_output_dir,
                "-n",
                run_name,
            ]
            if enableLayoutGeneration:
                command.append("--layout")
            if generateSVG:
                command.append("--svg")
            if verbose:
                command.append("--verbose")
            if log_level:
                command.extend(["--log-level", log_level])

            logger.debug("Running artwork generation command: %s", " ".join(command))
            process = subprocess.run(command)

            if process.returncode == 0:
                logger.info("Artwork generation succeeded for %s", run_key)
                if needs_layout:
                    update_checkpoint(
                        run_key,
                        checkpoint_db,
                        checkpoint_file_path,
                        {"layout_completed": os.path.exists(gdsPath)},
                    )
                if needs_svg:
                    update_checkpoint(
                        run_key,
                        checkpoint_db,
                        checkpoint_file_path,
                        {"svg_completed": os.path.exists(svgPath)},
                    )
            else:
                logger.error("Artwork generation failed for %s with code %d", run_key, process.returncode)
                if needs_layout:
                    update_checkpoint(
                        run_key,
                        checkpoint_db,
                        checkpoint_file_path,
                        {"layout_completed": False},
                    )
                if needs_svg:
                    update_checkpoint(
                        run_key,
                        checkpoint_db,
                        checkpoint_file_path,
                        {"svg_completed": False},
                    )

        if enableSimulation:
            should_run_sim = force or not simulation_done or not os.path.exists(sParamPath)

            if os.path.exists(gdsPath) and should_run_sim:
                task_status = {
                    "layout": {"status": "completed"},
                    "svg": {"status": "completed" if os.path.exists(svgPath) else "pending"},
                    "simulation": {"status": "in progress", "last_updated": get_timestamp()},
                }
                update_summary(
                    summary_file_path,
                    total_permutations,
                    completedRuns,
                    run_key,
                    run_index,
                    task_status,
                    checkpoint_db,
                    current_permutation=current_permutation,
                    current_run_name=run_name,
                )

                logger.info("Performing EM simulation for %s", run_key)

                command = [
                    sys.executable,
                    str(SIMULATOR_SCRIPT),
                    "-f",
                    gdsPath,
                    "-a",
                    json.dumps(run_artwork),
                    "-c",
                    simulatorConfig if simulatorConfig else "",
                    "--sim",
                    simulator,
                    "-o",
                    run_output_dir,
                    "-n",
                    run_name,
                ]

                if verbose:
                    command.append("--verbose")
                if log_level:
                    command.extend(["--log-level", log_level])

                command = [arg for arg in command if arg]

                logger.debug("Running simulation command: %s", " ".join(command))
                process = subprocess.run(command)

                if process.returncode == 0:
                    logger.info("Simulation succeeded for %s", run_key)
                    update_checkpoint(
                        run_key,
                        checkpoint_db,
                        checkpoint_file_path,
                        {"simulation_completed": os.path.exists(sParamPath)},
                    )
                else:
                    logger.error("Simulation failed for %s with code %d", run_key, process.returncode)
                    update_checkpoint(
                        run_key,
                        checkpoint_db,
                        checkpoint_file_path,
                        {"simulation_completed": False},
                    )
            elif enableSimulation and not os.path.exists(gdsPath):
                logger.warning("Skipping simulation for %s because GDS file is missing.", run_key)

        completedRuns += 1
        task_status = {
            "layout": {"status": "completed" if os.path.exists(gdsPath) else "pending"},
            "svg": {"status": "completed" if os.path.exists(svgPath) else "pending"},
            "simulation": {"status": "completed" if os.path.exists(sParamPath) else "pending"},
        }
        update_summary(
            summary_file_path,
            total_permutations,
            completedRuns,
            run_key,
            run_index,
            task_status,
            checkpoint_db,
            current_permutation=current_permutation,
            current_run_name=run_name,
        )

    if packSimulationResults:
        logger.info("Packing simulation results from base output: %s", base_output_dir)
        pack_simulation_data(base_output_dir)

        # refresh summary one last time after pack step
        update_summary(
            summary_file_path,
            total_permutations,
            completedRuns,
            "DONE",
            total_permutations - 1 if total_permutations > 0 else -1,
            {
                "layout": {"status": "completed"},
                "svg": {"status": "completed" if generateSVG else "pending"},
                "simulation": {"status": "completed" if enableSimulation else "pending"},
                "packing": {"status": "completed"},
            },
            checkpoint_db,
            current_permutation={},
            current_run_name=None,
        )
    else:
        update_summary(
            summary_file_path,
            total_permutations,
            completedRuns,
            "DONE",
            total_permutations - 1 if total_permutations > 0 else -1,
            {
                "layout": {"status": "completed"},
                "svg": {"status": "completed" if generateSVG else "pending"},
                "simulation": {"status": "completed" if enableSimulation else "pending"},
            },
            checkpoint_db,
            current_permutation={},
            current_run_name=None,
        )


# ------------------------------------------------------------------------------
# Pack simulation data
# ------------------------------------------------------------------------------
def pack_simulation_data(sweep_dir):
    logger.info("Packing simulation results from directory: %s", sweep_dir)

    features_list = []
    targets_list = []
    feature_names = None
    target_names = None
    frequency_points = None

    for run_folder in os.listdir(sweep_dir):
        if not run_folder.startswith("RunID"):
            continue

        run_path = os.path.join(sweep_dir, run_folder)
        parameters_path = os.path.join(run_path, "parameters.json")
        if not os.path.exists(parameters_path):
            continue

        with open(parameters_path, "r", encoding="utf-8") as param_file:
            params = json.load(param_file)
            params_values = list(params["parameters"].values())
            if feature_names is None:
                feature_names = list(params["parameters"].keys())
            features_list.append(params_values)

        touchstone_files = glob.glob(os.path.join(run_path, "*.s*p"))
        if touchstone_files:
            touchstone_path = touchstone_files[0]
            logger.info("Touchstone file found: %s", touchstone_path)
            network = rf.Network(touchstone_path)
            num_ports = network.s.shape[1]

            if frequency_points is None:
                frequency_points = network.f

            if target_names is None:
                target_names = []
                for i in range(num_ports):
                    for j in range(num_ports):
                        target_names.append(f"S{i+1}{j+1}_real")
                        target_names.append(f"S{i+1}{j+1}_imag")

            s_real_imag = []
            for i in range(num_ports):
                for j in range(num_ports):
                    s_real_imag.append(network.s[:, i, j].real)
                    s_real_imag.append(network.s[:, i, j].imag)

            s_real_imag = np.stack(s_real_imag, axis=0)
            targets_list.append(s_real_imag)
        else:
            logger.warning("No touchstone file found for %s", run_folder)

    if not targets_list:
        logger.warning("No touchstone files found. Skipping packing operation.")
        return

    features_array = np.array(features_list)
    targets_array = np.array(targets_list)
    output_npz_path = os.path.join(sweep_dir, "simulation_data.npz")

    np.savez(
        output_npz_path,
        features=features_array,
        targets=targets_array,
        feature_names=feature_names,
        target_names=target_names,
        frequency_points=frequency_points,
    )

    logger.info("Packed simulation results saved to: %s", output_npz_path)


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Sweep script for artwork generation and simulation using .env paths with checkpointing."
    )
    parser.add_argument("--artwork", "-a", required=True, help="JSON data or file path for artwork description file")
    parser.add_argument("--sweep", required=True, help="JSON file path for sweep parameters datafile")
    parser.add_argument("--output", "-o", required=True, help="Base output directory")
    parser.add_argument("--name", "-n", help="Output file base name")
    parser.add_argument("--layout", action="store_true", help="Enable layout generation in GDSII")
    parser.add_argument("--svg", action="store_true", help="Enable SVG generation")
    parser.add_argument("--simulate", action="store_true", help="Enable simulation")
    parser.add_argument("--pack_sim", action="store_true", help="Package simulation results")
    parser.add_argument("--simulator", "--sim", choices=["emx", "openems", "empro", "raptor"], help="Choose a simulator")
    parser.add_argument("--config", "-c", help="JSON configuration file for the simulator configuration", default=None)
    parser.add_argument("--force", action="store_true", help="Force overwrite of existing outputs")
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level",
        default=None,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose (debug) output")

    args = parser.parse_args()

    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    if args.verbose:
        effective_level = logging.DEBUG
    elif args.log_level:
        effective_level = log_levels[args.log_level]
    else:
        effective_level = logging.INFO

    logger.setLevel(effective_level)
    logger.debug("Effective log level set to %s.", logging.getLevelName(effective_level))

    artworkData = load_json_data(args.artwork)
    sweepData = load_json_data(args.sweep)

    arg_log_level = args.log_level if args.log_level and not args.verbose else "debug" if args.verbose else None

    sweep(
        args.simulator,
        artworkData,
        sweepData,
        args.config,
        args.output,
        args.name,
        enableLayoutGeneration=args.layout,
        generateSVG=args.svg,
        enableSimulation=args.simulate,
        packSimulationResults=args.pack_sim,
        force=args.force,
        verbose=args.verbose,
        log_level=arg_log_level,
    )


if __name__ == "__main__":
    main()