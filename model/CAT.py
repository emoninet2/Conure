# CAT.py

import os
import json
import joblib
import time
import logging
import numpy as np
import psutil

from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import (
    StandardScaler,
    MinMaxScaler,
    RobustScaler,
    MaxAbsScaler,
)

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

    # Feature scaling
    if scalers[feature_method] is None:
        f_scaler = None
        f_train_norm = np.asarray(feature_train, dtype=np.float64)
        f_test_norm = np.asarray(feature_test, dtype=np.float64)
    else:
        f_scaler = scalers[feature_method]()
        f_train_norm = f_scaler.fit_transform(feature_train)
        f_test_norm = f_scaler.transform(feature_test)

    # Target scaling
    if scalers[target_method] is None:
        t_scaler = None
        t_train_norm = np.asarray(target_train, dtype=np.float64)
        t_test_norm = np.asarray(target_test, dtype=np.float64)
    else:
        t_scaler = scalers[target_method]()
        t_train_norm = t_scaler.fit_transform(target_train)
        t_test_norm = t_scaler.transform(target_test)

    return f_train_norm, f_test_norm, t_train_norm, t_test_norm, f_scaler, t_scaler


def get_normalization_config(config):
    normalization_cfg = config.get("normalization", {}) or {}
    feature_method = normalization_cfg.get("feature_method", "none")
    target_method = normalization_cfg.get("target_method", "none")
    return feature_method, target_method


# ============================================================
# PARAM HELPERS
# ============================================================
def get_cat_params(config):
    params = dict(config.get("cat_params", {}) or {})

    int_fields = [
        "iterations",
        "depth",
        "random_seed",
        "border_count",
        "min_data_in_leaf",
        "max_leaves",
    ]
    float_fields = [
        "learning_rate",
        "l2_leaf_reg",
        "random_strength",
        "bagging_temperature",
    ]
    bool_fields = [
        "verbose",
    ]

    for key in int_fields:
        if key in params and params[key] is not None:
            params[key] = int(params[key])

    for key in float_fields:
        if key in params and params[key] is not None:
            params[key] = float(params[key])

    for key in bool_fields:
        if key in params and isinstance(params[key], bool):
            params[key] = bool(params[key])

    if "loss_function" in params and params["loss_function"] is not None:
        params["loss_function"] = str(params["loss_function"])

    if "eval_metric" in params and params["eval_metric"] is not None:
        params["eval_metric"] = str(params["eval_metric"])

    if "task_type" in params and params["task_type"] is not None:
        params["task_type"] = str(params["task_type"]).upper()

    if "devices" in params and params["devices"] is not None:
        params["devices"] = str(params["devices"])

    return params


# ============================================================
# MODEL TRAINING
# ============================================================
def train_cat_models(feature_train, target_train, config, save_path):
    """
    Train separate CatBoost models for each output dimension.
    """
    n_outputs = target_train.shape[1]
    models = []
    params = get_cat_params(config)

    # Dedicated folder for CatBoost internal logs
    catboost_info_dir = os.path.join(save_path, "catboost_info")
    os.makedirs(catboost_info_dir, exist_ok=True)
    params["train_dir"] = catboost_info_dir

    for i in range(n_outputs):
        model = CatBoostRegressor(**params)
        model.fit(feature_train, target_train[:, i], verbose=False)
        models.append(model)
        logger.info(f"Trained CatBoost for output {i + 1}/{n_outputs}")

    return models


# ============================================================
# PREDICT HELPERS
# ============================================================
def predict_cat(models, feature_data):
    n_samples = feature_data.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs), dtype=np.float64)

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_data)

    return predictions


# ============================================================
# REPORT GENERATION
# ============================================================
def generate_report(
    cat_models,
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

    preds_norm = predict_cat(cat_models, f_test_eval)

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(t_test, preds)

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024 ** 3), 2)

    total_samples = f_train.shape[0] + f_test.shape[0]

    model_files = [
        os.path.join(save_path, "cat_models_list.pkl"),
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

    cat_params = config.get("cat_params", {}) or {}
    task_type = str(cat_params.get("task_type", "")).upper()
    gpu_used = task_type == "GPU"

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "CatBoost",
            "framework_version": None,
            "trainable_outputs": t_train.shape[1],
            "training_duration_sec": train_duration,
            "model_size_mb": model_size_mb,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "data_info": {
            "input_dim": f_train.shape[1],
            "output_dim": t_train.shape[1],
            "total_samples": total_samples,
            "train_samples": f_train.shape[0],
            "test_samples": f_test.shape[0],
            "split_strategy": "train_test_split",
            "test_size": test_size,
            "random_state": random_state,
        },
        "training_summary": {
            "iterations": cat_params.get("iterations"),
            "learning_rate": cat_params.get("learning_rate"),
            "depth": cat_params.get("depth"),
            "n_outputs": t_train.shape[1],
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
        "system_info": report.get_system_info(),
        "hardware_info": {
            "gpu_utilized": gpu_used,
            "gpu_count": 1 if gpu_used else 0,
            "gpu_details": "GPU Mode" if gpu_used else "CPU Mode",
            "peak_process_ram_gb": peak_ram_gb,
        },
        "configuration": config,
    }

    return full_report


# ============================================================
# TRAINING PIPELINE
# ============================================================
def train_model_pipeline(X, y, config, model_base_dir):
    test_size, random_state = get_data_split_config(config)
    feature_method, target_method = get_normalization_config(config)

    # 1. Split data
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

    # 3. Prepare save folder
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    # 4. Train
    start_time = time.time()
    cat_models = train_cat_models(f_train_n, t_train_n, config, save_path)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # 5. Save artifacts
    joblib.dump(cat_models, os.path.join(save_path, "cat_models_list.pkl"))

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))

    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    config_to_save = dict(config)
    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=4)

    # 6. Generate & save report
    report_data = generate_report(
        cat_models=cat_models,
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
    report.log_metric(
        report_data["performance"]["metrics"],
        config["model_type"],
        logger,
    )

    logger.info("CatBoost training pipeline completed successfully.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new):
    """
    Predict using saved CatBoost models.

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
    X_new = np.asarray(X_new, dtype=np.float32)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    model_file = os.path.join(model_dir, "cat_models_list.pkl")
    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")

    if not os.path.exists(model_file):
        raise FileNotFoundError(f"Model file not found: {model_file}")

    cat_models = joblib.load(model_file)
    f_scaler = joblib.load(f_scaler_file) if os.path.exists(f_scaler_file) else None
    t_scaler = joblib.load(t_scaler_file) if os.path.exists(t_scaler_file) else None

    if len(cat_models) == 0:
        raise ValueError("Loaded CatBoost model list is empty.")

    if f_scaler is not None:
        expected_features = getattr(f_scaler, "n_features_in_", None)
        if expected_features is not None and X_new.shape[1] != expected_features:
            raise ValueError(
                f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
            )
        X_eval = f_scaler.transform(X_new)
    else:
        expected_features = getattr(cat_models[0], "feature_count_", None)
        if expected_features is not None and X_new.shape[1] != expected_features:
            raise ValueError(
                f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
            )
        X_eval = X_new

    y_pred_norm = predict_cat(cat_models, X_eval)

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
        "model_name": "TX11_CAT",
        "model_type": "CAT",
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "none",
            "target_method": "none",
        },
        "cat_params": {
            "iterations": 1000,
            "learning_rate": 0.05,
            "depth": 6,
            "l2_leaf_reg": 3,
            "random_seed": 42,
            "loss_function": "RMSE",
            "task_type": "GPU",   # use "CPU" if needed
            "devices": "0",
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