#!/usr/bin/env python3

import os
import sys
import json
import argparse
import inspect

sys.path.insert(0, os.path.dirname(__file__))

import ANN
import GPR
import PCE
import CAT
import XGB
import RF
import PR
import SVR
import data_translator


# ==========================================================
# CLI FLAG DEFINITIONS
# ==========================================================
CLI = {
    "npz_file": ("-d", "--npz-file"),
    "model_type": ("-t", "--model-type"),
    "translate_config": ("-a", "--translate-config"),
    "model_config": ("-m", "--model-config"),
    "output_dir": ("-o", "--output-dir"),
}


# ==========================================================
# TRANSLATION DISPATCH
# ==========================================================
TRANSLATORS = {
    "ffi": data_translator.prepare_ffi_data,
    "ffi_augmented": data_translator.prepare_ffi_augmented,
    "ffd": data_translator.prepare_ffd_data,
    "ffd_augmented": data_translator.prepare_ffd_augmented,
    "ifi": data_translator.prepare_ifi_data,
    "ifi_augmented": data_translator.prepare_ifi_augmented,
    "ifd": data_translator.prepare_ifd_data,
    "ifd_augmented": data_translator.prepare_ifd_augmented,
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
    - dict
    - JSON string
    - path to JSON file
    """
    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        raise TypeError("Expected dict, JSON string, or JSON file path.")

    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(
            "Input is neither a valid JSON file path nor valid JSON content."
        ) from e


def load_translate_config(config_input):
    config = load_json_input(config_input)

    if not isinstance(config, dict):
        raise TypeError("translate_config must resolve to a JSON object.")

    if "translation_type" not in config:
        raise KeyError("translate_config must contain 'translation_type'.")

    translation_params = config.get("translation_params", {})
    if translation_params is None:
        translation_params = {}
    if not isinstance(translation_params, dict):
        raise TypeError("'translation_params' must be a dictionary.")

    return config


def load_model_config(config_input):
    config = load_json_input(config_input)

    if not isinstance(config, dict):
        raise TypeError("model_config must resolve to a JSON object.")

    if "model_name" not in config:
        raise KeyError("model_config must contain 'model_name'.")

    return config


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


def build_effective_train_config(model_type, model_config):
    """
    Build the flat config expected by existing model modules.
    """
    model_type_key = str(model_type).strip().upper()

    effective_config = {
        "model_type": model_type_key,
        **model_config,
    }

    return effective_config


def load_translated_data(npz_file, translation_type, translation_params=None):
    if not os.path.exists(npz_file):
        raise FileNotFoundError(f"NPZ data file not found: {npz_file}")

    translation_key = str(translation_type).strip().lower()

    if translation_key not in TRANSLATORS:
        raise ValueError(
            f"Unsupported translation_type '{translation_type}'. "
            f"Supported values: {list(TRANSLATORS.keys())}"
        )

    translator_fn = TRANSLATORS[translation_key]
    translation_params = translation_params or {}

    sig = inspect.signature(translator_fn)
    allowed_params = sig.parameters

    filtered_params = {
        k: v for k, v in translation_params.items()
        if k in allowed_params
    }

    return translator_fn(npz_file, **filtered_params)


# ==========================================================
# TRAIN
# ==========================================================
def train_model(npz_file, model_type, translate_config, model_config, output_dir):
    translation_type = translate_config["translation_type"]
    translation_params = translate_config.get("translation_params", {})

    effective_config = build_effective_train_config(model_type, model_config)
    model_module = get_model_module(effective_config["model_type"])

    os.makedirs(output_dir, exist_ok=True)

    X, y, _, _, _ = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type,
        translation_params=translation_params,
    )

    if str(effective_config["model_type"]).strip().upper() == "PCE":
        model_module.train_model_pipeline(npz_file, output_dir, effective_config)
    else:
        model_module.train_model_pipeline(X, y, effective_config, output_dir)


# ==========================================================
# ARGPARSE
# ==========================================================
def build_parser():
    parser = argparse.ArgumentParser(description="Train surrogate model")

    parser.add_argument(
        *CLI["npz_file"],
        dest="npz_file",
        required=True,
        help="Path to simulation_data.npz",
    )

    parser.add_argument(
        *CLI["model_type"],
        dest="model_type",
        required=True,
        help="Model type (ANN, GPR, PCE, CAT, XGB, RF, PR, SVR)",
    )

    parser.add_argument(
        *CLI["translate_config"],
        dest="translate_config",
        required=True,
        help="Translation config JSON file path or raw JSON string",
    )

    parser.add_argument(
        *CLI["model_config"],
        dest="model_config",
        required=True,
        help="Model config JSON file path or raw JSON string",
    )

    parser.add_argument(
        *CLI["output_dir"],
        dest="output_dir",
        required=True,
        help="Directory where trained model artifacts will be saved",
    )

    return parser


# ==========================================================
# MAIN
# ==========================================================
def main():
    parser = build_parser()
    args = parser.parse_args()

    translate_config = load_translate_config(args.translate_config)
    model_config = load_model_config(args.model_config)

    train_model(
        npz_file=args.npz_file,
        model_type=args.model_type,
        translate_config=translate_config,
        model_config=model_config,
        output_dir=args.output_dir,
    )

    print("Training completed.")


if __name__ == "__main__":
    main()