# RF.py

import os
import json
import joblib
import time
import logging
import math
import numpy as np
import psutil

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import (
    StandardScaler,
    MinMaxScaler,
    RobustScaler,
    MaxAbsScaler,
)
from sklearn.ensemble import RandomForestRegressor

import report


# ============================================================
# LOGGER
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============================================================
# DATA SPLIT CONFIG
# ============================================================
def get_data_split_config(config):
    split_cfg = config.get("data_split", {}) or {}

    test_size = float(split_cfg.get("test_size", 0.2))
    random_state = split_cfg.get("random_state", 42)

    if not (0.0 < test_size < 1.0):
        raise ValueError(f"data_split.test_size must be between 0 and 1, got {test_size}")

    return test_size, random_state


# ============================================================
# NORMALIZATION
# ============================================================
def normalize_data_sets(
    feature_train,
    feature_test,
    target_train,
    target_test,
    feature_method="none",
    target_method="none",
):
    scalers = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler,
        "maxabs": MaxAbsScaler,
        "none": None,
    }

    feature_method = str(feature_method).strip().lower()
    target_method = str(target_method).strip().lower()

    if feature_method not in scalers:
        raise ValueError(f"Unsupported feature normalization method: {feature_method}")
    if target_method not in scalers:
        raise ValueError(f"Unsupported target normalization method: {target_method}")

    if scalers[feature_method] is None:
        f_scaler = None
        f_train_norm = np.asarray(feature_train, dtype=np.float64)
        f_test_norm = np.asarray(feature_test, dtype=np.float64)
    else:
        f_scaler = scalers[feature_method]()
        f_train_norm = f_scaler.fit_transform(feature_train)
        f_test_norm = f_scaler.transform(feature_test)

    if scalers[target_method] is None:
        t_scaler = None
        t_train_norm = np.asarray(target_train, dtype=np.float64)
        t_test_norm = np.asarray(target_test, dtype=np.float64)
    else:
        t_scaler = scalers[target_method]()
        t_train_norm = t_scaler.fit_transform(target_train)
        t_test_norm = t_scaler.transform(target_test)

    return f_train_norm, f_test_norm, t_train_norm, t_test_norm, f_scaler, t_scaler


# ============================================================
# CONFIG HELPERS
# ============================================================
def get_normalization_config(config):
    normalization_cfg = config.get("normalization", {}) or {}
    feature_method = normalization_cfg.get("feature_method", "none")
    target_method = normalization_cfg.get("target_method", "none")
    return feature_method, target_method


def get_rf_params(config):
    params = dict(config.get("rf_params", {}) or {})

    if "n_estimators" in params:
        params["n_estimators"] = int(params["n_estimators"])

    if "max_depth" in params and params["max_depth"] is not None:
        params["max_depth"] = int(params["max_depth"])

    if "min_samples_split" in params:
        val = params["min_samples_split"]
        params["min_samples_split"] = int(val) if isinstance(val, int) or (isinstance(val, float) and val >= 1) else float(val)

    if "min_samples_leaf" in params:
        val = params["min_samples_leaf"]
        params["min_samples_leaf"] = int(val) if isinstance(val, int) or (isinstance(val, float) and val >= 1) else float(val)

    if "n_jobs" in params and params["n_jobs"] is not None:
        params["n_jobs"] = int(params["n_jobs"])

    if "random_state" in params and params["random_state"] is not None:
        params["random_state"] = int(params["random_state"])

    if "bootstrap" in params:
        params["bootstrap"] = bool(params["bootstrap"])

    return params


# ============================================================
# JSON SANITIZER
# ============================================================
def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_json(x) for x in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


# ============================================================
# TRAIN MODEL
# ============================================================
def train_rf_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    models = []

    for i in range(n_outputs):
        model = RandomForestRegressor(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        logger.info(f"Trained RF for output {i + 1}/{n_outputs}")

    return models


# ============================================================
# PREDICT HELPERS
# ============================================================
def predict_rf(models, feature_data):
    n_samples = feature_data.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs), dtype=np.float64)

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_data)

    return predictions


# ============================================================
# REPORT
# ============================================================
def generate_report(
    rf_models,
    f_train,
    f_test,
    t_train,
    t_test,
    f_scaler,
    t_scaler,
    config,
    train_duration,
    save_path,
):
    if f_scaler is not None:
        f_test_eval = f_scaler.transform(f_test)
    else:
        f_test_eval = np.asarray(f_test, dtype=np.float64)

    preds_norm = predict_rf(rf_models, f_test_eval)

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(t_test, preds)

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024 ** 3), 2)
    system_info = report.get_system_info()

    model_files = [
        os.path.join(save_path, "rf_models_list.pkl"),
        os.path.join(save_path, "config.json"),
        os.path.join(save_path, "feature_scaler.pkl"),
        os.path.join(save_path, "target_scaler.pkl"),
    ]
    model_size_bytes = sum(os.path.getsize(p) for p in model_files if os.path.exists(p))
    model_size_mb = round(model_size_bytes / (1024 ** 2), 2)

    test_size, random_state = get_data_split_config(config)
    feature_method, target_method = get_normalization_config(config)

    feature_norm_used = str(feature_method).lower() != "none"
    target_norm_used = str(target_method).lower() != "none"

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "scikit-learn",
            "framework_version": None,
            "trainable_outputs": t_train.shape[1],
            "training_duration_sec": train_duration,
            "model_size_mb": model_size_mb,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "data_info": {
            "input_dim": f_train.shape[1],
            "output_dim": t_train.shape[1],
            "total_samples": f_train.shape[0] + f_test.shape[0],
            "train_samples": f_train.shape[0],
            "test_samples": f_test.shape[0],
            "split_strategy": "train_test_split",
            "test_size": test_size,
            "random_state": random_state,
        },
        "training_summary": {
            "n_outputs": t_train.shape[1],
            "n_estimators": config.get("rf_params", {}).get("n_estimators"),
            "max_depth": config.get("rf_params", {}).get("max_depth"),
        },
        "performance": {
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "evaluation_dataset": "held-out test set",
                "predictions_inverse_transformed": target_norm_used,
                "normalization_used": feature_norm_used or target_norm_used,
                "feature_normalization_used": feature_norm_used,
                "target_normalization_used": target_norm_used,
            },
        },
        "system_info": system_info,
        "hardware_info": {
            "peak_process_ram_gb": peak_ram_gb,
            "gpu_used": False,
        },
        "configuration": config,
    }

    return sanitize_json(full_report)


# ============================================================
# TRAINING PIPELINE
# ============================================================
def train_model_pipeline(X, y, config, model_base_dir):
    test_size, random_state = get_data_split_config(config)
    feature_method, target_method = get_normalization_config(config)

    # 1. Split
    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    # 2. Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train,
        f_test,
        t_train,
        t_test,
        feature_method=feature_method,
        target_method=target_method,
    )

    # 3. Train
    rf_params = get_rf_params(config)

    start_time = time.time()
    rf_models = train_rf_models(f_train_n, t_train_n, rf_params)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # 4. Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    joblib.dump(rf_models, os.path.join(save_path, "rf_models_list.pkl"))

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))

    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    config_to_save = dict(config)
    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=4)

    # 5. Report
    report_data = generate_report(
        rf_models=rf_models,
        f_train=f_train,
        f_test=f_test,
        t_train=t_train,
        t_test=t_test,
        f_scaler=f_scaler,
        t_scaler=t_scaler,
        config=config_to_save,
        train_duration=train_duration,
        save_path=save_path,
    )

    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)

    logger.info("Random Forest training pipeline completed successfully.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new):
    """
    Predict using saved Random Forest models.

    Parameters
    ----------
    model_dir : str
        Path to the saved model directory.
    X_new : np.ndarray
        Input features with shape (n_samples, n_features) or (n_features,).

    Returns
    -------
    np.ndarray
        Predictions with shape (n_samples, n_outputs).
    """
    X_new = np.asarray(X_new, dtype=np.float64)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    model_file = os.path.join(model_dir, "rf_models_list.pkl")
    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")

    if not os.path.exists(model_file):
        raise FileNotFoundError(f"RF model file not found: {model_file}")

    rf_models = joblib.load(model_file)
    f_scaler = joblib.load(f_scaler_file) if os.path.exists(f_scaler_file) else None
    t_scaler = joblib.load(t_scaler_file) if os.path.exists(t_scaler_file) else None

    if len(rf_models) == 0:
        raise ValueError("Loaded RF model list is empty.")

    if f_scaler is not None:
        expected_features = getattr(f_scaler, "n_features_in_", None)
        if expected_features is not None and X_new.shape[1] != expected_features:
            raise ValueError(
                f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
            )
        X_eval = f_scaler.transform(X_new)
    else:
        expected_features = getattr(rf_models[0], "n_features_in_", None)
        if expected_features is not None and X_new.shape[1] != expected_features:
            raise ValueError(
                f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
            )
        X_eval = X_new

    y_pred_norm = predict_rf(rf_models, X_eval)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    return y_pred


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import data_translator

    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_RF_SIMPLE",
        "model_type": "RF",
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "none",
            "target_method": "none",
        },
        "rf_params": {
            "n_estimators": 200,
            "max_depth": 20,
            "min_samples_split": 5,
            "min_samples_leaf": 5,
            "max_features": "sqrt",
            "bootstrap": True,
            "random_state": 42,
            "n_jobs": -1,
        },
    }

    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    num_samples = 100
    num_outputs = 10

    train_model_pipeline(
        X[:num_samples],
        y[:num_samples, :num_outputs],
        train_config,
        MODEL_BASE_DIR,
    )