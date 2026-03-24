# LGBM.py

import os
import json
import time
import logging
import numpy as np
import psutil
import joblib
import lightgbm as lgb

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import (
    StandardScaler,
    MinMaxScaler,
    RobustScaler,
    MaxAbsScaler,
)

import data_translator
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
def get_data_split_config(config):
    split_cfg = config.get("data_split", {}) or {}

    test_size = float(split_cfg.get("test_size", 0.2))
    random_state = split_cfg.get("random_state", 42)

    if not (0.0 < test_size < 1.0):
        raise ValueError(f"data_split.test_size must be between 0 and 1, got {test_size}")

    return test_size, random_state


def get_lgb_params(config):
    params = dict(config.get("lgb_params", {}) or {})

    int_keys = [
        "n_estimators",
        "max_depth",
        "num_leaves",
        "min_child_samples",
        "subsample_freq",
        "random_state",
        "n_jobs",
        "verbose",
        "max_bin",
    ]
    float_keys = [
        "learning_rate",
        "subsample",
        "colsample_bytree",
        "reg_alpha",
        "reg_lambda",
        "min_split_gain",
        "min_child_weight",
    ]
    bool_keys = [
        "boost_from_average",
        "deterministic",
        "force_col_wise",
        "force_row_wise",
    ]

    for k in int_keys:
        if k in params and params[k] is not None:
            params[k] = int(params[k])

    for k in float_keys:
        if k in params and params[k] is not None:
            params[k] = float(params[k])

    for k in bool_keys:
        if k in params:
            params[k] = bool(params[k])

    if "objective" not in params:
        params["objective"] = "regression"

    return params


def _json_safe_lgb_params(params):
    out = {}
    for k, v in params.items():
        if isinstance(v, (np.integer, np.floating)):
            out[k] = v.item()
        else:
            out[k] = v
    return out


# ============================================================
# TRAIN MODEL
# ============================================================
def train_lgb_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    models = []

    for i in range(n_outputs):
        model = lgb.LGBMRegressor(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        logger.info(f"Trained LGBM for output {i + 1}/{n_outputs}")

    return models


# ============================================================
# PREDICT HELPERS
# ============================================================
def predict_lgb(models, feature_data):
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
    lgb_models,
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

    preds_norm = predict_lgb(lgb_models, f_test_eval)

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(t_test, preds)

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)
    system_info = report.get_system_info()

    model_files = [
        os.path.join(save_path, "lgb_models_list.pkl"),
        os.path.join(save_path, "config.json"),
    ]
    if f_scaler is not None:
        model_files.append(os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        model_files.append(os.path.join(save_path, "target_scaler.pkl"))

    model_size_bytes = sum(os.path.getsize(p) for p in model_files if os.path.exists(p))
    model_size_mb = round(model_size_bytes / (1024**2), 2)

    test_size, random_state = get_data_split_config(config)
    normalization_cfg = config.get("normalization", {}) or {}

    feature_norm_used = str(normalization_cfg.get("feature_method", "none")).lower() != "none"
    target_norm_used = str(normalization_cfg.get("target_method", "none")).lower() != "none"

    device_type = str(config.get("lgb_params", {}).get("device_type", "cpu")).lower()
    device = str(config.get("lgb_params", {}).get("device", device_type)).lower()
    gpu_used = ("gpu" in device) or ("gpu" in device_type)

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "lightgbm",
            "framework_version": lgb.__version__,
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
            "objective": str(config.get("lgb_params", {}).get("objective", "regression")),
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
            "gpu_used": gpu_used,
        },
        "configuration": {
            **config,
            "lgb_params": _json_safe_lgb_params(config.get("lgb_params", {})),
        },
    }

    return full_report


# ============================================================
# PIPELINE
# ============================================================
def train_model_pipeline(X, y, config, model_base_dir):
    test_size, random_state = get_data_split_config(config)

    # 1. Split dataset
    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    # 2. Normalize
    normalization_cfg = config.get("normalization", {}) or {}
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train,
        f_test,
        t_train,
        t_test,
        feature_method=normalization_cfg.get("feature_method", "none"),
        target_method=normalization_cfg.get("target_method", "none"),
    )

    # 3. Train LightGBM models
    lgb_params = get_lgb_params(config)

    start_time = time.time()
    lgb_models = train_lgb_models(f_train_n, t_train_n, lgb_params)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # 4. Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    joblib.dump(lgb_models, os.path.join(save_path, "lgb_models_list.pkl"))

    config_to_save = dict(config)
    config_to_save["lgb_params"] = _json_safe_lgb_params(config.get("lgb_params", {}))

    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=4)

    # 5. Generate report
    report_data = generate_report(
        lgb_models=lgb_models,
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
    logger.info("LightGBM training pipeline completed successfully.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new):
    """
    Predict using saved LightGBM models.

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

    model_file = os.path.join(model_dir, "lgb_models_list.pkl")
    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")

    if not os.path.exists(model_file):
        raise FileNotFoundError(f"Model file not found: {model_file}")

    lgb_models = joblib.load(model_file)
    f_scaler = joblib.load(f_scaler_file) if os.path.exists(f_scaler_file) else None
    t_scaler = joblib.load(t_scaler_file) if os.path.exists(t_scaler_file) else None

    if len(lgb_models) == 0:
        raise ValueError("Loaded LightGBM model list is empty.")

    expected_features = getattr(lgb_models[0], "n_features_in_", None)
    if expected_features is not None and X_new.shape[1] != expected_features:
        raise ValueError(
            f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
        )

    if f_scaler is not None:
        X_eval = f_scaler.transform(X_new)
    else:
        X_eval = X_new.astype(np.float32)

    y_pred_norm = predict_lgb(lgb_models, X_eval)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    return y_pred


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_LGBM",
        "model_type": "LGBM",
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "none",   # standard / minmax / robust / maxabs / none
            "target_method": "none",    # standard / minmax / robust / maxabs / none
        },
        "lgb_params": {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "max_depth": 6,
            "num_leaves": 31,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.0,
            "reg_lambda": 0.0,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
            "objective": "regression",
        },
    }

    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Quick test example
    # num_samples = 50
    # num_outputs = 100
    # train_model_pipeline(X[:num_samples], y[:num_samples, :num_outputs], train_config, MODEL_BASE_DIR)

    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)