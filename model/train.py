#!/usr/bin/env python3

import argparse
import inspect
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(__file__))

import ANN
import CAT
import GPR
import PCE
import PR
import RF
import SVR
import XGB
import data_translator
import report


CLI = {
    "npz_file": ("-d", "--npz-file"),
    "model_type": ("-t", "--model-type"),
    "translate_config": ("-a", "--translate-config"),
    "model_config": ("-m", "--model-config"),
    "output_dir": ("-o", "--output-dir"),
}


TRANSLATORS = {
    "ffi": data_translator.prepare_ffi_data,
    "ffi_augmented": data_translator.prepare_ffi_augmented,
    "ffd": data_translator.prepare_ffd_data,
    "ffd_augmented": data_translator.prepare_ffd_augmented,
    "ifi": data_translator.prepare_ifi_data,
    "ifi_augmented": data_translator.prepare_ifi_augmented,
    "ifd": data_translator.prepare_ifd_data,
    "ifd_augmented": data_translator.prepare_ifd_augmented,
    "ffi_inductor": data_translator.prepare_ffi_inductor_data,
    "ffi_inductor_augmented": data_translator.prepare_ffi_inductor_augmented,
    "ffd_inductor": data_translator.prepare_ffd_inductor_data,
    "ffd_inductor_augmented": data_translator.prepare_ffd_inductor_augmented,
    "ifi_inductor": data_translator.prepare_ifi_inductor_data,
    "ifi_inductor_augmented": data_translator.prepare_ifi_inductor_augmented,
    "ifd_inductor": data_translator.prepare_ifd_inductor_data,
    "ifd_inductor_augmented": data_translator.prepare_ifd_inductor_augmented,
    "ffi_transformer": data_translator.prepare_ffi_transformer_data,
    "ffi_transformer_augmented": data_translator.prepare_ffi_transformer_augmented,
    "ffd_transformer": data_translator.prepare_ffd_transformer_data,
    "ffd_transformer_augmented": data_translator.prepare_ffd_transformer_augmented,
    "ifi_transformer": data_translator.prepare_ifi_transformer_data,
    "ifi_transformer_augmented": data_translator.prepare_ifi_transformer_augmented,
    "ifd_transformer": data_translator.prepare_ifd_transformer_data,
    "ifd_transformer_augmented": data_translator.prepare_ifd_transformer_augmented,
}


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


def load_json_input(value):
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


def _normalize_selection(config: Dict[str, Any]) -> Dict[str, Any]:
    selection = config.get("selection", {}) or {}
    if not isinstance(selection, dict):
        raise TypeError("translate_config.selection must be an object when provided.")

    def _to_name_list(value, key):
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError(f"translate_config.selection.{key} must be a list of strings.")
        out = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out

    return {
        "x_names": _to_name_list(selection.get("x_names", []), "x_names"),
        "y_names": _to_name_list(selection.get("y_names", []), "y_names"),
    }


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

    config = dict(config)
    config["translation_params"] = translation_params
    config["selection"] = _normalize_selection(config)
    return config


def load_model_config(config_input):
    config = load_json_input(config_input)

    if not isinstance(config, dict):
        raise TypeError("model_config must resolve to a JSON object.")

    if "model_name" not in config:
        raise KeyError("model_config must contain 'model_name'.")

    return config


def get_model_module(model_type):
    model_type_key = str(model_type).strip().upper()

    if model_type_key not in MODEL_MODULES:
        raise ValueError(
            f"Unsupported model_type '{model_type}'. "
            f"Supported values: {list(MODEL_MODULES.keys())}"
        )

    return MODEL_MODULES[model_type_key]


def build_effective_train_config(model_type, model_config):
    return {"model_type": str(model_type).strip().upper(), **model_config}


def load_translated_data(npz_file, translation_type, translation_params=None, return_metadata=False):
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
    filtered_params = {k: v for k, v in translation_params.items() if k in allowed_params}

    if return_metadata and "return_metadata" in allowed_params:
        filtered_params["return_metadata"] = True

    return translator_fn(npz_file, **filtered_params)


def _prod(values: Sequence[int]) -> int:
    out = 1
    for v in values:
        out *= int(v)
    return int(out)


def _normalize_names(names: Optional[Sequence[Any]]) -> List[str]:
    if not names:
        return []
    return [str(x) for x in names]


def _axis_group_info(names: Sequence[str], flat_width: int, per_sample_shape: Optional[Sequence[Any]]) -> Tuple[str, int, List[str]]:
    names = _normalize_names(names)
    if flat_width <= 0:
        return "direct", 1, names
    if not names:
        names = [f"col_{i}" for i in range(flat_width)]
        return "direct", 1, names
    if len(names) == flat_width:
        return "direct", 1, names
    if per_sample_shape:
        try:
            shape = [int(x) for x in per_sample_shape]
        except Exception:
            shape = []
        if shape and len(shape) >= 1 and shape[0] == len(names):
            trailing = _prod(shape[1:]) if len(shape) > 1 else 1
            if trailing > 0 and len(names) * trailing == flat_width:
                return "grouped", trailing, names
    if flat_width % len(names) == 0:
        return "grouped", flat_width // len(names), names
    expanded = [f"col_{i}" for i in range(flat_width)]
    return "direct", 1, expanded


def _selection_info(X, y, feature_names, target_names, translation_metadata=None):
    meta = translation_metadata or {}
    x_mode, x_group_size, x_selectable_names = _axis_group_info(
        feature_names,
        int(X.shape[1]),
        meta.get("original_input_shape_per_sample"),
    )
    y_mode, y_group_size, y_selectable_names = _axis_group_info(
        target_names,
        int(y.shape[1]),
        meta.get("original_output_shape_per_sample"),
    )
    return {
        "x": {
            "mode": x_mode,
            "group_size": int(x_group_size),
            "selectable_names": x_selectable_names,
            "flat_width": int(X.shape[1]),
        },
        "y": {
            "mode": y_mode,
            "group_size": int(y_group_size),
            "selectable_names": y_selectable_names,
            "flat_width": int(y.shape[1]),
        },
    }


def _resolve_selected_indices(selected_names: Sequence[str], selectable_names: Sequence[str], mode: str, group_size: int, flat_width: int, axis_label: str) -> Tuple[List[int], List[str], List[str]]:
    """
    Returns ``(indices, ordered_group_names, column_labels)`` where ``column_labels`` has one
    logical name per *output* column (length == len(indices)), for per-feature normalization maps.
    """
    selectable_names = _normalize_names(selectable_names)
    selected_names = _normalize_names(selected_names)

    if not selected_names:
        indices = list(range(flat_width))
        column_labels: List[str] = []
        if mode == "grouped" and group_size > 0:
            for j in range(flat_width):
                gi = j // group_size
                column_labels.append(
                    selectable_names[gi] if gi < len(selectable_names) else f"col_{j}"
                )
        else:
            for j in range(flat_width):
                column_labels.append(
                    selectable_names[j] if j < len(selectable_names) else f"col_{j}"
                )
        return indices, list(selectable_names), column_labels

    name_to_idx = {name: idx for idx, name in enumerate(selectable_names)}
    missing = [name for name in selected_names if name not in name_to_idx]
    if missing:
        raise ValueError(f"Unknown selected {axis_label} name(s): {missing}. Available: {selectable_names}")

    ordered_names = []
    indices = []
    column_labels = []
    for name in selected_names:
        if name in ordered_names:
            continue
        ordered_names.append(name)
        idx = name_to_idx[name]
        if mode == "grouped":
            start = idx * group_size
            stop = min(start + group_size, flat_width)
            for i in range(start, stop):
                indices.append(i)
                column_labels.append(name)
        else:
            indices.append(idx)
            column_labels.append(name)

    if not indices:
        raise ValueError(f"Selection for axis '{axis_label}' removed all columns.")

    return indices, ordered_names, column_labels


def apply_translated_selection(X, y, feature_names, target_names, selection=None, translation_metadata=None):
    selection = selection or {}
    info = _selection_info(X, y, feature_names, target_names, translation_metadata)

    x_indices, resolved_x_names, x_column_labels = _resolve_selected_indices(
        selection.get("x_names", []),
        info["x"]["selectable_names"],
        info["x"]["mode"],
        info["x"]["group_size"],
        info["x"]["flat_width"],
        "X",
    )
    y_indices, resolved_y_names, y_column_labels = _resolve_selected_indices(
        selection.get("y_names", []),
        info["y"]["selectable_names"],
        info["y"]["mode"],
        info["y"]["group_size"],
        info["y"]["flat_width"],
        "Y",
    )

    X_sel = X[:, x_indices]
    y_sel = y[:, y_indices]

    updated_meta = dict(translation_metadata or {})
    updated_meta["selection"] = {
        "x_names": resolved_x_names,
        "y_names": resolved_y_names,
        "x_mode": info["x"]["mode"],
        "y_mode": info["y"]["mode"],
        "x_group_size": info["x"]["group_size"],
        "y_group_size": info["y"]["group_size"],
        "x_indices": x_indices,
        "y_indices": y_indices,
        "x_flat_width_before_selection": info["x"]["flat_width"],
        "y_flat_width_before_selection": info["y"]["flat_width"],
        "x_flat_width_after_selection": int(X_sel.shape[1]),
        "y_flat_width_after_selection": int(y_sel.shape[1]),
    }
    updated_meta["selected_feature_names"] = resolved_x_names
    updated_meta["selected_target_names"] = resolved_y_names
    updated_meta["model_input_shape"] = [int(X_sel.shape[0]), int(X_sel.shape[1])]
    updated_meta["model_output_shape"] = [int(y_sel.shape[0]), int(y_sel.shape[1])]
    updated_meta["model_input_shape_per_sample"] = [int(X_sel.shape[1])]
    updated_meta["model_output_shape_per_sample"] = [int(y_sel.shape[1])]
    updated_meta["feature_column_names"] = list(x_column_labels)
    updated_meta["target_column_names"] = list(y_column_labels)

    return X_sel, y_sel, resolved_x_names, resolved_y_names, updated_meta, info


def build_translation_preview(npz_file, translate_config):
    """
    Preview should describe the translated schema for the *current* translation config.
    It must not fail because of stale X/Y selections from a previous translation type.
    """
    translate_config = load_translate_config(translate_config)
    translated = load_translated_data(
        npz_file=npz_file,
        translation_type=translate_config["translation_type"],
        translation_params=translate_config.get("translation_params", {}),
        return_metadata=True,
    )

    if len(translated) == 6:
        X, y, feature_names, target_names, freqs, translation_metadata = translated
    else:
        X, y, feature_names, target_names, freqs = translated
        translation_metadata = {}

    selection_info = _selection_info(X, y, feature_names, target_names, translation_metadata)

    # For preview we intentionally ignore persisted selection from the config.
    # The UI may still keep a local subset and reconcile it against these names.
    resolved_x_names = list(selection_info["x"]["selectable_names"])
    resolved_y_names = list(selection_info["y"]["selectable_names"])

    return {
        "translation_type": translate_config["translation_type"],
        "translation_params": translate_config.get("translation_params", {}),
        "feature_names": _normalize_names(feature_names),
        "target_names": _normalize_names(target_names),
        "freq_count": None if freqs is None else int(len(freqs)),
        "model_input_width": int(X.shape[1]),
        "model_output_width": int(y.shape[1]),
        "selection": {
            "x": {
                **selection_info["x"],
                "selected_names": resolved_x_names,
            },
            "y": {
                **selection_info["y"],
                "selected_names": resolved_y_names,
            },
        },
        "translation_metadata": translation_metadata or {},
    }


def build_artifact_metadata(npz_file, translate_config, translation_metadata):
    return {
        "npz_file": os.path.abspath(npz_file),
        "translate_config": translate_config,
        "translation_metadata": translation_metadata,
    }


def get_model_artifact_dir(output_dir, effective_config):
    model_name = effective_config.get("model_name")
    if not model_name:
        raise KeyError("model_config must contain 'model_name'.")
    return os.path.join(output_dir, model_name)


def save_artifact_metadata_into_report(model_artifact_dir, artifact_metadata):
    os.makedirs(model_artifact_dir, exist_ok=True)
    report_path = os.path.join(model_artifact_dir, "report.json")
    report_data = report.load_report(report_path)
    report_data["artifact_metadata"] = artifact_metadata
    report.save_report(report_data, model_artifact_dir)
    return report_path


def train_model(npz_file, model_type, translate_config, model_config, output_dir):
    translate_config = load_translate_config(translate_config)
    translation_type = translate_config["translation_type"]
    translation_params = translate_config.get("translation_params", {})
    selection = translate_config.get("selection", {}) or {}

    effective_config = build_effective_train_config(model_type, model_config)
    model_module = get_model_module(effective_config["model_type"])
    os.makedirs(output_dir, exist_ok=True)

    translated = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type,
        translation_params=translation_params,
        return_metadata=True,
    )

    if len(translated) == 6:
        X, y, feature_names, target_names, _, translation_metadata = translated
    else:
        X, y, feature_names, target_names, _ = translated
        translation_metadata = {}

    X, y, selected_feature_names, selected_target_names, translation_metadata, _ = apply_translated_selection(
        X,
        y,
        feature_names,
        target_names,
        selection=selection,
        translation_metadata=translation_metadata,
    )

    norm_cfg = effective_config.setdefault("normalization", {})
    if not isinstance(norm_cfg, dict):
        norm_cfg = {}
        effective_config["normalization"] = norm_cfg
    norm_cfg["feature_column_names"] = translation_metadata.get("feature_column_names")
    norm_cfg["target_column_names"] = translation_metadata.get("target_column_names")

    model_module.train_model_pipeline(X, y, effective_config, output_dir)

    model_artifact_dir = get_model_artifact_dir(output_dir, effective_config)
    artifact_metadata = build_artifact_metadata(
        npz_file=npz_file,
        translate_config=translate_config,
        translation_metadata=translation_metadata,
    )
    artifact_metadata["selected_feature_names"] = selected_feature_names
    artifact_metadata["selected_target_names"] = selected_target_names
    report_path = save_artifact_metadata_into_report(model_artifact_dir, artifact_metadata)

    legacy_metadata_path = os.path.join(model_artifact_dir, "translation_metadata.json")
    if os.path.isfile(legacy_metadata_path):
        os.remove(legacy_metadata_path)

    return report_path


def build_parser():
    parser = argparse.ArgumentParser(description="Train surrogate model")
    parser.add_argument(*CLI["npz_file"], dest="npz_file", required=True, help="Path to simulation_data.npz")
    parser.add_argument(*CLI["model_type"], dest="model_type", required=True, help="Model type (ANN, GPR, PCE, CAT, XGB, RF, PR, SVR)")
    parser.add_argument(*CLI["translate_config"], dest="translate_config", required=True, help="Translation config JSON file path or raw JSON string")
    parser.add_argument(*CLI["model_config"], dest="model_config", required=True, help="Model config JSON file path or raw JSON string")
    parser.add_argument(*CLI["output_dir"], dest="output_dir", required=True, help="Directory where trained model artifacts will be saved")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    translate_config = load_translate_config(args.translate_config)
    model_config = load_model_config(args.model_config)

    report_path = train_model(
        npz_file=args.npz_file,
        model_type=args.model_type,
        translate_config=translate_config,
        model_config=model_config,
        output_dir=args.output_dir,
    )

    print("Training completed.")
    print(f"Artifact metadata written into: {report_path}")


if __name__ == "__main__":
    main()
