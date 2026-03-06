import os
import sys
import json

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
import inspect

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
# CONFIG LOADER
# ==========================================================
def load_train_config(train_config):
    """
    Load training config from:
    - dict
    - JSON string
    - path to JSON file
    """
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

    # Keep only parameters the translator actually accepts
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
def train_model(npz_file, translation_type, train_config, output_dir, translation_params=None):
    """
    Unified training entrypoint.
    """
    config = load_train_config(train_config)

    if "model_type" not in config:
        raise KeyError("train_config must contain 'model_type'.")

    if "model_name" not in config:
        raise KeyError("train_config must contain 'model_name'.")

    if translation_params is None:
        translation_params = config.get("translation_params", {})

    model_module = get_model_module(config["model_type"])

    os.makedirs(output_dir, exist_ok=True)

    X, y, _, _, _ = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type,
        translation_params=translation_params
    )

    # PCE currently has a different training signature
    if str(config["model_type"]).strip().upper() == "PCE":
        model_module.train_model_pipeline(npz_file, output_dir, config)
    else:
        model_module.train_model_pipeline(X, y, config, output_dir)


# ==========================================================
# PREDICT
# ==========================================================
def predict_model(model_type, model_dir, X_new):
    """
    Unified prediction entrypoint.
    """
    model_module = get_model_module(model_type)

    if not hasattr(model_module, "predict"):
        raise AttributeError(
            f"Module for model type '{model_type}' has no predict() function."
        )

    return model_module.predict(model_dir, X_new)


# ==========================================================
# EXAMPLE
# ==========================================================
def example():
    # ---------------------------
    # Paths
    # ---------------------------
    npz_file = "/mnt/storage/emon/projects/Conure/data/2026/TX11/simulation_data.npz"
    output_dir = "./data/MAGIC"

    # ---------------------------
    # Experiment settings
    # ---------------------------
    model_type = "ANN"
    translation_type = "FFD"
    model_name = f"{model_type}_{translation_type.upper()}"
    model_dir = os.path.join(output_dir, model_name)

    # ---------------------------
    # Training config
    # ---------------------------
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
    # 1. TRAIN
    # ==========================================================
    train_model(
        npz_file=npz_file,
        translation_type=translation_type,
        train_config=train_config,
        output_dir=output_dir
    )
    print("Training completed.")

    # ==========================================================
    # 2. LOAD DATA
    # ==========================================================
    X, y, feature_names, target_names, freqs = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type
    )

    X_test = X[0].reshape(1, -1)
    y_true = y[0].reshape(1, -1)

    # ==========================================================
    # 3. PREDICT
    # ==========================================================
    pred = predict_model(
        model_type=model_type,
        model_dir=model_dir,
        X_new=X_test
    )

    # ==========================================================
    # 4. DISPLAY
    # ==========================================================
    print("\n" + "=" * 60)
    print("PREDICTION SUMMARY")
    print("=" * 60)
    print(f"Model name: {model_name}")
    print(f"Model type: {model_type}")
    print(f"Translation type: {translation_type}")
    print(f"Input shape: {X_test.shape}")
    print(f"Target shape: {y_true.shape}")
    print(f"Prediction shape: {pred.shape}")
    print(f"Input feature names: {feature_names}")
    print(f"Target names: {target_names}")
    print(f"Number of frequency points: {len(freqs)}")

    print("\n" + "=" * 60)
    print("ORIGINAL VS PREDICTED")
    print("=" * 60)
    print("original:")
    print(y_true)
    print("\npredicted:")
    print(pred)


if __name__ == "__main__":
    example()