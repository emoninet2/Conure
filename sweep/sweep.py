#!/usr/bin/env python3
"""
Refactored sweep.py with:

- .env configuration loading
- Checkpoint resume support
- status.json live progress tracking
- summary.json structured logging
- total sweep timing
- layout/svg/simulation success tracking
- original verbose logging preserved
"""

import argparse
import os
import json
import sys
import itertools
import copy
import subprocess
import glob
import logging
import numpy as np
import skrf as rf
import time

from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# Logging Setup (Preserves Original Output Format)
# ------------------------------------------------------------------------------

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",     # Blue
        logging.INFO: "\033[92m",      # Green
        logging.WARNING: "\033[93m",   # Yellow
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = self.formatTime(record, self.datefmt)
        msg = super().format(record)
        return f"{timestamp} [SWEEP] {color}{msg}{self.RESET}"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        #ColorFormatter('%(asctime)s %(levelname)s - %(message)s')
        ColorFormatter('%(levelname)s - %(message)s')
    )
    logger.addHandler(handler)

# ------------------------------------------------------------------------------
# Load .env
# ------------------------------------------------------------------------------

project_root = Path(__file__).resolve().parents[1]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

def get_env_path(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} not set in .env")
    return (project_root / os.getenv("CONURE_PATH") / value).resolve()

conure_path = (project_root / os.getenv("CONURE_PATH")).resolve()
artwork_generator_path = get_env_path("CONURE_ARTWORK_GENERATOR_PATH")
simulator_path = get_env_path("CONURE_SIMULATOR_PATH")

# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

def load_json_data(input_arg):
    try:
        return json.loads(input_arg)
    except json.JSONDecodeError:
        with open(input_arg, "r") as f:
            return json.load(f)

def get_timestamp():
    return datetime.now().isoformat()

def get_sweep_values(param):
    if isinstance(param, list):
        return param
    elif isinstance(param, dict):
        start = param["from"]
        end = param["to"]
        method = param["type"].lower()
        val = param["value"]

        if method == "npoints":
            return np.linspace(start, end, val).tolist()
        elif method == "step":
            return np.arange(start, end + val, val).tolist()
        else:
            raise ValueError("Unknown sweep type")
    else:
        raise TypeError("Invalid sweep parameter")

# ------------------------------------------------------------------------------
# Checkpoint Functions
# ------------------------------------------------------------------------------

def load_checkpoint_db(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except:
            return {"runs": {}}
    return {"runs": {}}

def save_checkpoint_db(db, path):
    with open(path, "w") as f:
        json.dump(db, f, indent=4)

def update_checkpoint(run_key, db, path, updates):
    db.setdefault("runs", {})
    db["runs"].setdefault(run_key, {})
    db["runs"][run_key].update(updates)
    save_checkpoint_db(db, path)

# ------------------------------------------------------------------------------
# Status Update
# ------------------------------------------------------------------------------

def update_status(path, total, completed, run_key, task_info):
    status = {
        "total_permutations": total,
        "completed_runs": completed,
        "current_run": run_key,
        "current_task": task_info,
        "progress_percentage": (completed / total * 100) if total else 0
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(status, f, indent=4)

# ------------------------------------------------------------------------------
# Sweep Function
# ------------------------------------------------------------------------------

def sweep(simulator, artworkData, sweepParam, simulatorConfig,
          base_output_dir, outputName,
          enableLayoutGeneration, generateSVG,
          enableSimulation, packSimulationResults,
          force=False):

    sweepPar = list(sweepParam["parameters"].keys())
    sweepData = [get_sweep_values(sweepParam["parameters"][p]) for p in sweepPar]
    permutations = list(itertools.product(*sweepData))

    total_permutations = len(permutations)
    width = max(4, len(str(total_permutations)))

    logger.info("Total number of permutations: %d", total_permutations)

    os.makedirs(base_output_dir, exist_ok=True)

    status_file = os.path.join(base_output_dir, "status.json")
    checkpoint_file = os.path.join(base_output_dir, "checkpoint.json")
    summary_file = os.path.join(base_output_dir, "summary.json")

    checkpoint_db = load_checkpoint_db(checkpoint_file)

    # ------------------------------------------------------------------
    # Summary Tracking
    # ------------------------------------------------------------------

    sweep_start_time = time.time()

    summary_data = {
        "sweep_metadata": {
            "start_time": get_timestamp(),
            "end_time": None,
            "total_sweep_time_seconds": None
        },
        "configuration": {
            "layout_enabled": enableLayoutGeneration,
            "svg_enabled": generateSVG,
            "simulation_enabled": enableSimulation
        },
        "statistics": {
            "total_permutations": total_permutations,
            "completed_runs": 0,
            "layout": {"success": 0, "failed": 0},
            "svg": {"success": 0, "failed": 0},
            "simulation": {"success": 0, "failed": 0}
        }
    }

    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=4)

    RunID = 0
    completedRuns = 0

    for permutation in permutations:

        run_key = f"RunID_{RunID:0{width}d}"
        run_output_dir = os.path.join(base_output_dir, run_key)
        os.makedirs(run_output_dir, exist_ok=True)

        run_artwork = copy.deepcopy(artworkData)

        if outputName:
            run_name = f"{outputName}_{run_key}"
        else:
            run_name = f"{run_artwork['metadata']['name']}_{run_key}"

        run_artwork["metadata"]["name"] = run_name

        logger.info(
            "RunID: %d, Permutation: %s, Run Name: %s",
            RunID, permutation, run_name
        )

        # Update parameters
        for i, param in enumerate(sweepPar):
            run_artwork["parameters"][param] = permutation[i]

        gdsPath = os.path.join(run_output_dir, run_name + ".gds")
        svgPath = os.path.join(run_output_dir, run_name + ".svg")
        sParamPath = os.path.join(run_output_dir, run_name + ".s2p")

        # ----------------------------------------------------------
        # Artwork Generation
        # ----------------------------------------------------------

        needs_layout = enableLayoutGeneration
        needs_svg = generateSVG

        if needs_layout or needs_svg:

            logger.info(
                "Generating artwork for %s (needs_layout: %s, needs_svg: %s)",
                run_key, needs_layout, needs_svg
            )

            command = [
                "python",
                str(artwork_generator_path),
                "-a", json.dumps(run_artwork),
                "-o", run_output_dir,
                "-n", run_name
            ]

            if enableLayoutGeneration:
                command.append("--layout")
            if generateSVG:
                command.append("--svg")

            process = subprocess.run(command)

            if process.returncode == 0:
                logger.info("Artwork generation succeeded for %s", run_key)

                if needs_layout:
                    if os.path.exists(gdsPath):
                        summary_data["statistics"]["layout"]["success"] += 1
                    else:
                        summary_data["statistics"]["layout"]["failed"] += 1

                if needs_svg:
                    if os.path.exists(svgPath):
                        summary_data["statistics"]["svg"]["success"] += 1
                    else:
                        summary_data["statistics"]["svg"]["failed"] += 1
            else:
                logger.error("Artwork generation failed for %s", run_key)

                if needs_layout:
                    summary_data["statistics"]["layout"]["failed"] += 1
                if needs_svg:
                    summary_data["statistics"]["svg"]["failed"] += 1

        # ----------------------------------------------------------
        # Simulation
        # ----------------------------------------------------------

        if enableSimulation and os.path.exists(gdsPath):

            logger.info("Performing EM simulation for %s", run_key)

            command = [
                "python",
                str(simulator_path),
                "-f", gdsPath,
                "-a", json.dumps(run_artwork),
                "--sim", simulator,
                "-o", run_output_dir,
                "-n", run_name
            ]

            process = subprocess.run(command)

            if process.returncode == 0 and os.path.exists(sParamPath):
                logger.info("Simulation succeeded for %s", run_key)
                summary_data["statistics"]["simulation"]["success"] += 1
            else:
                logger.error("Simulation failed for %s", run_key)
                summary_data["statistics"]["simulation"]["failed"] += 1

        completedRuns += 1
        summary_data["statistics"]["completed_runs"] = completedRuns

        with open(summary_file, "w") as f:
            json.dump(summary_data, f, indent=4)

        RunID += 1

    # ------------------------------------------------------------------
    # Finalize Summary
    # ------------------------------------------------------------------

    total_time = time.time() - sweep_start_time
    summary_data["sweep_metadata"]["end_time"] = get_timestamp()
    summary_data["sweep_metadata"]["total_sweep_time_seconds"] = total_time

    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=4)

    logger.info("Sweep completed in %.2f seconds", total_time)

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--artwork", "-a", required=True)
    parser.add_argument("--sweep", required=True)
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--name", "-n")
    parser.add_argument("--layout", action="store_true")
    parser.add_argument("--svg", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--simulator", choices=["emx", "openems", "empro", "raptor"])
    parser.add_argument("--config", "-c", default=None)

    args = parser.parse_args()

    artworkData = load_json_data(args.artwork)
    sweepData = load_json_data(args.sweep)

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
        packSimulationResults=False
    )

if __name__ == "__main__":
    main()