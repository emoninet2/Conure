from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

PROJECT_PATH = None
PROJECT_NAME = None
ARTWORK_FILENAME = 'artwork.json'

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
    PROJECT_PATH = data.get('location')

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
    global PROJECT_PATH
    data = request.get_json()
    PROJECT_PATH = data.get('location')

    logging.info(f"Project opened at {PROJECT_PATH}")

    response = {
        "success": True,
        "data": {
            "message": f"Project opened at {PROJECT_PATH}!"
        }
    }
    return jsonify(response)


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



# ========================
# Entry Point
# ========================
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    logging.info("Starting Flask server on port 5000...")
    app.run(debug=True, port=5000, use_reloader=True)

