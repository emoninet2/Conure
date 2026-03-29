# SVR.py

import os
import json
import joblib
import time
import logging
import numpy as np
import psutil

from sklearn.model_selection import train_test_split
from sklearn.svm import SVR

import normalization
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
# CONFIG HELPERS
# ============================================================
def get_data_split_config(config):
    split_cfg = config.get("data_split", {}) or {}

    test_size = float(split_cfg.get("test_size", 0.2))
    random_state = split_cfg.get("random_state", 42)

    if not (0.0 < test_size < 1.0):
        raise ValueError(f"data_split.test_size must be between 0 and 1, got {test_size}")

    return test_size, random_state


def get_svr_params(config):
    params = dict(config.get("svr_params", {}) or {})

    if "kernel" in params:
        params["kernel"] = str(params["kernel"]).strip().lower()

    if "C" in params:
        params["C"] = float(params["C"])

    if "epsilon" in params:
        params["epsilon"] = float(params["epsilon"])

    if "degree" in params:
        params["degree"] = int(params["degree"])

    if "coef0" in params:
        params["coef0"] = float(params["coef0"])

    if "tol" in params:
        params["tol"] = float(params["tol"])

    if "cache_size" in params:
        params["cache_size"] = float(params["cache_size"])

    if "shrinking" in params:
        params["shrinking"] = bool(params["shrinking"])

    if "max_iter" in params:
        params["max_iter"] = int(params["max_iter"])

    return params


# ============================================================
# TRAIN
# ============================================================
def train_svr_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    models = []

    for i in range(n_outputs):
        model = SVR(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        logger.info(f"Trained SVR for output {i + 1}/{n_outputs}")

    return models


# ============================================================
# PREDICT HELPERS
# ============================================================
def predict_svr(models, feature_data):
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
    svr_models,
    f_train,
    f_test,
    t_train,
    t_test,
    f_scaler,
    t_scaler,
    config,
    train_duration,
    save_path,
    feature_names=None,
    target_names=None,
):
    if f_scaler is not None:
        f_test_eval = f_scaler.transform(f_test)
    else:
        f_test_eval = np.asarray(f_test, dtype=np.float64)

    preds_norm = predict_svr(svr_models, f_test_eval)

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(t_test, preds)

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)

    model_files = [
        os.path.join(save_path, "svr_models_list.pkl"),
        os.path.join(save_path, "config.json"),
    ]

    if f_scaler is not None:
        model_files.append(os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        model_files.append(os.path.join(save_path, "target_scaler.pkl"))

    model_size_bytes = sum(os.path.getsize(p) for p in model_files if os.path.exists(p))
    model_size_mb = round(model_size_bytes / (1024**2), 2)

    test_size, random_state = get_data_split_config(config)
    feature_norm_used, target_norm_used = normalization.normalization_usage_flags(
        config,
        n_features=int(f_train.shape[1]),
        n_targets=int(t_train.shape[1]),
        feature_default="standard",
        target_default="standard",
    )

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "scikit-learn",
            "framework_version": None,
            "trainable_outputs": t_train.shape[1],
            "model_size_mb": model_size_mb,
            "training_duration_sec": train_duration,
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
            "observed_ranges": report.observed_ranges_for_report(
                f_train, f_test, t_train, t_test, feature_names, target_names
            ),
        },
        "training_summary": {
            "kernel": str(config.get("svr_params", {}).get("kernel", "rbf")),
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
            "peak_process_ram_gb": peak_ram_gb,
        },
        "configuration": config,
    }

    return full_report


# ============================================================
# TRAINING PIPELINE
# ============================================================
def train_model_pipeline(X, y, config, model_base_dir, feature_names=None, target_names=None):
    test_size, random_state = get_data_split_config(config)

    # 1. Split
    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    # 2. Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalization.normalize_train_test_split(
        config,
        f_train,
        f_test,
        t_train,
        t_test,
        feature_default="standard",
        target_default="standard",
    )

    # 3. Train
    svr_params = get_svr_params(config)

    start_time = time.time()
    svr_models = train_svr_models(f_train_n, t_train_n, svr_params)
    train_duration = time.time() - start_time
    logger.info(f"SVR training completed in {train_duration:.2f} seconds.")

    # 4. Save artifacts
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    joblib.dump(svr_models, os.path.join(save_path, "svr_models_list.pkl"))

    config_to_save = dict(config)
    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=4)

    # 5. Generate & save report
    report_data = generate_report(
        svr_models=svr_models,
        f_train=f_train,
        f_test=f_test,
        t_train=t_train,
        t_test=t_test,
        f_scaler=f_scaler,
        t_scaler=t_scaler,
        config=config_to_save,
        train_duration=train_duration,
        save_path=save_path,
        feature_names=feature_names,
        target_names=target_names,
    )

    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)

    logger.info("SVR pipeline completed successfully.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new):
    """
    Predict using saved SVR models.

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

    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")
    model_file = os.path.join(model_dir, "svr_models_list.pkl")

    if not os.path.exists(model_file):
        raise FileNotFoundError(f"SVR model file not found: {model_file}")

    f_scaler = joblib.load(f_scaler_file) if os.path.exists(f_scaler_file) else None
    t_scaler = joblib.load(t_scaler_file) if os.path.exists(t_scaler_file) else None
    svr_models = joblib.load(model_file)

    if len(svr_models) == 0:
        raise ValueError("Loaded SVR model list is empty.")

    if f_scaler is not None:
        expected_features = getattr(f_scaler, "n_features_in_", None)
    else:
        expected_features = getattr(svr_models[0], "n_features_in_", None)

    if expected_features is not None and X_new.shape[1] != expected_features:
        raise ValueError(
            f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
        )

    if f_scaler is not None:
        X_norm = f_scaler.transform(X_new)
    else:
        X_norm = X_new.astype(np.float64)

    y_pred_norm = predict_svr(svr_models, X_norm)

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
        "model_name": "TX11_SVR",
        "model_type": "SVR",
        "normalization": {
            "feature_method": "standard",   # standard / minmax / robust / maxabs / none
            "target_method": "standard",    # standard / minmax / robust / maxabs / none
        },
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "svr_params": {
            "kernel": "rbf",
            "C": 100.0,
            "epsilon": 0.001,
            "gamma": "scale",
        },
    }

    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)