#!/usr/bin/env python3

import os
import sys
import json
import argparse
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import ANN
import GPR
import PCE
import CAT
import XGB
import RF
import PR
import SVR


# ==========================================================
# CLI FLAG DEFINITIONS
# ==========================================================
CLI = {
    "model_type": ("-t", "--model-type"),
    "model_dir": ("-m", "--model-dir"),
    "x_input": ("-x", "--x-input"),
    "output_file": ("-o", "--output-file"),
    "pretty": ("-p", "--pretty"),
}


# ==========================================================
# MODEL DISPATCH
# ==========================================================
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


# ==========================================================
# LOADERS
# ==========================================================
def load_json_input(value):
    """
    Load JSON from:
    - dict / list
    - JSON string
    - path to JSON file
    """
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
        raise ValueError(
            "Input is neither a valid JSON file path nor valid JSON content."
        ) from e


def load_predict_input(x_input):
    """
    Load X_new from:
    - .npy file
    - .json file
    - raw JSON string
    """
    if not isinstance(x_input, str):
        raise TypeError("--x-input must be a path or raw JSON string.")

    if os.path.isfile(x_input):
        lower = x_input.lower()

        if lower.endswith(".npy"):
            return np.load(x_input)

        if lower.endswith(".json"):
            return np.asarray(load_json_input(x_input))

        raise ValueError("Supported input file types for --x-input are .npy and .json")

    return np.asarray(load_json_input(x_input))


# ==========================================================
# HELPERS
# ==========================================================
def get_model_module(model_type):
    model_type_key = str(model_type).strip().upper()

    if model_type_key not in MODEL_MODULES:
        raise ValueError(
            f"Unsupported model_type '{model_type}'. "
            f"Supported values: {list(MODEL_MODULES.keys())}"
        )

    return MODEL_MODULES[model_type_key]


# ==========================================================
# PREDICT
# ==========================================================
def predict_model(model_type, model_dir, X_new):
    model_module = get_model_module(model_type)

    if not hasattr(model_module, "predict"):
        raise AttributeError(
            f"Module for model type '{model_type}' has no predict() function."
        )

    return model_module.predict(model_dir, X_new)


# ==========================================================
# ARGPARSE
# ==========================================================
def build_parser():
    parser = argparse.ArgumentParser(description="Predict using trained model")

    parser.add_argument(
        *CLI["model_type"],
        dest="model_type",
        required=True,
        help="Model type (ANN, GPR, PCE, CAT, XGB, RF, PR, SVR)",
    )

    parser.add_argument(
        *CLI["model_dir"],
        dest="model_dir",
        required=True,
        help="Directory containing trained model artifacts",
    )

    parser.add_argument(
        *CLI["x_input"],
        dest="x_input",
        required=True,
        help="Prediction input as .npy path, .json path, or raw JSON string",
    )

    parser.add_argument(
        *CLI["output_file"],
        dest="output_file",
        default=None,
        help="Optional output file path for prediction JSON",
    )

    parser.add_argument(
        *CLI["pretty"],
        dest="pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    return parser


# ==========================================================
# MAIN
# ==========================================================
def main():
    parser = build_parser()
    args = parser.parse_args()

    X_new = load_predict_input(args.x_input)

    pred = predict_model(
        model_type=args.model_type,
        model_dir=args.model_dir,
        X_new=X_new,
    )

    pred_out = pred.tolist() if hasattr(pred, "tolist") else pred

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(pred_out, f, indent=2 if args.pretty else None)
        print(f"Prediction written to: {args.output_file}")
    else:
        print(json.dumps(pred_out, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()