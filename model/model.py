import os, sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import ANN, GPR, PCE, CAT, XGB, RF, PR, SVR  # LGBM
import data_translator


# --------------------------------------------------
# TRANSLATION DISPATCH
# --------------------------------------------------
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


# --------------------------------------------------
# MODEL DISPATCH
# --------------------------------------------------
MODEL_MODULES = {
    "ANN": ANN,
    "GPR": GPR,
    "PCE": PCE,
    "CATBOOST": CAT,
    "CAT": CAT,
    "XGB": XGB,
    "RF": RF,
    "RANDOMFOREST": RF,
    "PR": PR,
    "SVR": SVR,
}


# --------------------------------------------------
# CONFIG LOADER
# --------------------------------------------------
def load_train_config(train_config):
    if isinstance(train_config, dict):
        return train_config

    if not isinstance(train_config, str):
        raise TypeError("train_config must be a dict, JSON string, or path to JSON file.")

    if os.path.isfile(train_config):
        with open(train_config, "r") as f:
            return json.load(f)

    try:
        return json.loads(train_config)
    except json.JSONDecodeError as e:
        raise ValueError(
            "train_config string is neither a valid file path nor valid JSON content."
        ) from e


# --------------------------------------------------
# DATA LOADER
# --------------------------------------------------
def load_translated_data(npz_file, translation_type, translation_params=None):
    if not os.path.exists(npz_file):
        raise FileNotFoundError(f"NPZ data file not found: {npz_file}")

    translation_key = translation_type.strip().lower()

    if translation_key not in TRANSLATORS:
        raise ValueError(
            f"Unsupported translation_type '{translation_type}'. "
            f"Supported values: {list(TRANSLATORS.keys())}"
        )

    translator_fn = TRANSLATORS[translation_key]
    translation_params = translation_params or {}

    return translator_fn(npz_file, **translation_params)


# --------------------------------------------------
# TRAIN ENTRYPOINT
# --------------------------------------------------
def train_model(npz_file, translation_type, train_config, output_dir, translation_params=None):
    config = load_train_config(train_config)

    if "model_type" not in config:
        raise KeyError("train_config must contain 'model_type'.")

    if "model_name" not in config:
        raise KeyError("train_config must contain 'model_name'.")

    model_type_key = str(config["model_type"]).strip().upper()

    if model_type_key not in MODEL_MODULES:
        raise ValueError(
            f"Unsupported model_type '{config['model_type']}'. "
            f"Supported values: {list(MODEL_MODULES.keys())}"
        )

    model_module = MODEL_MODULES[model_type_key]

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    X, y, _, _, _ = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type,
        translation_params=translation_params
    )

    if model_type_key == "PCE":
        model_module.train_model_pipeline(npz_file, output_dir, config)
    else:
        model_module.train_model_pipeline(X, y, config, output_dir)


# --------------------------------------------------
# PREDICTION SHAPE RESTORATION
# --------------------------------------------------
def _restore_prediction_to_original_format(y_pred, npz_file, translation_type):
    """
    Restore model predictions to the original raw data format using the
    structure stored in the npz file.

    Raw NPZ assumptions from data_translator:
        features -> (num_samples, num_feature_dims)
        targets  -> (num_samples, num_targets, num_freqs)
    """
    if not os.path.exists(npz_file):
        raise FileNotFoundError(f"NPZ data file not found: {npz_file}")

    translation_type = translation_type.strip().lower()

    with np.load(npz_file) as data:
        raw_features = data["features"]
        raw_targets = data["targets"]
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        frequency_points = data["frequency_points"]

    if raw_targets.ndim != 3:
        raise ValueError(
            f"Expected raw targets to have shape (num_samples, num_targets, num_freqs), "
            f"but got {raw_targets.shape}"
        )

    num_raw_samples = raw_targets.shape[0]
    num_targets = raw_targets.shape[1]
    num_freqs = raw_targets.shape[2]
    num_feature_dims = raw_features.shape[1]

    y_pred = np.asarray(y_pred)

    # ---------------- FFI ----------------
    # Training target:
    # y = targets.reshape(num_samples, -1)
    # Prediction comes out as:
    # (n_samples, num_targets * num_freqs)
    # Restore to:
    # (n_samples, num_targets, num_freqs)
    if translation_type in {"ffi", "ffi_augmented"}:
        expected_dim = num_targets * num_freqs
        if y_pred.ndim != 2 or y_pred.shape[1] != expected_dim:
            raise ValueError(
                f"FFI prediction shape mismatch. Expected second dim {expected_dim}, "
                f"got {y_pred.shape}"
            )

        restored = y_pred.reshape(y_pred.shape[0], num_targets, num_freqs)
        return {
            "predictions": restored,
            "target_names": target_names,
            "frequency_points": frequency_points,
            "format": "samples_targets_freqs"
        }

    # ---------------- FFD ----------------
    # Training target:
    # y = targets.transpose(0, 2, 1).reshape(-1, num_targets)
    # Prediction comes out as:
    # (n_samples * num_freqs, num_targets)
    # Restore to:
    # (n_samples, num_targets, num_freqs)
    if translation_type in {"ffd", "ffd_augmented"}:
        if y_pred.ndim != 2 or y_pred.shape[1] != num_targets:
            raise ValueError(
                f"FFD prediction shape mismatch. Expected second dim {num_targets}, "
                f"got {y_pred.shape}"
            )

        if y_pred.shape[0] % num_freqs != 0:
            raise ValueError(
                f"FFD prediction row count {y_pred.shape[0]} is not divisible by "
                f"num_freqs={num_freqs}"
            )

        num_samples = y_pred.shape[0] // num_freqs
        restored = y_pred.reshape(num_samples, num_freqs, num_targets).transpose(0, 2, 1)
        return {
            "predictions": restored,
            "target_names": target_names,
            "frequency_points": frequency_points,
            "format": "samples_targets_freqs"
        }

    # ---------------- IFI ----------------
    # Training target:
    # y = features
    # Prediction already comes out as:
    # (n_samples, num_feature_dims)
    if translation_type in {"ifi", "ifi_augmented"}:
        if y_pred.ndim != 2 or y_pred.shape[1] != num_feature_dims:
            raise ValueError(
                f"IFI prediction shape mismatch. Expected second dim {num_feature_dims}, "
                f"got {y_pred.shape}"
            )

        return {
            "predictions": y_pred,
            "target_names": feature_names,
            "frequency_points": None,
            "format": "samples_features"
        }

    # ---------------- IFD ----------------
    # Training target:
    # y = np.repeat(features, num_freqs, axis=0)
    # Prediction comes out as:
    # (n_samples * num_freqs, num_feature_dims)
    #
    # Since original raw format for geometry is (n_samples, num_feature_dims),
    # we restore both:
    # 1) per-frequency predictions -> (n_samples, num_freqs, num_feature_dims)
    # 2) averaged predictions      -> (n_samples, num_feature_dims)
    if translation_type in {"ifd", "ifd_augmented"}:
        if y_pred.ndim != 2 or y_pred.shape[1] != num_feature_dims:
            raise ValueError(
                f"IFD prediction shape mismatch. Expected second dim {num_feature_dims}, "
                f"got {y_pred.shape}"
            )

        if y_pred.shape[0] % num_freqs != 0:
            raise ValueError(
                f"IFD prediction row count {y_pred.shape[0]} is not divisible by "
                f"num_freqs={num_freqs}"
            )

        num_samples = y_pred.shape[0] // num_freqs
        per_frequency = y_pred.reshape(num_samples, num_freqs, num_feature_dims)
        averaged = per_frequency.mean(axis=1)

        return {
            "predictions": averaged,
            "predictions_per_frequency": per_frequency,
            "target_names": feature_names,
            "frequency_points": frequency_points,
            "format": "samples_features"
        }

    raise ValueError(f"Unsupported translation_type '{translation_type}'")


# --------------------------------------------------
# PREDICTION ENTRYPOINT
# --------------------------------------------------
def predict_model(model_type, model_dir, X_new, npz_file=None, translation_type=None, restore_original_format=True):
    """
    Unified prediction entrypoint.

    Parameters
    ----------
    model_type : str
        ANN, GPR, PCE, CAT, XGB, RF, PR, SVR
    model_dir : str
        Path to saved model directory
    X_new : np.ndarray
        Already-translated model input data
    npz_file : str, optional
        Original npz file used only for restoring prediction structure
    translation_type : str, optional
        ffi, ffd, ifi, ifd, ...
    restore_original_format : bool
        If True, convert prediction back to raw/original format

    Returns
    -------
    np.ndarray or dict
        Flat prediction if restore_original_format=False,
        otherwise structured prediction info dict
    """
    model_type_key = str(model_type).strip().upper()

    if model_type_key not in MODEL_MODULES:
        raise ValueError(
            f"Unsupported model_type '{model_type}'. "
            f"Supported values: {list(MODEL_MODULES.keys())}"
        )

    model_module = MODEL_MODULES[model_type_key]

    if not hasattr(model_module, "predict"):
        raise AttributeError(f"Module for model type '{model_type}' has no predict() function.")

    y_pred = model_module.predict(model_dir, X_new)

    if not restore_original_format:
        return y_pred

    if npz_file is None:
        raise ValueError("npz_file must be provided when restore_original_format=True")

    if translation_type is None:
        raise ValueError("translation_type must be provided when restore_original_format=True")

    return _restore_prediction_to_original_format(
        y_pred=y_pred,
        npz_file=npz_file,
        translation_type=translation_type
    )








# ======================== EXAMPLE =========================
# ==========================================================
# ==========================================================

import os

def example():
    # ==========================================================
    # PATHS
    # ==========================================================
    npz_file = "/mnt/storage/emon/projects/Conure/data/2026/TX11/simulation_data.npz"
    output_dir = "./data/MAGIC"

    # ==========================================================
    # EXPERIMENT SETTINGS
    # ==========================================================
    model_type = "ANN"

    # Train on augmented inverse data
    train_translation_type = "IFD_AUGMENTED"

    # Predict on clean inverse data
    predict_translation_type = "IFD_AUGMENTED"

    model_name = f"{model_type}_{train_translation_type.upper()}"
    model_dir = os.path.join(output_dir, model_name)

    num_samples_to_predict = 3

    # ==========================================================
    # TRAIN CONFIG
    # ==========================================================
    train_config = {
        "model_name": model_name,
        "model_type": model_type,

        "translation_params": {
            "feature_noise_std": 0.01,
            "target_noise_std": 0.005,
            "n_augment": 3,
            "clip": True
        },

        "normalization": {
            "feature_method": "standard",
            "target_method": "standard"
        },
        "training": {
            "epochs": 100,
            "batch_size": 32,
            "loss": "mse",
            "metrics": ["mae"],
            "validation_split": 0.2,
            "optimizer": {
                "type": "Adam",
                "learning_rate": 0.001,
                "momentum": 0.9
            }
        },
        "early_stopping": {
            "monitor": "val_loss",
            "patience": 15,
            "restore_best_weights": True
        },
        "architecture": [
            {
                "type": "Dense",
                "units": 128,
                "activation": "relu",
                "regularizer": {"type": "l2", "value": 0.01}
            },
            {"type": "Dropout", "rate": 0.1},
            {
                "type": "Dense",
                "units": 512,
                "activation": "relu",
                "regularizer": {"type": "l1_l2", "l1": 0.001, "l2": 0.01}
            },
            {"type": "Dense", "units": "AUTO", "activation": "linear"}
        ],
    }

    # ==========================================================
    # 1. TRAIN MODEL
    # ==========================================================
    train_model(
        npz_file=npz_file,
        translation_type=train_translation_type,
        train_config=train_config,
        output_dir=output_dir
    )

    print("Training completed.")

    # ==========================================================
    # 2. LOAD CLEAN DATA FOR PREDICTION
    # ==========================================================
    # For IFI:
    #   X = flattened EM response
    #   y = geometry parameters
    X, y, feature_names, target_names, freqs = load_translated_data(
        npz_file=npz_file,
        translation_type=predict_translation_type
    )

    X_test = X[:num_samples_to_predict]
    y_true = y[:num_samples_to_predict]

    # ==========================================================
    # 3. RUN PREDICTION
    # ==========================================================
    result = predict_model(
        model_type=model_type,
        model_dir=model_dir,
        X_new=X_test,
        npz_file=npz_file,
        translation_type=predict_translation_type,
        restore_original_format=True
    )

    pred = result["predictions"]

    # ==========================================================
    # 4. DISPLAY SUMMARY
    # ==========================================================
    print("\n" + "=" * 60)
    print("PREDICTION SUMMARY")
    print("=" * 60)
    print(f"Model name: {model_name}")
    print(f"Model type: {model_type}")
    print(f"Train translation type: {train_translation_type}")
    print(f"Predict translation type: {predict_translation_type}")
    print(f"Prediction shape: {pred.shape}")
    print(f"Predicted targets: {result['target_names']}")

    if result["frequency_points"] is not None:
        print(f"Number of frequency points: {len(result['frequency_points'])}")
    else:
        print("Frequency points: None")

    # ==========================================================
    # 5. ORIGINAL VS PREDICTED
    # ==========================================================
    print("\n" + "=" * 60)
    print("ORIGINAL VS PREDICTED")
    print("=" * 60)

    for i in range(num_samples_to_predict):
        print(f"\nSample {i + 1}")
        print("-" * 40)

        for j, name in enumerate(result["target_names"]):
            true_value = y_true[i, j]
            pred_value = pred[i, j]
            print(
                f"{name:>10} | "
                f"original: {true_value:12.6f} | "
                f"predicted: {pred_value:12.6f}"
            )


example()