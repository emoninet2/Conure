#!/usr/bin/env python3
"""
Refactored sweep.py for artwork generation and simulation using .env configuration with checkpointing.
This script loads environment variables from the .env file (located in the project root, e.g., /conure)
and builds relative paths for:
  - CONURE_PATH
  - CONURE_ARTWORK_GENERATOR_PATH
  - CONURE_SWEEP_PATH
  - CONURE_SIMULATOR_PATH

It then uses these paths when invoking the artwork generator and simulator.
A persistent JSON database (checkpoint.json) is maintained to track each run's progress so that
if simulation is interrupted, it can resume from the last completed run.
The status.json file now provides detailed, structured information.
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
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# Load .env and Build Relative Paths
# ------------------------------------------------------------------------------

# Assume this file is in conure/sweep/ and the .env file is in conure/.
project_root = Path(__file__).resolve().parents[1]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Get environment variable values and build full paths.
conure_path_env = os.getenv("CONURE_PATH")
if not conure_path_env:
    raise ValueError("CONURE_PATH is not set in the .env file!")
conure_path = (project_root / conure_path_env).resolve()

artwork_generator_rel = os.getenv("CONURE_ARTWORK_GENERATOR_PATH")
if not artwork_generator_rel:
    raise ValueError("CONURE_ARTWORK_GENERATOR_PATH is not set in the .env file!")
artwork_generator_path = (conure_path / artwork_generator_rel).resolve()

sweep_rel = os.getenv("CONURE_SWEEP_PATH")
if not sweep_rel:
    raise ValueError("CONURE_SWEEP_PATH is not set in the .env file!")
sweep_path = (conure_path / sweep_rel).resolve()

simulator_rel = os.getenv("CONURE_SIMULATOR_PATH")
if not simulator_rel:
    raise ValueError("CONURE_SIMULATOR_PATH is not set in the .env file!")
simulator_path = (conure_path / simulator_rel).resolve()

# ------------------------------------------------------------------------------
# Initialize Logging
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

def load_json_data(input_arg):
    """
    Load JSON data either from a direct JSON string or from a file.
    """
    try:
        return json.loads(input_arg)
    except json.JSONDecodeError:
        try:
            with open(input_arg, "r") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            logger.error("File '%s' not found.", input_arg)
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error("File '%s' does not contain valid JSON.", input_arg)
            sys.exit(1)

def get_timestamp():
    """Return the current time in ISO 8601 format."""
    return datetime.now().isoformat()

# ------------------------------------------------------------------------------
# Checkpoint Database Functions
# ------------------------------------------------------------------------------

def load_checkpoint_db(checkpoint_path):
    """Load the checkpoint JSON database if it exists; otherwise, return a new dictionary."""
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r") as f:
                data = f.read().strip()
                if not data:
                    return {"runs": {}}
                return json.loads(data)
        except json.JSONDecodeError:
            logger.warning("Checkpoint file %s is empty or corrupted. Resetting checkpoint database.", checkpoint_path)
            return {"runs": {}}
    else:
        return {"runs": {}}

def save_checkpoint_db(db, checkpoint_path):
    """Save the checkpoint database dictionary to disk."""
    with open(checkpoint_path, "w") as f:
        json.dump(db, f, indent=4)

def update_checkpoint(run_key, checkpoint_db, checkpoint_path, updates):
    """Update the record for a given run and save the checkpoint DB."""
    run_record = checkpoint_db.get("runs", {}).get(run_key, {})
    run_record.update(updates)
    checkpoint_db.setdefault("runs", {})[run_key] = run_record
    save_checkpoint_db(checkpoint_db, checkpoint_path)

# ------------------------------------------------------------------------------
# Status Update Function (Enhanced)
# ------------------------------------------------------------------------------

def update_status(status_file_path, total, completed, run_key, task_info):
    """
    Update the status file with detailed structured information.
    task_info should be a dict with keys for "layout", "svg", and "simulation".
    Each should be a dict containing at least a "status" key and optionally "last_updated".
    Also computes progress_percentage as completed/total * 100.
    """
    progress_percentage = (completed / total) * 100 if total > 0 else 0
    status = {
        "total_permutations": total,
        "completed_runs": completed,
        "current_run": run_key,
        "current_task": task_info,
        "progress_percentage": progress_percentage
    }
    # Ensure the parent directory exists:
    os.makedirs(os.path.dirname(status_file_path), exist_ok=True)
    with open(status_file_path, "w") as status_file:
        json.dump(status, status_file, indent=4)


# ------------------------------------------------------------------------------
# Sweep Function with Checkpointing and Enhanced Status Reporting
# ------------------------------------------------------------------------------

def sweep(simulator, artworkData, sweepParam, simulatorConfig, base_output_dir, outputName,
          enableLayoutGeneration, generateSVG, enableSimulation, packSimulationResults):
    """
    Sweep over a set of parameters to generate artwork layouts and optionally run simulations.
    Each run output is placed in a unique subdirectory under base_output_dir and tracked in a 
    checkpoint JSON file, so that interrupted runs can be resumed.
    Detailed status is written to a JSON file indicating what is currently happening.
    """
    sweepPar = list(sweepParam["parameters"].keys())
    sweepData = [sweepParam["parameters"][param] for param in sweepPar]
    permutations = list(itertools.product(*sweepData))
    total_permutations = len(permutations)
    # Compute the required width based on the total number of iterations.
    width = max(4, len(str(total_permutations)))
    logger.info("Total number of permutations: %d", total_permutations)
    
    status_file_path = os.path.join(base_output_dir, "status.json")
    checkpoint_file_path = os.path.join(base_output_dir, "checkpoint.json")
    checkpoint_db = load_checkpoint_db(checkpoint_file_path)
    
    RunID = 0
    completedRuns = 0
    
    # Initially, set all task statuses to "pending"
    default_task_status = {
        "layout": {"status": "pending"},
        "svg": {"status": "pending"},
        "simulation": {"status": "pending"}
    }
    update_status(status_file_path, total_permutations, completedRuns, "N/A", default_task_status)
    
    for permutation in permutations:
        #run_key = "RunID_{:04d}".format(RunID)
        run_key = f"RunID_{RunID:0{width}d}"
        run_record = checkpoint_db.get("runs", {}).get(run_key, {})
        layout_done = run_record.get("layout_completed", False)
        svg_done = run_record.get("svg_completed", False)
        simulation_done = run_record.get("simulation_completed", False)
        
        # For simulation, skip if already done.
        if enableSimulation and simulation_done:
            logger.info("Simulation for %s already completed. Skipping simulation step.", run_key)
        
        run_artwork = copy.deepcopy(artworkData)
        run_output_dir = os.path.join(base_output_dir, run_key)
        os.makedirs(run_output_dir, exist_ok=True)
        
        if outputName is None:
            run_name = run_artwork["metadata"]["name"] + "_" + run_key
        else:
            run_name = outputName + "_" + run_key
        run_artwork["metadata"]["name"] = run_name
        
        logger.info("RunID: %d, Permutation: %s, Run Name: %s", RunID, permutation, run_name)
        
        run_parameters_json_path = os.path.join(run_output_dir, "parameters.json")
        if not os.path.exists(run_parameters_json_path):
            runData = {"runID": RunID, "parameters": {}}
            for i, param in enumerate(sweepPar):
                run_artwork["parameters"][param] = permutation[i]
                runData["parameters"][param] = permutation[i]
            runData["parameters"]["rings"] = run_artwork["parameters"].get("rings", None)
            with open(run_parameters_json_path, "w") as parfile:
                json.dump(runData, parfile, indent=4)
            update_checkpoint(run_key, checkpoint_db, checkpoint_file_path, {"parameters": runData["parameters"],
                                                                              "run_name": run_name})
        
        # >>> Save the complete artwork JSON to a file for this iteration <<<
        artwork_json_path = os.path.join(run_output_dir, run_name + "_artwork.json")
        with open(artwork_json_path, "w") as f:
            json.dump(run_artwork, f, indent=4)

        portCount = len(run_artwork["ports"]["config"].get("simulatingPorts", []))
        gdsPath = os.path.join(run_output_dir, run_name + ".gds")
        svgPath = os.path.join(run_output_dir, run_name + ".svg")
        sParamPath = os.path.join(run_output_dir, run_name + f".s{portCount}p")
        
        # Determine if artwork needs to be generated.
        needs_layout = (enableLayoutGeneration or enableSimulation) and not os.path.exists(gdsPath)
        needs_svg = generateSVG and not os.path.exists(svgPath)
        
        if needs_layout or needs_svg:
            # Set current task status accordingly.
            task_status = {
                "layout": {"status": "in progress", "last_updated": get_timestamp()} if needs_layout else {"status": "completed"},
                "svg": {"status": "in progress", "last_updated": get_timestamp()} if needs_svg else {"status": "completed"},
                "simulation": {"status": "pending"}
            }
            update_status(status_file_path, total_permutations, completedRuns, run_key, task_status)
            
            logger.info("Generating artwork for %s (needs_layout: %s, needs_svg: %s)", run_key, needs_layout, needs_svg)
            command = [
                "python",
                str(artwork_generator_path),
                "-a", json.dumps(run_artwork),
                "-o", run_output_dir,
                "-n", run_name,
            ]
            if enableLayoutGeneration:
                command.append("--layout")
            if generateSVG:
                command.append("--svg")
            
            logger.debug("Running artwork generation command: %s", command)
            process = subprocess.run(command)
            if process.returncode == 0:
                logger.info("Artwork generation succeeded for %s", run_key)
                if needs_layout:
                    update_checkpoint(run_key, checkpoint_db, checkpoint_file_path,
                                      {"layout_completed": os.path.exists(gdsPath)})
                if needs_svg:
                    update_checkpoint(run_key, checkpoint_db, checkpoint_file_path,
                                      {"svg_completed": os.path.exists(svgPath)})
            else:
                logger.error("Artwork generation failed for %s with code %d", run_key, process.returncode)
                if needs_layout:
                    update_checkpoint(run_key, checkpoint_db, checkpoint_file_path,
                                      {"layout_completed": False})
                if needs_svg:
                    update_checkpoint(run_key, checkpoint_db, checkpoint_file_path,
                                      {"svg_completed": False})
        
        # Simulation step.
        if enableSimulation and os.path.exists(gdsPath) and not os.path.exists(sParamPath):
            task_status = {
                "layout": {"status": "completed"},
                "svg": {"status": "completed" if os.path.exists(svgPath) else "pending"},
                "simulation": {"status": "in progress", "last_updated": get_timestamp()}
            }
            update_status(status_file_path, total_permutations, completedRuns, run_key, task_status)
            logger.info("Performing EM simulation for %s", run_key)
            
            command = [
                "python",
                str(simulator_path),
                "-f", gdsPath,
                "-a", json.dumps(run_artwork),
                "-c", simulatorConfig if simulatorConfig else "",
                "--sim", simulator,
                "-o", run_output_dir,
                "-n", run_name
            ]
            command = [arg for arg in command if arg]
            logger.debug("Running simulation command: %s", command)
            process = subprocess.run(command)
            if process.returncode == 0:
                logger.info("Simulation succeeded for %s", run_key)
                if os.path.exists(sParamPath):
                    update_checkpoint(run_key, checkpoint_db, checkpoint_file_path, {"simulation_completed": True})
                else:
                    update_checkpoint(run_key, checkpoint_db, checkpoint_file_path, {"simulation_completed": False})
            else:
                logger.error("Simulation failed for %s with code %d", run_key, process.returncode)
                update_checkpoint(run_key, checkpoint_db, checkpoint_file_path, {"simulation_completed": False})
        
        completedRuns += 1
        # At end of run, update status to show idle.
        task_status = {
            "layout": {"status": "completed"},
            "svg": {"status": "completed" if os.path.exists(svgPath) else "pending"},
            "simulation": {"status": "completed" if os.path.exists(sParamPath) else "pending"}
        }
        update_status(status_file_path, total_permutations, completedRuns, run_key, task_status)
        RunID += 1

    # Optionally, pack simulation results.
    if packSimulationResults:
        logger.info("Packing simulation results from base output: %s", base_output_dir)
        pack_simulation_data(base_output_dir)

# ------------------------------------------------------------------------------
# Pack Function (for Touchstone Files Only)
# ------------------------------------------------------------------------------

def pack_simulation_data(sweep_dir):
    """
    Gather simulation run parameters and S-parameter data from touchstone files,
    then pack them into a compressed NPZ file.
    If no touchstone files are found, this function does nothing.
    """
    logger.info("Packing simulation results from directory: %s", sweep_dir)
    features_list = []
    targets_list = []
    feature_names = None
    target_names = None
    frequency_points = None
    
    for run_folder in os.listdir(sweep_dir):
        if run_folder.startswith('RunID'):
            run_path = os.path.join(sweep_dir, run_folder)
            parameters_path = os.path.join(run_path, 'parameters.json')
            if not os.path.exists(parameters_path):
                continue
            with open(parameters_path, 'r') as param_file:
                params = json.load(param_file)
                params_values = list(params['parameters'].values())
                if feature_names is None:
                    feature_names = list(params['parameters'].keys())
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
        logger.info("No touchstone files found. Skipping packing operation.")
        return

    features_array = np.array(features_list)
    targets_array = np.array(targets_list)
    output_npz_path = os.path.join(sweep_dir, 'simulation_data.npz')
    np.savez(output_npz_path,
             features=features_array,
             targets=targets_array,
             feature_names=feature_names,
             target_names=target_names,
             frequency_points=frequency_points)
    logger.info("Packed simulation results saved to: %s", output_npz_path)

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sweep script for artwork generation and simulation using .env paths with checkpointing."
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--artwork", "-a", required=True, help="JSON data or file path for artwork")
    parser.add_argument("--sweep", required=True, help="JSON file path for sweep parameters")
    parser.add_argument("--output", "-o", required=True, help="Base output directory")
    parser.add_argument("--name", "-n", help="Output file base name")
    parser.add_argument("--layout", action="store_true", help="Enable layout generation in GDSII")
    parser.add_argument("--svg", action="store_true", help="Enable SVG generation")
    parser.add_argument("--simulate", action="store_true", help="Enable simulation")
    parser.add_argument("--pack", action="store_true", help="Package simulation results")
    parser.add_argument("--simulator", "--sim", choices=["emx", "openems", "empro"], help="Choose a simulator")
    parser.add_argument("--config", "-c", help="Simulator configuration file", default=None)
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    artworkData = load_json_data(args.artwork)
    sweepData = load_json_data(args.sweep)
    config = load_json_data(args.config) if args.config else None
    
    sweep(args.simulator, artworkData, sweepData, args.config,
          args.output, args.name,
          enableLayoutGeneration=args.layout,
          generateSVG=args.svg,
          enableSimulation=args.simulate,
          packSimulationResults=args.pack)

if __name__ == "__main__":
    main()
