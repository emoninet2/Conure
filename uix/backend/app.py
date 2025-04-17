import logging
import os
import json
import atexit
import signal
import sys
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pathlib import Path
import shutil

# Adjust the path to where your .env file is located:
env_path = Path(__file__).parent / '.env'
load_dotenv(".env")

app = Flask(__name__)
CORS(app)

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
        return f"{timestamp} [BACKEND] {color}{msg}{self.RESET}"


# Global process tracker
SWEEP_PROCESSES = {}





BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../data"))

PROJECT_NAME = None
PROJECT_PATH = None

ARTWORK_FILENAME = 'artwork.json'
GDS_FILENAME = 'artwork.gds'

def convert_frontend_to_backend_artwork(frontend_data):
    """
    Convert frontend artwork data structure into a backend-compatible format.
    """

    def parse_value(value):
        try:
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                value = value.strip()
                # Avoid misclassifying negative numbers like "-1" as expressions
                if any(op in value for op in ['+', '*', '/', '(', ')']) or ('-' in value[1:]):
                    return value  # expression
                # Convert to number if it looks like one
                if '.' in value:
                    return float(value)
                return int(value)
        except Exception:
            return value
        return value



    # Metadata
    metadata_dict = {
        item["parameter"]: item["value"]
        for item in frontend_data.get("metaData", [])
        if item.get("parameter") and item.get("value") is not None
    }
    default_metadata = {
        "name": "",
        "description": "",
        "author": "",
        "date": "",
        "version": ""
    }
    default_metadata.update(metadata_dict)
    metadata_dict = default_metadata

    # Parameters
    parameter_dict = {}
    for item in frontend_data.get("parameterData", []):
        key, val = item.get("parameter"), item.get("value")
        if key and val is not None:
            if isinstance(val, str) and any(op in val for op in ['+', '-', '*', '/', '(', ')']):
                parameter_dict[key] = val
            else:
                parameter_dict[key] = parse_value(val)

    # Layers
    layer_dict = {}
    for layer in frontend_data.get("layerData", []):
        name = layer.get("name")
        if name:
            layer_dict[name] = {
                "gds": {
                    "layer": parse_value(layer.get("gdsLayer")),
                    "datatype": parse_value(layer.get("gdsDatatype"))
                }
            }

    # Vias
    via_dict = {}
    for via in frontend_data.get("viaData", []):
        name = via.get("name")
        if name:
            via_dict[name] = {
                "length": parse_value(via.get("length")),
                "width": parse_value(via.get("width")),
                "spacing": parse_value(via.get("spacing")),
                "angle": parse_value(via.get("angle")),
                "layer": via.get("layer")
            }

    # Segments
    segments_raw = frontend_data.get("segmentData", [])
    segments_dict = {
        f"S{i}": {
            "id": i,
            "group": [
                {
                    "type": item.get("type", "").upper(),
                    "data": {
                        **({
                            "bridge": item["item"]
                        } if item.get("type") == "bridge" else
                        {
                            "arm": item["item"]
                        } if item.get("type") == "port" else {}),
                        **({
                            "jump": parse_value(item["jump"])
                        } if item.get("type") == "bridge" and item.get("jump") not in ("", None) else {}),
                        "layer": item.get("layer", "")
                    }
                } for item in group if item.get("type")
            ]
        } for i, group in enumerate(segments_raw)
    }


    # Ports
    ports_data = {}
    for i, port in enumerate(frontend_data.get("portData", [])):
        ports_data[f"PORT{i}"] = {
            "label": port.get("label", f"P{i}")
        }

    sim_ports = []
    for i, sim in enumerate(frontend_data.get("simPortData", [])):
        sim_ports.append({
            "id": i,
            "type": sim.get("portType", "differential"),
            "plus": sim.get("plusPort"),
            "minus": sim.get("minusPort"),
            "enable": bool(sim.get("enable"))
        })

    ports_dict = {
        "config": {"simulatingPorts": sim_ports},
        "data": ports_data
    }

    # Arms
    arm_dict = {}
    for i, arm in enumerate(frontend_data.get("armData", [])):
        arm_entry = {}
        if arm.get("type"): arm_entry["type"] = arm["type"]
        if arm.get("length") not in ("", None): arm_entry["length"] = parse_value(arm["length"])
        if arm.get("width") not in ("", None): arm_entry["width"] = parse_value(arm["width"])
        if arm.get("spacing") not in ("", None): arm_entry["spacing"] = parse_value(arm["spacing"])
        if arm.get("layer"): arm_entry["layer"] = arm["layer"]
        if arm.get("viaPadStack"): arm_entry["viaStack"] = arm["viaPadStack"]
        if arm.get("port2"):
            arm_entry["port"] = [arm["port1"], arm["port2"]]
        elif arm.get("port1"):
            arm_entry["port"] = arm["port1"]
        arm_dict[f"A{i}"] = arm_entry

    # Via Pad Stack
    via_pad_stack_dict = {}
    for stack in frontend_data.get("viaPadStackData", []):
        name = stack.get("name")
        if name:
            via_list = stack.get("viaList")
            via_pad_stack_dict[name] = {
                "topLayer": stack.get("topLayer"),
                "bottomLayer": stack.get("bottomLayer"),
                "margin": parse_value(stack.get("margin")),
                "vias": via_list.split(",") if isinstance(via_list, str) else via_list
            }

    # Bridges
    bridge_dict = {
        "DEFAULT": {
            "layer": "M9",   # or pull from somewhere dynamic
            "Via": "V0"
        }
    }
    for i, bridge in enumerate(frontend_data.get("bridgeData", [])):
        name = bridge.get("name", f"B{i}")
        bridge_dict[name] = {
            "layer": bridge.get("layer"),
            "via": bridge.get("via"),
            "ViaWidth": parse_value(bridge.get("viaWidth")),
            "ViaStackCCW": bridge.get("viaStackCCW"),
            "ViaStackCW": bridge.get("viaStackCW")
        }
    # Guard Ring
    guard_config = {
        "useGuardRing": frontend_data.get("useGuardRing", False),
    }

    guard_data = frontend_data.get("guardRingData", [])
    guard_segments = {}
    for i, item in enumerate(guard_data):
        name = item.get("name", f"GR{i}")
        if name:
            seg = {
                "shape": item.get("shape"),
                "offset": parse_value(item.get("offset")),
                "layer": item.get("layer")
            }
            if item.get("width") not in (None, ""):
                seg["width"] = parse_value(item["width"])
            if item.get("contacts"):
                seg["contacts"] = {
                    "use": item["contacts"],
                    "viaStack": item.get("viaPadStack")
                }
            if item.get("UsePartialCut"):
                seg["partialCut"] = {
                    "use": True,
                    "segment": item.get("partialCutSegments"),
                    "spacing": item.get("spacing")
                }
            guard_segments[name] = seg

    dummy_fills = {}
    for i, dummy in enumerate(frontend_data.get("guardRingDummyData", [])):
        entry = {}
        if dummy.get("shape"): entry["shape"] = dummy["shape"]
        if dummy.get("length") not in (None, ""): entry["length"] = parse_value(dummy["length"])
        if dummy.get("height") not in (None, ""): entry["height"] = parse_value(dummy["height"])
        if dummy.get("offsetX") not in (None, ""): entry["offsetX"] = parse_value(dummy["offsetX"])
        if dummy.get("offsetY") not in (None, ""): entry["offsetY"] = parse_value(dummy["offsetY"])
        if dummy.get("layers"): entry["layers"] = dummy["layers"]
        dummy_fills[f"rect{i}"] = entry

    guard_ring_dict = {
        "config": guard_config,
        "data": {
            "distance": parse_value(frontend_data.get("guardRingDistance")),
            "segments": guard_segments,
            "dummyFills": {
                "type": "checkered",
                "groupSpacing": 2,
                "items": dummy_fills
            },
            
        }
    }
    # Final output
    return {
        "metadata": metadata_dict,
        "parameters": parameter_dict,
        "layer": layer_dict,
        "via": via_dict,
        "segments": {
            "config": {
                "bridge_extension_aligned": True
            },
            "data": segments_dict
        },
        "arms": arm_dict,
        "ports": ports_dict,
        "bridges": bridge_dict,
        "viaPadStack": via_pad_stack_dict,
        "guardRing": guard_ring_dict
    }


def convert_backend_to_frontend_artwork(backend_data):
    """
    Convert backend artwork data structure into a frontend-compatible format.
    """

    def value_to_str(val):
        if isinstance(val, (int, float)):
            return str(val)
        return val

    # Metadata
    metaData = [
        {"parameter": key, "value": value_to_str(value)}
        for key, value in backend_data.get("metadata", {}).items()
    ]

    # Parameters
    parameterData = [
        {"parameter": key, "value": value_to_str(value)}
        for key, value in backend_data.get("parameters", {}).items()
    ]

    # Layers
    layerData = [
        {
            "name": name,
            "gdsLayer": value["gds"].get("layer"),
            "gdsDatatype": value["gds"].get("datatype")
        }
        for name, value in backend_data.get("layer", {}).items()
    ]

    # Vias
    viaData = [
        {
            "name": name,
            "length": value.get("length"),
            "width": value.get("width"),
            "spacing": value.get("spacing"),
            "angle": value.get("angle"),
            "layer": value.get("layer")
        }
        for name, value in backend_data.get("via", {}).items()
    ]

    # Segments
    segmentData = []
    for segment in backend_data.get("segments", {}).get("data", {}).values():
        group_items = []
        for item in segment.get("group", []):
            item_type = item.get("type", "").lower()
            data = item.get("data", {})
            entry = {
                "type": item_type,
                "layer": data.get("layer", "")
            }

            if item_type == "bridge":
                entry["item"] = data.get("bridge", "")
                entry["jump"] = value_to_str(data.get("jump", ""))
            elif item_type == "port":
                entry["item"] = data.get("arm", "")
            else:
                entry["item"] = ""

            group_items.append(entry)
        segmentData.append(group_items)


    # ✅ FIX: Add `name` to each port
    portData = [
        {"name": key, "label": value["label"]}
        for key, value in backend_data.get("ports", {}).get("data", {}).items()
    ]

    simPortData = [
        {
            "portType": item.get("type"),
            "plusPort": item.get("plus"),
            "minusPort": item.get("minus"),
            "enable": item.get("enable", False)
        }
        for item in backend_data.get("ports", {}).get("config", {}).get("simulatingPorts", [])
    ]

    # Arms
    armData = []
    for key, arm in backend_data.get("arms", {}).items():
        arm_entry = {
            "name": key,  # 👈 FIX HERE
            "type": arm.get("type"),
            "length": value_to_str(arm.get("length")),
            "width": value_to_str(arm.get("width")),
            "spacing": value_to_str(arm.get("spacing")),
            "layer": arm.get("layer"),
            "viaPadStack": arm.get("viaStack")
        }
        port = arm.get("port")
        if isinstance(port, list):
            arm_entry["port1"] = port[0]
            arm_entry["port2"] = port[1]
        else:
            arm_entry["port1"] = port
        armData.append(arm_entry)

    # Via Pad Stack
    viaPadStackData = [
        {
            "name": name,
            "topLayer": value.get("topLayer"),
            "bottomLayer": value.get("bottomLayer"),
            "margin": value_to_str(value.get("margin")),
            "viaList": value.get("vias", [])  # ✅ Fix: Send as a proper array
        }
        for name, value in backend_data.get("viaPadStack", {}).items()
    ]


    # Bridges
    bridgeData = [
        {
            "name": name,
            "layer": value.get("layer"),
            "via": value.get("via"),
            "viaWidth": value.get("ViaWidth"),
            "viaStackCCW": value.get("ViaStackCCW"),
            "viaStackCW": value.get("ViaStackCW")
        }
        for name, value in backend_data.get("bridges", {}).items()
        if name != "DEFAULT"
    ]

    # Guard Ring
    guardRingData = []
    for name, segment in backend_data.get("guardRing", {}).get("data", {}).get("segments", {}).items():
        seg = {
            "name": name,
            "shape": segment.get("shape"),
            "offset": value_to_str(segment.get("offset")),
            "layer": segment.get("layer"),
            "width": value_to_str(segment.get("width")) if "width" in segment else "",
            "contacts": segment.get("contacts", {}).get("use") if segment.get("contacts") else None,
            "viaPadStack": segment.get("contacts", {}).get("viaStack") if segment.get("contacts") else None,
            "UsePartialCut": segment.get("partialCut", {}).get("use") if segment.get("partialCut") else None,
            "partialCutSegments": value_to_str(segment.get("partialCut", {}).get("segment")) if segment.get("partialCut") else None,
            "spacing": value_to_str(segment.get("partialCut", {}).get("spacing")) if segment.get("partialCut") else None
        }
        guardRingData.append(seg)

    guardRingDummyData = [
    {
        "name": key,  # ✅ Add the key as name
        "shape": dummy.get("shape", ""),
        "length": value_to_str(dummy.get("length")),
        "height": value_to_str(dummy.get("height")),
        "offsetX": value_to_str(dummy.get("offsetX")),
        "offsetY": value_to_str(dummy.get("offsetY")),
        "layers": dummy.get("layers")
    }
    for key, dummy in backend_data.get("guardRing", {}).get("data", {}).get("dummyFills", {}).get("items", {}).items()
]

    return {
        "metaData": metaData,
        "parameterData": parameterData,
        "layerData": layerData,
        "viaData": viaData,
        "segmentData": segmentData,
        "portData": portData,  # ✅ with name + label
        "simPortData": simPortData,
        "armData": armData,
        "viaPadStackData": viaPadStackData,
        "bridgeData": bridgeData,
        "guardRingData": guardRingData,
        "guardRingDummyData": guardRingDummyData,
        "useGuardRing": backend_data.get("guardRing", {}).get("config", {}).get("useGuardRing", False),
        "guardRingDistance": backend_data.get("guardRing", {}).get("data", {}).get("distance", "")
    }




@app.route('/api/create_project', methods=['POST'])
def create_project():
    global PROJECT_PATH, PROJECT_NAME
    data = request.get_json()
    PROJECT_NAME = data.get('name')
    PROJECT_PATH = os.path.join(DATA_DIR, PROJECT_NAME)

    try:
        if not os.path.exists(PROJECT_PATH):
            os.makedirs(PROJECT_PATH)
            logging.info(f"Created project directory: {PROJECT_PATH}")
        else:
            logging.info(f"Using existing directory: {PROJECT_PATH}")

        # Create project.json
        project_json = {
            "name": PROJECT_NAME,
            "version": "1.0",
            "lastOpened": datetime.utcnow().isoformat() + "Z"
        }

        with open(os.path.join(PROJECT_PATH, "project.json"), "w") as f:
            json.dump(project_json, f, indent=2)

        response = {
            "success": True,
            "data": {
                "message": f"Project {PROJECT_NAME} created in {PROJECT_PATH}!",
                "projectJson": project_json
            }
        }
        return jsonify(response)

    except PermissionError as e:
        logging.error(f"Permission denied: {e}")
        return jsonify({
            "success": False,
            "error": "Permission denied. Cannot write to the specified directory."
        }), 403

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



@app.route('/api/open_project', methods=['POST'])
def open_project():
    global PROJECT_PATH, PROJECT_NAME
    data = request.get_json()
    PROJECT_NAME = data.get('name')
    PROJECT_PATH = os.path.join(DATA_DIR, PROJECT_NAME)

    try:
        if not os.path.exists(PROJECT_PATH):
            return jsonify({
                "success": False,
                "error": "Specified project path does not exist."
            }), 404

        project_file = os.path.join(PROJECT_PATH, "project.json")

        if os.path.exists(project_file):
            with open(project_file, "r") as f:
                project_data = json.load(f)
                PROJECT_NAME = project_data.get("name", "")
                project_data["lastOpened"] = datetime.utcnow().isoformat() + "Z"
        else:
            # fallback if project.json doesn't exist
            PROJECT_NAME = os.path.basename(PROJECT_PATH)
            project_data = {
                "name": PROJECT_NAME,
                "version": "1.0",
                "lastOpened": datetime.utcnow().isoformat() + "Z"
            }

        # Update project.json with new lastOpened timestamp
        with open(project_file, "w") as f:
            json.dump(project_data, f, indent=2)

        logging.info(f"Project opened at {PROJECT_PATH}")

        return jsonify({
            "success": True,
            "data": {
                "message": f"Project opened at {PROJECT_PATH}!",
                "projectJson": project_data
            }
        })

    except Exception as e:
        logging.exception("Failed to open project.")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



@app.route('/api/save_artwork', methods=['POST'])
def save_artwork():
    global PROJECT_PATH
    logging.info("Triggered /api/save_artwork")

    if not PROJECT_PATH:
        logging.error("Attempted to save artwork without an open project.")
        return jsonify({"success": False, "error": "No project opened"}), 400

    data = request.get_json()
    backend_artwork_data = convert_frontend_to_backend_artwork(data)
    logging.debug("Backend artwork data:\n%s", json.dumps(backend_artwork_data, indent=2))
    logging.info("Saving artwork data...")

    try:
        filepath = os.path.join(PROJECT_PATH, ARTWORK_FILENAME)
        with open(filepath, 'w') as f:
            json.dump(backend_artwork_data, f, indent=2)  # ✅ correct data
        logging.info(f"Artwork saved to {filepath}")
        return jsonify({"success": True, "message": "Artwork saved."})
    except Exception as e:
        logging.exception("Failed to save artwork.")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/api/load_artwork', methods=['GET'])
def load_artwork():
    global PROJECT_PATH
    logging.debug("Triggered /api/load_artwork")

    if not PROJECT_PATH:
        logging.error("Attempted to load artwork without an open project.")
        return jsonify({"success": False, "error": "No project opened"}), 400

    filepath = os.path.join(PROJECT_PATH, ARTWORK_FILENAME)

    if not os.path.exists(filepath):
        logging.warning("No artwork file found, returning empty data.")
        return jsonify({"success": True, "data": {}})

    try:
        # Load backend artwork JSON
        with open(filepath, 'r') as f:
            backend_artwork_data = json.load(f)

        # Convert to frontend format
        frontend_data = convert_backend_to_frontend_artwork(backend_artwork_data)

        logging.info(f"Artwork loaded and converted from {filepath}")
        return jsonify({"success": True, "data": frontend_data})

    except Exception as e:
        logging.exception("Failed to load artwork.")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/upload_artwork', methods=['POST'])
def upload_artwork():
    global PROJECT_PATH

    if not PROJECT_PATH:
        return jsonify({"success": False, "error": "No project opened"}), 400

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(PROJECT_PATH, ARTWORK_FILENAME)

        logging.debug(f"FILE SAVE PATH: {filepath}")

        file.save(filepath)

        return jsonify({"success": True, "message": f"File uploaded and saved as {filename}"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    

@app.route('/api/download_artwork', methods=['GET'])
def download_artwork():
    global PROJECT_PATH
    if not PROJECT_PATH:
        logging.error("Attempted to download artwork without an open project.")
        return jsonify({"success": False, "error": "No project opened"}), 400

    # Build the full file path for the artwork JSON file.
    filepath = os.path.join(PROJECT_PATH, ARTWORK_FILENAME)

    if not os.path.exists(filepath):
        logging.error(f"Artwork file not found: {filepath}")
        return jsonify({"success": False, "error": "Artwork file not found"}), 404

    try:
        # Use Flask's send_file to send the artwork.json file as an attachment.
        return send_file(
            filepath,
            as_attachment=True,
            download_name=ARTWORK_FILENAME,
            mimetype='application/json'
        )
    except Exception as e:
        logging.exception("Failed to download artwork file.")
        return jsonify({"success": False, "error": str(e)}), 500




@app.route('/api/preview_artwork', methods=['POST'])
def preview_artwork():
    global PROJECT_PATH

    if not PROJECT_PATH:
        return jsonify({"success": False, "error": "No project opened"}), 400

    filepath = os.path.join(PROJECT_PATH, ARTWORK_FILENAME)

    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Artwork file not found"}), 404

    try:
        command = [
            'python',
            '../../artwork_generator/artwork_generator.py',
            '-a', filepath,
            '-o', PROJECT_PATH,
            '-n', 'artwork',
            '--layout',
            '--svg'
        ]

        logging.info(f"Running preview generation: {' '.join(command)}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            logging.error("Preview generation failed:\n" + result.stderr)
            return jsonify({"success": False, "error": "Preview generation failed", "details": result.stderr}), 500

        logging.info("Preview generation successful")
        return jsonify({"success": True, "message": "Preview generated successfully!"})

    except Exception as e:
        logging.exception("Failed to generate preview.")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/preview_svg', methods=['GET'])
def get_preview_svg():
    global PROJECT_PATH
    svg_path = os.path.join(PROJECT_PATH, 'artwork.svg')

    if not os.path.exists(svg_path):
        return jsonify({"success": False, "error": "Preview not found"}), 404

    try:
        return send_file(svg_path, mimetype='image/svg+xml')
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download_gdsii', methods=['GET'])
def download_gdsii():
    global PROJECT_PATH
    gds_path = os.path.join(PROJECT_PATH, GDS_FILENAME)

    if not os.path.exists(gds_path):
        return jsonify({"success": False, "error": "GDSII file not found"}), 404

    try:
        return send_file(gds_path, as_attachment=True, download_name=GDS_FILENAME, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



# ========================
# Simulator Configurations
# ========================

from collections import OrderedDict

@app.route('/api/save_emx_config', methods=['POST'])
def save_emx_config():
    global PROJECT_PATH
    logging.info("Triggered /api/save_emx_config")

    if not PROJECT_PATH:
        logging.error("No project opened")
        return jsonify({"success": False, "error": "No project opened"}), 400

    try:
        emx_config = request.get_json()
        if not emx_config:
            return jsonify({"success": False, "error": "No config provided"}), 400

        # Save only simConfig.json with wrapped content
        sim_config_path = os.path.join(PROJECT_PATH, 'simConfig.json')
        wrapped_config = {
            "emx_config": emx_config
        }

        with open(sim_config_path, 'w') as f:
            json.dump(wrapped_config, f, indent=2)
        logging.info(f"✅ Saved EMX config to {sim_config_path}")

        return jsonify({
            "success": True,
            "message": "EMX config saved to simConfig.json successfully."
        })

    except Exception as e:
        logging.exception("Failed to save EMX config.")
        return jsonify({"success": False, "error": str(e)}), 500




@app.route('/api/load_emx_config', methods=['GET'])
def load_emx_config():
    global PROJECT_PATH
    logging.info("Triggered /api/load_emx_config")

    if not PROJECT_PATH:
        logging.error("No project opened")
        return jsonify({"success": False, "error": "No project opened"}), 400

    filepath = os.path.join(PROJECT_PATH, "simConfig.json")

    if not os.path.exists(filepath):
        logging.warning(f"simConfig.json not found at {filepath}")
        return jsonify({"success": True, "data": {}})

    try:
        with open(filepath, "r") as f:
            sim_config = json.load(f, object_pairs_hook=OrderedDict)

        emx_config = sim_config.get("emx_config", {})
        logging.info(f"Loaded EMX config from simConfig.json")


        return app.response_class(
            response=json.dumps({
                "success": True,
                "data": emx_config
            }, indent=2),
            status=200,
            mimetype='application/json'
        )


    except Exception as e:
        logging.exception("Failed to load EMX config from simConfig.")
        return jsonify({"success": False, "error": str(e)}), 500






# ========================
# Simulation
# ========================

import subprocess
import os

@app.route('/api/start_simulation', methods=['POST'])
def start_simulation():
    global PROJECT_PATH
    data = request.get_json()
    simulator = data.get('simulator')

    logging.info(f"Starting simulation for: {simulator}")

    try:
        if not PROJECT_PATH:
            return jsonify({
                "success": False,
                "status": "❌ No project path set. Open a project first."
            }), 400

        if simulator == "EMX":
            logging.info("💻 EMX simulator selected.")

            simulate_script = os.path.abspath(os.path.join(BASE_DIR, '../../simulator/simulator.py'))
            gds_path = os.path.join(PROJECT_PATH, 'artwork.gds')
            config_path = os.path.join(PROJECT_PATH, 'simConfig.json')
            artwork_path = os.path.join(PROJECT_PATH, 'artwork.json')

      
            command = [
                'python', simulate_script,
                '-f', gds_path,
                '--sim', 'emx',
                '-c', config_path,
                '-a', artwork_path,
                '-o', PROJECT_PATH,
                '-n', 'artwork'
            ]

            logging.info(f"Running simulation command: {' '.join(command)}")

            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                logging.error(f"Simulation failed:\n{result.stderr}")
                return jsonify({
                    "success": False,
                    "status": "❌ EMX simulation failed",
                    "error": result.stderr
                }), 500

            logging.info(f"Simulation output:\n{result.stdout}")

        elif simulator == "openEMS":
            logging.info("📡 openEMS simulator selected.")
            # TODO: Insert openEMS logic

        elif simulator == "ANSYS Raptor":
            logging.info("⚡ ANSYS Raptor simulator selected.")
            # TODO: Insert ANSYS Raptor logic

        else:
            return jsonify({
                "success": False,
                "status": f"❌ Unknown simulator: {simulator}"
            }), 400

        return jsonify({
            "success": True,
            "status": f"✅ {simulator} simulation completed successfully."
        })

    except Exception as e:
        logging.exception("Simulation failed to start.")
        return jsonify({
            "success": False,
            "status": f"❌ Failed to start simulation: {str(e)}"
        }), 500



@app.route('/api/stop_simulation', methods=['POST'])
def stop_simulation():
    # TODO: Add logic to stop the running simulation process
    logging.info("Stopping simulation.")
    
    return jsonify({
        "success": True,
        "status": "⏹ Simulation stopped."
    })


# ========================
# Sweep
# ========================

# ========================
# SWEEP ENDPOINTS
# ========================

@app.route('/api/save_sweep', methods=['POST'])
def save_sweep():
    """
    Save sweep data to a folder named with the sweepName in PROJECT_PATH/sweep.
    Expects JSON payload with:
      - sweepName: string indicating the sweep folder name
      - parameters: a JSON object containing the sweep parameters
    The data is saved to a file named "checkpoint.json" inside that folder.
    """
    global PROJECT_PATH
    data = request.get_json()
    sweep_name = data.get("sweepName")
    # Updated to read the key "parameters"
    sweep_params = data.get("parameters")
    
    if not sweep_name or sweep_params is None:
        logging.error("Invalid sweep data provided. 'sweepName' and 'parameters' are required.")
        return jsonify({"success": False, "error": "Invalid sweep data provided"}), 400

    # Build the path: PROJECT_PATH/sweep/sweep_name
    sweep_folder = os.path.join(PROJECT_PATH, "sweep", sweep_name)
    
    # Create the folder if it does not exist
    os.makedirs(sweep_folder, exist_ok=True)
    
    sweep_json_path = os.path.join(sweep_folder, "sweep.json")
    
    # Save the sweep data into checkpoint.json
    try:
        with open(sweep_json_path, "w") as f:
            json.dump({"sweepName": sweep_name, "parameters": sweep_params}, f, indent=2)
        logging.info(f"Sweep saved successfully: {sweep_name}")
        return jsonify({"success": True, "message": "Sweep saved successfully."})
    except Exception as e:
        logging.exception("Failed to save sweep data.")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/load_sweep', methods=['GET'])
def load_sweep():
    """
    Load sweep data by sweep name from PROJECT_PATH/sweep.
    Expects a query parameter 'sweepName'.
    Returns the parsed data from sweep.json.
    """
    global PROJECT_PATH
    sweep_name = request.args.get('sweepName')
    
    if not sweep_name:
        logging.error("No sweep name provided in request.")
        return jsonify({"success": False, "error": "No sweep name provided"}), 400
    
    sweep_folder = os.path.join(PROJECT_PATH, "sweep", sweep_name)
    sweep_file = os.path.join(sweep_folder, "sweep.json")
    
    if not os.path.exists(sweep_file):
        logging.error(f"sweep.json not found for sweep: {sweep_name}")
        return jsonify({"success": False, "error": "Sweep not found"}), 404
    
    try:
        with open(sweep_file, "r") as f:
            sweep_data = json.load(f)
        logging.info(f"Sweep loaded successfully: {sweep_name}")
        return jsonify({"success": True, "sweep": sweep_data})
    except Exception as e:
        logging.exception("Failed to load sweep data.")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/list_sweeps', methods=['GET'])
def list_sweeps():
    """
    List all sweep folders in PROJECT_PATH/sweep that contain a checkpoint.json file.
    Returns a JSON object with the sweep names.
    """
    global PROJECT_PATH
    sweep_dir = os.path.join(PROJECT_PATH, "sweep")
    sweeps_info = []

    if not os.path.exists(sweep_dir):
        logging.error(f"Sweep directory not found: {sweep_dir}")
        return jsonify({"data_dir": DATA_DIR, "success": False, "error": "Sweep directory not found"}), 404

    for folder in os.listdir(sweep_dir):
        folder_path = os.path.join(sweep_dir, folder)
        if os.path.isdir(folder_path):
            #checkpoint_path = os.path.join(folder_path, "checkpoint.json")
            #if os.path.exists(checkpoint_path):
            sweeps_info.append({
                "sweep_name": folder,
                    # Optionally: "checkpoint": checkpoint_data
               })
            #else:
            #    logging.warning(f"No checkpoint.json found in {folder_path}. Skipping this folder.")
    return jsonify({"success": True, "sweeps": sweeps_info})

@app.route('/api/delete_sweep', methods=['POST'])
def delete_sweep():
    """
    Delete a sweep folder from PROJECT_PATH/sweep.
    Expects a JSON payload with a key "sweep_name" indicating the folder name.
    """
    global PROJECT_PATH
    data = request.get_json()
    sweep_name = data.get("sweep_name")
    
    if not sweep_name:
        logging.error("No sweep name specified in request.")
        return jsonify({"success": False, "error": "No sweep name specified"}), 400

    folder_path = os.path.join(PROJECT_PATH, "sweep", sweep_name)
    
    if not os.path.isdir(folder_path):
        logging.error(f"Sweep folder not found: {folder_path}")
        return jsonify({"success": False, "error": "Sweep folder not found"}), 404

    try:
        shutil.rmtree(folder_path)
        logging.info(f"Sweep folder deleted: {folder_path}")
        return jsonify({"success": True, "message": f"Sweep folder '{sweep_name}' deleted successfully."})
    except Exception as e:
        logging.exception("Failed to delete sweep folder.")
        return jsonify({"success": False, "error": str(e)}), 500

from subprocess import Popen

@app.route('/api/start_sweep', methods=['POST'])
def start_sweep():
    global PROJECT_PATH, SWEEP_PROCESSES
    data = request.get_json()

    sweep_name = data.get("sweepName")
    enable_layout = data.get("enableLayout", False)
    enable_svg = data.get("enableSvg", False)
    enable_simulation = data.get("enableSimulation", False)
    simulator = data.get("simulator", None)
    force_overwrite = data.get("forceOverwrite", False)

    if not sweep_name:
        return jsonify({"success": False, "error": "Missing sweep name"}), 400

    try:
        sweep_script = os.path.abspath(os.path.join(BASE_DIR, '../../sweep/sweep.py'))
        sweep_folder = os.path.join(PROJECT_PATH, "sweep", sweep_name)
        os.makedirs(sweep_folder, exist_ok=True)

        command = [
            "python", sweep_script,
            "-a", os.path.join(PROJECT_PATH, "artwork.json"),
            "--sweep", os.path.join(sweep_folder, "sweep.json"),
            "--output", sweep_folder
        ]
        if enable_layout:
            command.append("--layout")
        if enable_svg:
            command.append("--svg")
        if enable_simulation:
            config_path = os.path.join(PROJECT_PATH, "simConfig.json")
            command.extend(["--simulate", "-c", config_path])
            if simulator:
                command.extend(["--sim", "emx"])
        if force_overwrite:
            command.append("--force")

        command.append("--verbose")

        logging.info(f"Launching sweep process: {' '.join(command)}")

        process = Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        SWEEP_PROCESSES[sweep_name] = process

        
        return jsonify({"success": True, "status": f"🚀 Sweep '{sweep_name}' started.", "pid": process.pid})

    except Exception as e:
        logging.exception("Failed to start sweep.")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/api/stop_sweep', methods=['POST'])
def stop_sweep():
    global SWEEP_PROCESSES

    data = request.get_json()
    sweep_name = data.get("sweepName")

    if not sweep_name:
        return jsonify({"success": False, "error": "Missing sweep name"}), 400

    process = SWEEP_PROCESSES.get(sweep_name)

    if not process:
        return jsonify({"success": False, "status": f"No active sweep found for '{sweep_name}'."}), 404

    try:
        if process.poll() is None:  # Still running
            process.terminate()
            process.wait(timeout=5)
            SWEEP_PROCESSES.pop(sweep_name, None)
            logging.info(f"Sweep '{sweep_name}' terminated.")
            return jsonify({"success": True, "status": f"🛑 Sweep '{sweep_name}' terminated."})
        else:
            SWEEP_PROCESSES.pop(sweep_name, None)
            return jsonify({"success": False, "status": f"Sweep '{sweep_name}' had already completed."})
    except Exception as e:
        logging.exception("Failed to stop sweep process.")
        return jsonify({"success": False, "error": f"Failed to stop sweep: {str(e)}"}), 500


@app.route('/api/sweep_status', methods=['GET'])
def sweep_status():
    global PROJECT_PATH
    sweep_name = request.args.get("sweep_name")

    if not sweep_name:
        return jsonify({"success": False, "error": "Missing sweep name"}), 400

    status_file = os.path.join(PROJECT_PATH, "sweep", sweep_name, "status.json")

    if not os.path.exists(status_file):
        return jsonify({"success": False, "status": "⏳ No status file found yet."}), 404

    try:
        with open(status_file, 'r') as f:
            status_content = f.read().strip()
        return jsonify({"success": True, "status": status_content})
    except Exception as e:
        logging.exception("Failed to read sweep status file.")
        return jsonify({"success": False, "error": f"Failed to read status: {str(e)}"}), 500





# ========================
# Entry Point
# ========================
# if __name__ == '__main__':
#     logging.basicConfig(
#         level=logging.DEBUG,
#         format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
#     )
#     port = int(os.environ.get("VITE_BACKEND_PORT", 5005))
#     logging.info(f"Starting Flask server on port {port}...")
#     app.run(debug=True, port=port, use_reloader=True)

# if __name__ == '__main__':
#     logging.basicConfig(
#         level=logging.DEBUG,
#         format='[%(asctime)s][BACKEND] %(levelname)s in %(module)s: %(message)s'
#     )
#     port = int(os.environ.get("VITE_BACKEND_PORT", 5000))
#     logging.info(f"Starting Flask server on port {port}...")
#     app.run(debug=True, port=port, use_reloader=True)

if __name__ == '__main__':
    # Clear any default handlers
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Change as needed: DEBUG, INFO, etc.

    # Only add handler if not already added (important for reloader)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ColorFormatter('%(levelname)s - %(message)s'))
        logger.addHandler(handler)

    port = int(os.environ.get("VITE_BACKEND_PORT", 5000))
    logging.info(f"Starting Flask server on port {port}...")
    #app.run(debug=True, port=port, use_reloader=True)
    app.run(host='0.0.0.0', debug=True, port=port, use_reloader=True)

