#!/usr/bin/env python3

import argparse
import copy
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import ANN
import CAT
import GPR
import PCE
import PR
import RF
import SVR
import XGB

# Supported modules mapping
MODEL_MODULES = {
    "ANN": ANN,
    "GPR": GPR,
    "PCE": PCE,
    "CAT": CAT,
    "CATBOOST": CAT,
    "XGB": XGB,
    "RF": RF,
    "RANDOMFOREST": RF,
    "PR": PR,
    "SVR": SVR,
}

# ----------------------------------------------------------
# Input loading
# ----------------------------------------------------------
def load_json_input(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        raise TypeError("Expected dict, list, JSON string, or JSON file path.")
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as f:
            return json.load(f)
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError("Input is neither a valid JSON file path nor valid JSON content.") from e

def _extract_payload_and_optional_metadata(payload: Any) -> Tuple[Any, Optional[dict]]:
    if isinstance(payload, dict):
        for key in ("X", "x", "inputs", "features", "data", "x_input"):
            if key in payload:
                return payload[key], payload
    return payload, None

def load_predict_input(x_input: str) -> Tuple[np.ndarray, Optional[dict]]:
    if not isinstance(x_input, str):
        raise TypeError("--x-input must be a path or raw JSON string.")
    if os.path.isfile(x_input):
        lower = x_input.lower()
        if lower.endswith(".npy"):
            return np.load(x_input), None
        if lower.endswith(".json"):
            payload = load_json_input(x_input)
            extracted, wrapper = _extract_payload_and_optional_metadata(payload)
            return np.asarray(extracted, dtype=np.float32), wrapper
        raise ValueError("Supported input file types for --x-input are .npy and .json")
    payload = load_json_input(x_input)
    extracted, wrapper = _extract_payload_and_optional_metadata(payload)
    return np.asarray(extracted, dtype=np.float32), wrapper

# ----------------------------------------------------------
# Metadata loading
# ----------------------------------------------------------
def _load_json_file(path: str) -> Optional[dict]:
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_prediction_metadata(model_dir: str) -> Optional[dict]:
    report_path = os.path.join(model_dir, "report.json")
    report_data = _load_json_file(report_path)
    if isinstance(report_data, dict):
        artifact_meta = report_data.get("artifact_metadata") or {}
        tm = artifact_meta.get("translation_metadata")
        if isinstance(tm, dict):
            return {"source": "report.json", "translation_metadata": tm, "report": report_data}
    
    legacy_path = os.path.join(model_dir, "translation_metadata.json")
    legacy_data = _load_json_file(legacy_path)
    if isinstance(legacy_data, dict):
        tm = legacy_data.get("translation_metadata") if isinstance(legacy_data.get("translation_metadata"), dict) else legacy_data
        return {"source": "translation_metadata.json", "translation_metadata": tm}
    return None

# ----------------------------------------------------------
# Helpers & Reshaping
# ----------------------------------------------------------
def get_model_module(model_type: str):
    key = str(model_type).strip().upper()
    if key not in MODEL_MODULES:
        raise ValueError(f"Unsupported model_type '{model_type}'. Supported: {list(MODEL_MODULES.keys())}")
    return MODEL_MODULES[key]

def ensure_2d_samples(X_new: Any, metadata: Optional[dict] = None) -> np.ndarray:
    arr = np.asarray(X_new, dtype=np.float32)
    if arr.ndim == 0:
        raise ValueError("Prediction input must have at least one dimension.")
    if arr.ndim == 1:
        return arr.reshape(1, -1)
    return arr

def _to_serializable(value: Any) -> Any:
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, (np.integer, np.floating)): return value.item()
    return value

def _reshape_if_possible(pred: Any, tm: dict) -> Tuple[np.ndarray, bool]:
    pred_arr = np.asarray(pred)
    shape = tm.get("original_output_shape_per_sample")
    if not shape: return pred_arr, False
    
    target_width = int(np.prod(shape))
    if pred_arr.ndim == 1: pred_arr = pred_arr.reshape(1, -1)
    if pred_arr.shape[1] != target_width: return pred_arr, False
    
    return pred_arr.reshape((pred_arr.shape[0], *shape)), True

def maybe_group_rows(pred: Any, tm: dict) -> Tuple[Optional[np.ndarray], bool]:
    shape = tm.get("grouped_output_shape_per_original_sample")
    if not shape: return None, False
    arr = np.asarray(pred)
    if arr.ndim == 1: arr = arr.reshape(1, -1)
    rows, cols = shape[0], (shape[1] if len(shape) > 1 else 1)
    if arr.shape[1] == cols and arr.shape[0] % rows == 0:
        return arr.reshape(arr.shape[0] // rows, rows, cols), True
    return None, False

def build_named_predictions(structured_pred: Any, tm: dict, mode: str) -> List[Optional[dict]]:
    names, freqs = tm.get("target_names") or [], tm.get("frequency_points") or []
    arr = np.asarray(structured_pred)
    results = []
    for sample in arr:
        named = None
        if sample.ndim == 1 and len(names) == len(sample):
            named = {str(n): _to_serializable(v) for n, v in zip(names, sample)}
        elif sample.ndim == 2 and mode != "explicit_frequency":
            # Orientation check: (targets, freqs) or (freqs, targets)
            if sample.shape[0] == len(names) and sample.shape[1] == len(freqs):
                oriented = sample
            elif sample.shape[1] == len(names) and sample.shape[0] == len(freqs):
                oriented = sample.T
            else: oriented = None
            if oriented is not None:
                named = {str(n): {"frequency_points": _to_serializable(freqs), "values": _to_serializable(oriented[i])} 
                         for i, n in enumerate(names)}
        results.append(named)
    return results

def infer_prediction_mode(X_new: Any, tm: dict) -> str:
    arr = np.asarray(X_new)
    if arr.ndim == 1: arr = arr.reshape(1, -1)
    feat_names = [str(n).lower() for n in (tm.get("feature_names") or [])]
    if "frequency" not in feat_names: return "standard"
    
    width, count = arr.shape[1], len(feat_names)
    if width == count: return "explicit_frequency"
    if width == count - 1: return "frequency_sweep"
    return "standard"

# ----------------------------------------------------------
# Prediction Core
# ----------------------------------------------------------
def predict_model(model_dir: str, X_new: Any, manual_model_type: Optional[str] = None):
    """
    Unified entry point. Automatically detects model type from report.json.
    Handles denormalization (via model module) and reshaping (via metadata).
    """
    model_type = manual_model_type
    
    # 1. Auto-detect model type if not provided
    if not model_type:
        report = _load_json_file(os.path.join(model_dir, "report.json"))
        if report:
            model_type = report.get("model_info", {}).get("model_type")
    
    if not model_type:
        raise ValueError(f"Could not determine model_type for {model_dir}. Provide -t manually.")

    # 2. Run module-specific prediction (Includes Inverse Scaling/Denormalization)
    module = get_model_module(model_type)
    pred = module.predict(model_dir, X_new)

    # 3. Reshape using metadata
    meta_wrapper = load_prediction_metadata(model_dir)
    if meta_wrapper:
        tm = meta_wrapper.get("translation_metadata") or {}
        reshaped, was_reshaped = _reshape_if_possible(pred, tm)
        return reshaped if was_reshaped else pred
    
    return pred

# ----------------------------------------------------------
# CLI Entry
# ----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Predict using trained surrogate model")
    parser.add_argument("-m", "--model-dir", required=True, help="Path to model directory")
    parser.add_argument("-x", "--x-input", required=True, help="Input data (.npy, .json, or raw string)")
    parser.add_argument("-t", "--model-type", required=False, help="Optional: Override auto-detected model type")
    parser.add_argument("-o", "--output-file", help="Path to save output JSON")
    parser.add_argument("-p", "--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--flat-only", action="store_true", help="Return raw flat results only")
    args = parser.parse_args()

    # Load data and metadata
    X_raw, wrapper = load_predict_input(args.x_input)
    meta_wrap = load_prediction_metadata(args.model_dir)
    X_ready = ensure_2d_samples(X_raw, meta_wrap)

    # Predict
    pred = predict_model(args.model_dir, X_ready, manual_model_type=args.model_type)
    pred_arr = np.asarray(pred)

    # Format Output
    if args.flat_only or meta_wrap is None:
        pred_out = {"prediction": _to_serializable(pred_arr)}
    else:
        tm = meta_wrap["translation_metadata"]
        mode = infer_prediction_mode(X_ready, tm)
        
        # We call reshape again here for the JSON structure building
        struct_pred, was_reshaped = _reshape_if_possible(pred_arr, tm)
        grouped_pred, was_grouped = maybe_group_rows(pred_arr, tm)

        pred_out = {
            "prediction_flat": _to_serializable(pred_arr),
            "mode": mode,
            "metadata_source": meta_wrap.get("source")
        }

        if was_reshaped:
            pred_out["prediction_structured"] = _to_serializable(struct_pred)
            named = build_named_predictions(struct_pred, tm, mode)
            if any(n is not None for n in named):
                pred_out["prediction_named"] = named
        
        if was_grouped and mode != "explicit_frequency":
            pred_out["prediction_grouped"] = _to_serializable(grouped_pred)

    # Output
    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump(pred_out, f, indent=2 if args.pretty else None)
    else:
        print(json.dumps(pred_out, indent=2 if args.pretty else None))

if __name__ == "__main__":
    main()