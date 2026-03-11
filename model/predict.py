#!/usr/bin/env python3

import argparse
import copy
import json
import os
import sys
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


CLI = {
    "model_type": ("-t", "--model-type"),
    "model_dir": ("-m", "--model-dir"),
    "x_input": ("-x", "--x-input"),
    "output_file": ("-o", "--output-file"),
    "pretty": ("-p", "--pretty"),
    "flat_only": ("--flat-only",),
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


def _extract_payload_and_optional_metadata(payload):
    if isinstance(payload, dict):
        for key in ("X", "x", "inputs", "features", "data", "x_input"):
            if key in payload:
                return payload[key], payload
    return payload, None


def load_predict_input(x_input):
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
def _load_json_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prediction_metadata(model_dir):
    """
    Supports both layouts:
    1. New layout: report.json with artifact_metadata.translation_metadata
    2. Old layout: translation_metadata.json
    """
    report_path = os.path.join(model_dir, "report.json")
    report_data = _load_json_file(report_path)
    if isinstance(report_data, dict):
        artifact_meta = report_data.get("artifact_metadata") or {}
        translation_meta = artifact_meta.get("translation_metadata")
        if isinstance(translation_meta, dict):
            return {
                "source": "report.json",
                "translation_metadata": translation_meta,
                "report": report_data,
            }

    legacy_path = os.path.join(model_dir, "translation_metadata.json")
    legacy_data = _load_json_file(legacy_path)
    if isinstance(legacy_data, dict):
        if "translation_metadata" in legacy_data and isinstance(legacy_data["translation_metadata"], dict):
            return {
                "source": "translation_metadata.json",
                "translation_metadata": legacy_data["translation_metadata"],
            }
        return {
            "source": "translation_metadata.json",
            "translation_metadata": legacy_data,
        }

    return None


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------
def get_model_module(model_type):
    model_type_key = str(model_type).strip().upper()

    if model_type_key not in MODEL_MODULES:
        raise ValueError(
            f"Unsupported model_type '{model_type}'. "
            f"Supported values: {list(MODEL_MODULES.keys())}"
        )

    return MODEL_MODULES[model_type_key]


def ensure_2d_samples(X_new, metadata=None):
    arr = np.asarray(X_new, dtype=np.float32)

    if arr.ndim == 0:
        raise ValueError("Prediction input must have at least one dimension.")

    if metadata is None:
        if arr.ndim == 1:
            return arr.reshape(1, -1)
        return arr

    translation_meta = metadata.get("translation_metadata") or {}
    model_input_shape_per_sample = translation_meta.get("model_input_shape_per_sample") or []
    original_input_shape_per_sample = translation_meta.get("original_input_shape_per_sample") or []

    flat_input_width = int(np.prod(model_input_shape_per_sample)) if model_input_shape_per_sample else None
    structured_input_width = int(np.prod(original_input_shape_per_sample)) if original_input_shape_per_sample else None

    if arr.ndim == 1:
        return arr.reshape(1, -1)

    if arr.ndim >= 2 and structured_input_width and flat_input_width == structured_input_width:
        trailing_shape = tuple(original_input_shape_per_sample)
        if tuple(arr.shape[1:]) == trailing_shape:
            return arr.reshape(arr.shape[0], -1)

    return arr


def _to_serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, tuple):
        return list(value)
    return value


def _reshape_if_possible(pred, translation_meta):
    pred_arr = np.asarray(pred)
    output_shape = translation_meta.get("original_output_shape_per_sample")

    if not output_shape:
        return pred_arr, False

    flat_output_width = int(np.prod(translation_meta.get("model_output_shape_per_sample") or []))
    structured_output_width = int(np.prod(output_shape))

    if flat_output_width != structured_output_width:
        return pred_arr, False

    if pred_arr.ndim == 1:
        pred_arr = pred_arr.reshape(1, -1)

    if pred_arr.ndim != 2 or pred_arr.shape[1] != structured_output_width:
        return pred_arr, False

    reshaped = pred_arr.reshape((pred_arr.shape[0], *output_shape))
    return reshaped, True


def maybe_group_rows(pred, translation_meta):
    grouped_shape = translation_meta.get("grouped_output_shape_per_original_sample")
    if not grouped_shape:
        return None, False

    arr = np.asarray(pred)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    if arr.ndim != 2:
        return None, False

    rows_per_group = grouped_shape[0]
    cols_per_row = grouped_shape[1] if len(grouped_shape) > 1 else 1

    if arr.shape[1] != cols_per_row:
        return None, False

    if arr.shape[0] % rows_per_group != 0:
        return None, False

    grouped = arr.reshape(arr.shape[0] // rows_per_group, rows_per_group, cols_per_row)
    return grouped, True


def _named_vector(sample, names):
    if len(names) != len(sample):
        return None
    return {str(name): _to_serializable(value) for name, value in zip(names, sample)}


def _named_matrix_with_frequency(sample, target_names, freqs):
    if sample.ndim != 2:
        return None

    sample_arr = np.asarray(sample)
    freqs_arr = np.asarray(freqs)

    # Accept either orientation: (targets, freqs) or (freqs, targets)
    if sample_arr.shape[0] == len(target_names) and sample_arr.shape[1] == len(freqs_arr):
        oriented = sample_arr
    elif sample_arr.shape[1] == len(target_names) and sample_arr.shape[0] == len(freqs_arr):
        oriented = sample_arr.T
    else:
        return None

    named = {}
    freq_list = _to_serializable(freqs_arr)
    for idx, name in enumerate(target_names):
        named[str(name)] = {
            "frequency_points": freq_list,
            "values": _to_serializable(oriented[idx]),
        }
    return named


def build_named_predictions(structured_pred, translation_meta, prediction_mode):
    target_names = translation_meta.get("target_names") or []
    freqs = translation_meta.get("frequency_points") or []
    arr = np.asarray(structured_pred)

    named_predictions = []
    for sample in arr:
        if np.asarray(sample).ndim == 1:
            named = _named_vector(np.asarray(sample), target_names)
        elif np.asarray(sample).ndim == 2 and prediction_mode != "explicit_frequency":
            named = _named_matrix_with_frequency(np.asarray(sample), target_names, freqs)
        else:
            named = None
        named_predictions.append(named)

    return named_predictions


def is_frequency_dependent_translation(translation_type):
    if not translation_type:
        return False
    translation_type = str(translation_type).strip().lower()
    return translation_type in {
        "ffd",
        "ifd",
        "ffd_augmented",
        "ifd_augmented",
        "ffd_augment",
        "ifd_augment",
    }


def infer_prediction_mode(X_new, translation_meta):
    arr = np.asarray(X_new)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    translation_type = translation_meta.get("translation_type")
    feature_names = list(translation_meta.get("feature_names") or [])
    has_frequency_feature = any(str(name).strip().lower() == "frequency" for name in feature_names)

    if not is_frequency_dependent_translation(translation_type) or not has_frequency_feature:
        return "standard"

    input_width = arr.shape[1] if arr.ndim >= 2 else None
    feature_count = len(feature_names)

    if input_width == feature_count:
        return "explicit_frequency"

    if input_width == feature_count - 1:
        return "frequency_sweep"

    return "standard"


def build_prediction_context(X_new, translation_meta, mode):
    arr = np.asarray(X_new)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    feature_names = list(translation_meta.get("feature_names") or [])
    target_names = list(translation_meta.get("target_names") or [])

    context = {
        "translation_type": translation_meta.get("translation_type"),
        "mode": mode,
        "feature_names": feature_names,
        "target_names": target_names,
        "n_prediction_rows": int(arr.shape[0]) if arr.ndim >= 2 else 1,
    }

    if mode == "explicit_frequency" and arr.ndim >= 2 and arr.shape[1] >= 1:
        context["queried_frequency"] = _to_serializable(arr[:, -1])
    elif mode == "frequency_sweep":
        freqs = translation_meta.get("frequency_points") or []
        context["frequency_count"] = len(freqs)
        context["frequency_points"] = _to_serializable(np.asarray(freqs))

    return context


def sanitize_translation_metadata_for_output(translation_meta, mode):
    cleaned = copy.deepcopy(translation_meta)

    if mode == "explicit_frequency":
        cleaned.pop("frequency_points", None)
        cleaned.pop("frequency_count", None)
        cleaned["notes"] = (
            "Explicit-frequency prediction mode: the full training frequency grid is omitted "
            "from prediction output because the query already supplied frequency values."
        )

    return cleaned


def predict_model(model_type, model_dir, X_new):
    model_module = get_model_module(model_type)

    if not hasattr(model_module, "predict"):
        raise AttributeError(
            f"Module for model type '{model_type}' has no predict() function."
        )

    return model_module.predict(model_dir, X_new)


def build_parser():
    parser = argparse.ArgumentParser(description="Predict using trained model")

    parser.add_argument(*CLI["model_type"], dest="model_type", required=True,
                        help="Model type (ANN, GPR, PCE, CAT, XGB, RF, PR, SVR)")
    parser.add_argument(*CLI["model_dir"], dest="model_dir", required=True,
                        help="Directory containing trained model artifacts")
    parser.add_argument(*CLI["x_input"], dest="x_input", required=True,
                        help="Prediction input as .npy path, .json path, or raw JSON string")
    parser.add_argument(*CLI["output_file"], dest="output_file", default=None,
                        help="Optional output file path for prediction JSON")
    parser.add_argument(*CLI["pretty"], dest="pretty", action="store_true",
                        help="Pretty-print JSON output")
    parser.add_argument(*CLI["flat_only"], dest="flat_only", action="store_true",
                        help="Return only the raw flat prediction array, even when metadata is available.")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    X_new_raw, input_wrapper = load_predict_input(args.x_input)
    prediction_metadata = load_prediction_metadata(args.model_dir)
    X_new = ensure_2d_samples(X_new_raw, prediction_metadata)

    pred = predict_model(
        model_type=args.model_type,
        model_dir=args.model_dir,
        X_new=X_new,
    )

    if args.flat_only:
        pred_out = pred.tolist() if hasattr(pred, "tolist") else pred
    elif prediction_metadata is None:
        pred_out = {
            # "prediction_flat": _to_serializable(np.asarray(pred)),
            # "prediction_shape_flat": list(np.asarray(pred).shape),
            # "warning": "No prediction metadata found. Expected report.json or translation_metadata.json in model_dir.",
        }
    else:
        translation_meta = prediction_metadata.get("translation_metadata") or {}
        prediction_mode = infer_prediction_mode(X_new, translation_meta)

        structured_pred, was_reshaped = _reshape_if_possible(pred, translation_meta)
        grouped_pred, was_grouped = maybe_group_rows(pred, translation_meta)

        pred_out = {
            # "prediction_flat": _to_serializable(np.asarray(pred)),
            # "prediction_shape_flat": list(np.asarray(pred).shape),
            # "translation_metadata": sanitize_translation_metadata_for_output(
            #     translation_meta,
            #     prediction_mode,
            # ),
            # "prediction_context": build_prediction_context(
            #     X_new,
            #     translation_meta,
            #     prediction_mode,
            # ),
            # "input_summary": {
            #     "input_shape_after_normalization": list(np.asarray(X_new).shape),
            #     "input_wrapper_keys": sorted(list(input_wrapper.keys())) if isinstance(input_wrapper, dict) else None,
            #     "metadata_source": prediction_metadata.get("source"),
            # },
        }

        if was_reshaped:
            #pred_out["prediction_structured"] = _to_serializable(structured_pred)
            #pred_out["prediction_shape_structured"] = list(np.asarray(structured_pred).shape)

            named_predictions = build_named_predictions(structured_pred, translation_meta, prediction_mode)
            if any(item is not None for item in named_predictions):
                pred_out["prediction_named"] = named_predictions

        # if was_grouped and prediction_mode != "explicit_frequency":
        #     pred_out["prediction_grouped_by_original_sample"] = _to_serializable(grouped_pred)
        #     pred_out["prediction_shape_grouped"] = list(np.asarray(grouped_pred).shape)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(pred_out, f, indent=2 if args.pretty else None)
        print(f"Prediction written to: {args.output_file}")
    else:
        print(json.dumps(pred_out, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()


# #!/usr/bin/env python3

# import argparse
# import json
# import os
# import sys
# import numpy as np

# sys.path.insert(0, os.path.dirname(__file__))

# import ANN
# import CAT
# import GPR
# import PCE
# import PR
# import RF
# import SVR
# import XGB


# # ==========================================================
# # CLI FLAG DEFINITIONS
# # ==========================================================
# CLI = {
#     "model_type": ("-t", "--model-type"),
#     "model_dir": ("-m", "--model-dir"),
#     "x_input": ("-x", "--x-input"),
#     "output_file": ("-o", "--output-file"),
#     "pretty": ("-p", "--pretty"),
#     "flat_only": ("--flat-only",),
# }


# # ==========================================================
# # MODEL DISPATCH
# # ==========================================================
# MODEL_MODULES = {
#     "ANN": ANN,
#     "GPR": GPR,
#     "PCE": PCE,
#     "CAT": CAT,
#     "CATBOOST": CAT,
#     "XGB": XGB,
#     "RF": RF,
#     "RANDOMFOREST": RF,
#     "PR": PR,
#     "SVR": SVR,
# }


# # ==========================================================
# # LOADERS
# # ==========================================================
# def load_json_input(value):
#     """
#     Load JSON from:
#     - dict / list
#     - JSON string
#     - path to JSON file
#     """
#     if isinstance(value, (dict, list)):
#         return value

#     if not isinstance(value, str):
#         raise TypeError("Expected dict, list, JSON string, or JSON file path.")

#     if os.path.isfile(value):
#         with open(value, "r", encoding="utf-8") as f:
#             return json.load(f)

#     try:
#         return json.loads(value)
#     except json.JSONDecodeError as e:
#         raise ValueError(
#             "Input is neither a valid JSON file path nor valid JSON content."
#         ) from e



# def _extract_payload_and_optional_metadata(payload):
#     if isinstance(payload, dict):
#         for key in ("X", "x", "inputs", "features", "data"):
#             if key in payload:
#                 return payload[key], payload
#     return payload, None



# def load_predict_input(x_input):
#     """
#     Load X_new from:
#     - .npy file
#     - .json file
#     - raw JSON string
#     """
#     if not isinstance(x_input, str):
#         raise TypeError("--x-input must be a path or raw JSON string.")

#     if os.path.isfile(x_input):
#         lower = x_input.lower()

#         if lower.endswith(".npy"):
#             return np.load(x_input)

#         if lower.endswith(".json"):
#             payload = load_json_input(x_input)
#             extracted, wrapper = _extract_payload_and_optional_metadata(payload)
#             return np.asarray(extracted, dtype=np.float32), wrapper

#         raise ValueError("Supported input file types for --x-input are .npy and .json")

#     payload = load_json_input(x_input)
#     extracted, wrapper = _extract_payload_and_optional_metadata(payload)
#     return np.asarray(extracted, dtype=np.float32), wrapper



# def load_prediction_metadata(model_dir):
#     report_path = os.path.join(model_dir, "report.json")
#     if os.path.isfile(report_path):
#         with open(report_path, "r", encoding="utf-8") as f:
#             report_payload = json.load(f)

#         artifact_metadata = report_payload.get("artifact_metadata") or {}
#         translation_metadata = artifact_metadata.get("translation_metadata")
#         if translation_metadata is not None:
#             return {
#                 "artifact_metadata": artifact_metadata,
#                 "translation_metadata": translation_metadata,
#             }

#         legacy_translation_metadata = report_payload.get("translation_metadata")
#         if legacy_translation_metadata is not None:
#             return {
#                 "translation_metadata": legacy_translation_metadata,
#             }

#     metadata_path = os.path.join(model_dir, "translation_metadata.json")
#     if os.path.isfile(metadata_path):
#         with open(metadata_path, "r", encoding="utf-8") as f:
#             legacy_payload = json.load(f)

#         if isinstance(legacy_payload, dict) and "translation_metadata" in legacy_payload:
#             return legacy_payload

#         return {"translation_metadata": legacy_payload}

#     return None


# # ==========================================================
# # HELPERS
# # ==========================================================
# def get_model_module(model_type):
#     model_type_key = str(model_type).strip().upper()

#     if model_type_key not in MODEL_MODULES:
#         raise ValueError(
#             f"Unsupported model_type '{model_type}'. "
#             f"Supported values: {list(MODEL_MODULES.keys())}"
#         )

#     return MODEL_MODULES[model_type_key]



# def ensure_2d_samples(X_new, metadata=None):
#     arr = np.asarray(X_new, dtype=np.float32)

#     if arr.ndim == 0:
#         raise ValueError("Prediction input must have at least one dimension.")

#     if metadata is None:
#         if arr.ndim == 1:
#             return arr.reshape(1, -1)
#         return arr

#     translation_meta = metadata.get("translation_metadata") or {}
#     model_input_shape_per_sample = translation_meta.get("model_input_shape_per_sample") or []
#     original_input_shape_per_sample = translation_meta.get("original_input_shape_per_sample") or []

#     flat_input_width = int(np.prod(model_input_shape_per_sample)) if model_input_shape_per_sample else None
#     structured_input_width = int(np.prod(original_input_shape_per_sample)) if original_input_shape_per_sample else None

#     if arr.ndim == 1:
#         return arr.reshape(1, -1)

#     if arr.ndim >= 2 and structured_input_width and flat_input_width == structured_input_width:
#         trailing_shape = tuple(original_input_shape_per_sample)
#         if tuple(arr.shape[1:]) == trailing_shape:
#             return arr.reshape(arr.shape[0], -1)

#     return arr



# def _reshape_if_possible(pred, translation_meta):
#     pred_arr = np.asarray(pred)
#     output_shape = translation_meta.get("original_output_shape_per_sample")

#     if not output_shape:
#         return pred_arr, False

#     flat_output_width = int(np.prod(translation_meta.get("model_output_shape_per_sample") or []))
#     structured_output_width = int(np.prod(output_shape))

#     if flat_output_width != structured_output_width:
#         return pred_arr, False

#     if pred_arr.ndim == 1:
#         pred_arr = pred_arr.reshape(1, -1)

#     if pred_arr.ndim != 2 or pred_arr.shape[1] != structured_output_width:
#         return pred_arr, False

#     reshaped = pred_arr.reshape((pred_arr.shape[0], *output_shape))
#     return reshaped, True



# def _named_vector(sample, names):
#     if len(names) != len(sample):
#         return None
#     return {str(name): _to_serializable(value) for name, value in zip(names, sample)}



# def _named_matrix_with_frequency(sample, target_names, freqs):
#     if sample.ndim != 2:
#         return None
#     if sample.shape[0] != len(target_names):
#         return None
#     if sample.shape[1] != len(freqs):
#         return None

#     named = {}
#     freq_list = _to_serializable(np.asarray(freqs))
#     for idx, name in enumerate(target_names):
#         named[str(name)] = {
#             "frequency_points": freq_list,
#             "values": _to_serializable(sample[idx]),
#         }
#     return named



# def _to_serializable(value):
#     if isinstance(value, np.ndarray):
#         return value.tolist()
#     if isinstance(value, (np.integer, np.floating)):
#         return value.item()
#     if isinstance(value, tuple):
#         return list(value)
#     return value



# def build_named_predictions(structured_pred, translation_meta):
#     target_names = translation_meta.get("target_names") or []
#     freqs = translation_meta.get("frequency_points") or []
#     arr = np.asarray(structured_pred)

#     named_predictions = []
#     for sample in arr:
#         if sample.ndim == 1:
#             named = _named_vector(sample, target_names)
#         elif sample.ndim == 2:
#             named = _named_matrix_with_frequency(sample, target_names, freqs)
#         else:
#             named = None
#         named_predictions.append(named)

#     return named_predictions



# def maybe_group_rows(pred, translation_meta):
#     grouped_shape = translation_meta.get("grouped_output_shape_per_original_sample")
#     if not grouped_shape:
#         return None, False

#     arr = np.asarray(pred)
#     if arr.ndim == 1:
#         arr = arr.reshape(1, -1)

#     if arr.ndim != 2:
#         return None, False

#     rows_per_group = grouped_shape[0]
#     cols_per_row = grouped_shape[1] if len(grouped_shape) > 1 else 1

#     if arr.shape[1] != cols_per_row:
#         return None, False

#     if arr.shape[0] % rows_per_group != 0:
#         return None, False

#     grouped = arr.reshape(arr.shape[0] // rows_per_group, rows_per_group, cols_per_row)
#     return grouped, True


# # ==========================================================
# # PREDICT
# # ==========================================================
# def predict_model(model_type, model_dir, X_new):
#     model_module = get_model_module(model_type)

#     if not hasattr(model_module, "predict"):
#         raise AttributeError(
#             f"Module for model type '{model_type}' has no predict() function."
#         )

#     return model_module.predict(model_dir, X_new)


# # ==========================================================
# # ARGPARSE
# # ==========================================================
# def build_parser():
#     parser = argparse.ArgumentParser(description="Predict using trained model")

#     parser.add_argument(
#         *CLI["model_type"],
#         dest="model_type",
#         required=True,
#         help="Model type (ANN, GPR, PCE, CAT, XGB, RF, PR, SVR)",
#     )

#     parser.add_argument(
#         *CLI["model_dir"],
#         dest="model_dir",
#         required=True,
#         help="Directory containing trained model artifacts",
#     )

#     parser.add_argument(
#         *CLI["x_input"],
#         dest="x_input",
#         required=True,
#         help="Prediction input as .npy path, .json path, or raw JSON string",
#     )

#     parser.add_argument(
#         *CLI["output_file"],
#         dest="output_file",
#         default=None,
#         help="Optional output file path for prediction JSON",
#     )

#     parser.add_argument(
#         *CLI["pretty"],
#         dest="pretty",
#         action="store_true",
#         help="Pretty-print JSON output",
#     )

#     parser.add_argument(
#         *CLI["flat_only"],
#         dest="flat_only",
#         action="store_true",
#         help="Return only the raw flat prediction array, even when metadata is available.",
#     )

#     return parser


# # ==========================================================
# # MAIN
# # ==========================================================
# def main():
#     parser = build_parser()
#     args = parser.parse_args()

#     X_new_raw, input_wrapper = load_predict_input(args.x_input)
#     prediction_metadata = load_prediction_metadata(args.model_dir)
#     X_new = ensure_2d_samples(X_new_raw, prediction_metadata)

#     pred = predict_model(
#         model_type=args.model_type,
#         model_dir=args.model_dir,
#         X_new=X_new,
#     )

#     if args.flat_only or prediction_metadata is None:
#         pred_out = pred.tolist() if hasattr(pred, "tolist") else pred
#     else:
#         translation_meta = prediction_metadata.get("translation_metadata") or {}

#         structured_pred, was_reshaped = _reshape_if_possible(pred, translation_meta)
#         grouped_pred, was_grouped = maybe_group_rows(pred, translation_meta)

#         pred_out = {
#             "prediction_flat": _to_serializable(np.asarray(pred)),
#             "prediction_shape_flat": list(np.asarray(pred).shape),
#             "translation_metadata": translation_meta,
#             "input_summary": {
#                 "input_shape_after_normalization": list(np.asarray(X_new).shape),
#                 "input_wrapper_keys": sorted(list(input_wrapper.keys())) if isinstance(input_wrapper, dict) else None,
#             },
#         }

#         if was_reshaped:
#             pred_out["prediction_structured"] = _to_serializable(structured_pred)
#             pred_out["prediction_shape_structured"] = list(np.asarray(structured_pred).shape)
#             named_predictions = build_named_predictions(structured_pred, translation_meta)
#             if any(item is not None for item in named_predictions):
#                 pred_out["prediction_named"] = named_predictions

#         if was_grouped:
#             pred_out["prediction_grouped_by_original_sample"] = _to_serializable(grouped_pred)
#             pred_out["prediction_shape_grouped"] = list(np.asarray(grouped_pred).shape)

#     if args.output_file:
#         with open(args.output_file, "w", encoding="utf-8") as f:
#             json.dump(pred_out, f, indent=2 if args.pretty else None)
#         print(f"Prediction written to: {args.output_file}")
#     else:
#         print(json.dumps(pred_out, indent=2 if args.pretty else None))


# if __name__ == "__main__":
#     main()
