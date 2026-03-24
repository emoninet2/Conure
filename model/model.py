import os
import sys
import json
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
# TRANSLATION DISPATCH
# ==========================================================
TRANSLATORS = {
    # ------------------------------------------------------
    # Original S-parameter translators
    # ------------------------------------------------------
    "ffi": data_translator.prepare_ffi_data,
    "ffi_augmented": data_translator.prepare_ffi_augmented,
    "ffd": data_translator.prepare_ffd_data,
    "ffd_augmented": data_translator.prepare_ffd_augmented,
    "ifi": data_translator.prepare_ifi_data,
    "ifi_augmented": data_translator.prepare_ifi_augmented,
    "ifd": data_translator.prepare_ifd_data,
    "ifd_augmented": data_translator.prepare_ifd_augmented,

    # ------------------------------------------------------
    # Inductor translators
    # ------------------------------------------------------
    "ffi_inductor": data_translator.prepare_ffi_inductor_data,
    "ffi_inductor_augmented": data_translator.prepare_ffi_inductor_augmented,
    "ffd_inductor": data_translator.prepare_ffd_inductor_data,
    "ffd_inductor_augmented": data_translator.prepare_ffd_inductor_augmented,
    "ifi_inductor": data_translator.prepare_ifi_inductor_data,
    "ifi_inductor_augmented": data_translator.prepare_ifi_inductor_augmented,
    "ifd_inductor": data_translator.prepare_ifd_inductor_data,
    "ifd_inductor_augmented": data_translator.prepare_ifd_inductor_augmented,

    # ------------------------------------------------------
    # Transformer translators
    # ------------------------------------------------------
    "ffi_transformer": data_translator.prepare_ffi_transformer_data,
    "ffi_transformer_augmented": data_translator.prepare_ffi_transformer_augmented,
    "ffd_transformer": data_translator.prepare_ffd_transformer_data,
    "ffd_transformer_augmented": data_translator.prepare_ffd_transformer_augmented,
    "ifi_transformer": data_translator.prepare_ifi_transformer_data,
    "ifi_transformer_augmented": data_translator.prepare_ifi_transformer_augmented,
    "ifd_transformer": data_translator.prepare_ifd_transformer_data,
    "ifd_transformer_augmented": data_translator.prepare_ifd_transformer_augmented,
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
        with open(train_config, "r", encoding="utf-8") as f:
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


def get_translator(translation_type):
    translation_key = str(translation_type).strip().lower()

    if translation_key not in TRANSLATORS:
        raise ValueError(
            f"Unsupported translation_type '{translation_type}'. "
            f"Supported values: {list(TRANSLATORS.keys())}"
        )

    return TRANSLATORS[translation_key]


def filter_translation_params(translator_fn, translation_params=None):
    """
    Keep only parameters actually accepted by the translator function.
    """
    translation_params = translation_params or {}
    sig = inspect.signature(translator_fn)
    allowed_params = sig.parameters

    return {
        k: v for k, v in translation_params.items()
        if k in allowed_params
    }


def load_translated_data(npz_file, translation_type, translation_params=None):
    """
    Load translated dataset using any registered translator.
    """
    if not os.path.exists(npz_file):
        raise FileNotFoundError(f"NPZ data file not found: {npz_file}")

    translator_fn = get_translator(translation_type)
    filtered_params = filter_translation_params(translator_fn, translation_params)

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

    model_type = str(config["model_type"]).strip().upper()
    model_module = get_model_module(model_type)

    os.makedirs(output_dir, exist_ok=True)

    X, y, _, _, _ = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type,
        translation_params=translation_params,
    )

    # All model modules, including PCE, now use the same interface
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
    npz_file = "/mnt/storage/emon/projects/Conure/data/2026/TX11/simulation_data.npz"
    output_dir = "./data/MAGIC"

    model_type = "ANN"

    # Examples:
    # translation_type = "FFD"
    # translation_type = "FFD_Inductor"
    translation_type = "FFD_Transformer"

    model_name = f"{model_type}_{translation_type}"
    model_dir = os.path.join(output_dir, model_name)

    train_config = {
        "model_name": model_name,
        "model_type": model_type,
        "translation_params": {
            "z0": 50.0,
            "feature_noise_std": 0.01,
            "target_noise_std": 0.005,
            "n_augment": 3,
            "clip": True,
        },
        "normalization": {
            "feature_method": "standard",
            "target_method": "standard",
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
                "momentum": 0.9,
            },
        },
        "early_stopping": {
            "monitor": "val_loss",
            "patience": 15,
            "restore_best_weights": True,
        },
        "architecture": [
            {
                "type": "Dense",
                "units": 128,
                "activation": "relu",
                "regularizer": {"type": "l2", "value": 0.01},
            },
            {"type": "Dropout", "rate": 0.1},
            {
                "type": "Dense",
                "units": 512,
                "activation": "relu",
                "regularizer": {"type": "l1_l2", "l1": 0.001, "l2": 0.01},
            },
            {"type": "Dense", "units": "AUTO", "activation": "linear"},
        ],
    }

    # ------------------------------------------------------
    # Train
    # ------------------------------------------------------
    train_model(
        npz_file=npz_file,
        translation_type=translation_type,
        train_config=train_config,
        output_dir=output_dir,
    )
    print("Training completed.")

    # ------------------------------------------------------
    # Load translated data
    # ------------------------------------------------------
    X, y, feature_names, target_names, freqs = load_translated_data(
        npz_file=npz_file,
        translation_type=translation_type,
        translation_params={"z0": 50.0},
    )

    X_test = X[0].reshape(1, -1)
    y_true = y[0].reshape(1, -1)

    # ------------------------------------------------------
    # Predict
    # ------------------------------------------------------
    pred = predict_model(
        model_type=model_type,
        model_dir=model_dir,
        X_new=X_test,
    )

    # ------------------------------------------------------
    # Display
    # ------------------------------------------------------
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