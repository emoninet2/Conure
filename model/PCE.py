# PCE.py

import os
import json
import time
import joblib
import numpy as np
import psutil
import logging

from numpy.polynomial.legendre import legval
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

import normalization
import report


# ============================================================
# LOGGER
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
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
# PCE BASIS
# ============================================================
def build_legendre_basis(X, degree):
    """
    Build a simple per-feature Legendre basis:
      [1, P1(x1), P1(x2), ..., P2(x1), P2(x2), ...]
    """
    X = np.asarray(X, dtype=np.float64)

    basis_list = [np.ones((X.shape[0], 1), dtype=np.float64)]
    for d in range(1, degree + 1):
        for j in range(X.shape[1]):
            coeff = [0] * d + [1]
            col = legval(X[:, j], coeff).reshape(-1, 1)
            basis_list.append(col)

    return np.hstack(basis_list)


# ============================================================
# PCE MODEL TRAINING
# ============================================================
def train_pce_models(feature_train, target_train, degree=3):
    n_outputs = target_train.shape[1]
    models = []
    X_basis = build_legendre_basis(feature_train, degree)

    for i in range(n_outputs):
        model = LinearRegression()
        model.fit(X_basis, target_train[:, i])
        models.append(model)
        logger.info(f"Trained PCE for output {i + 1}/{n_outputs}")

    return models


# ============================================================
# PCE PREDICTION
# ============================================================
def predict_pce(models, feature_data, degree=3):
    X_basis = build_legendre_basis(feature_data, degree)
    predictions = np.zeros((feature_data.shape[0], len(models)), dtype=np.float64)

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(X_basis)

    return predictions


# ============================================================
# HELPERS
# ============================================================
def _ensure_2d_array(name, value):
    arr = np.asarray(value, dtype=np.float64)

    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)

    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2D. Got shape {arr.shape}")

    if np.isnan(arr).any():
        raise ValueError(f"{name} contains NaN values.")

    return arr


def _get_degree(train_config):
    degree = int(train_config.get("degree", 3))
    if degree < 1:
        raise ValueError("degree must be >= 1")
    return degree


def _save_training_artifacts(save_path, models, f_scaler, t_scaler, train_config):
    os.makedirs(save_path, exist_ok=True)

    joblib.dump(models, os.path.join(save_path, "models.pkl"))

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))

    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(train_config, f, indent=4)


def _compute_model_size_mb(save_path):
    artifact_files = [
        os.path.join(save_path, "models.pkl"),
        os.path.join(save_path, "config.json"),
        os.path.join(save_path, "feature_scaler.pkl"),
        os.path.join(save_path, "target_scaler.pkl"),
    ]

    total_bytes = 0
    for path in artifact_files:
        if os.path.exists(path):
            total_bytes += os.path.getsize(path)

    return round(total_bytes / (1024 ** 2), 2)


# ============================================================
# PCE REPORT
# ============================================================
def generate_pce_report(
    models,
    X_train,
    X_test,
    y_train,
    y_test,
    f_scaler,
    t_scaler,
    params,
    train_duration,
    save_path,
    model_name="PCE_MODEL",
):
    degree = _get_degree(params)
    test_size, random_state = get_data_split_config(params)
    feature_norm_used, target_norm_used = normalization.normalization_usage_flags(
        params,
        n_features=int(X_train.shape[1]),
        n_targets=int(y_train.shape[1]),
        feature_default="standard",
        target_default="standard",
    )

    if f_scaler is not None:
        X_test_eval = f_scaler.transform(X_test)
    else:
        X_test_eval = np.asarray(X_test, dtype=np.float64)

    preds_norm = predict_pce(models, X_test_eval, degree=degree)

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(y_test, preds)

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024 ** 3), 2)
    sys_info = report.get_system_info()

    total_samples = X_train.shape[0] + X_test.shape[0]
    train_samples = X_train.shape[0]
    test_samples = X_test.shape[0]

    total_model_size_mb = _compute_model_size_mb(save_path)

    full_report = {
        "model_info": {
            "model_name": model_name,
            "model_type": "PCE",
            "framework": "scikit-learn",
            "framework_version": None,
            "trainable_parameters": int(sum(m.coef_.size + 1 for m in models)),
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_size_mb": total_model_size_mb,
        },
        "data_info": {
            "input_dim": int(X_train.shape[1]),
            "output_dim": int(y_train.shape[1]),
            "total_samples": int(total_samples),
            "train_samples": int(train_samples),
            "validation_samples": 0,
            "test_samples": int(test_samples),
            "split_strategy": "train_test_split",
            "test_size": test_size,
            "random_state": random_state,
        },
        "training_summary": {
            "degree": degree,
            "n_outputs": int(y_train.shape[1]),
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
        "system_info": sys_info,
        "hardware_info": {
            "cpu_utilized": True,
            "peak_process_ram_gb": peak_ram_gb,
        },
        "configuration": params,
    }

    return full_report


# ============================================================
# PCE PIPELINE
# ============================================================
def train_model_pipeline(X, y, train_config, model_base_dir):
    """
    Unified PCE training interface.

    Same style as the other model modules:
        train_model_pipeline(X, y, config, output_dir)
    """
    X = _ensure_2d_array("X", X)
    y = _ensure_2d_array("y", y)

    if "model_name" not in train_config:
        raise KeyError("train_config must contain 'model_name'.")

    degree = _get_degree(train_config)
    test_size, random_state = get_data_split_config(train_config)

    # 1. Split
    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    # 2. Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalization.normalize_train_test_split(
        train_config,
        f_train,
        f_test,
        t_train,
        t_test,
        feature_default="standard",
        target_default="standard",
    )

    # 3. Train
    start_time = time.time()
    models = train_pce_models(f_train_n, t_train_n, degree=degree)
    train_duration = time.time() - start_time
    logger.info(f"PCE training completed in {train_duration:.2f} seconds.")

    # 4. Save
    save_path = os.path.join(model_base_dir, train_config["model_name"])
    _save_training_artifacts(save_path, models, f_scaler, t_scaler, train_config)

    # 5. Report
    report_data = generate_pce_report(
        models=models,
        X_train=f_train,
        X_test=f_test,
        y_train=t_train,
        y_test=t_test,
        f_scaler=f_scaler,
        t_scaler=t_scaler,
        params=train_config,
        train_duration=train_duration,
        save_path=save_path,
        model_name=train_config["model_name"],
    )

    report.save_report(report_data, save_path)
    report.log_metric(
        report_data["performance"]["metrics"],
        train_config.get("model_type", "PCE"),
        logger,
    )
    logger.info("PCE pipeline finished successfully.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new):
    """
    Predict using saved PCE models.

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

    if X_new.ndim != 2:
        raise ValueError(f"X_new must be 2D. Got shape {X_new.shape}")

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    model_file = os.path.join(model_dir, "models.pkl")
    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")
    config_file = os.path.join(model_dir, "config.json")

    if not os.path.exists(model_file):
        raise FileNotFoundError(f"PCE models not found: {model_file}")

    models = joblib.load(model_file)
    f_scaler = joblib.load(f_scaler_file) if os.path.exists(f_scaler_file) else None
    t_scaler = joblib.load(t_scaler_file) if os.path.exists(t_scaler_file) else None

    degree = 3
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            degree = int(config.get("degree", 3))

    if f_scaler is not None:
        expected_features = getattr(f_scaler, "n_features_in_", None)
        if expected_features is not None and X_new.shape[1] != expected_features:
            raise ValueError(
                f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
            )
        X_eval = f_scaler.transform(X_new)
    else:
        X_eval = X_new

    y_pred_norm = predict_pce(models, X_eval, degree=degree)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    return y_pred


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("PCE.py is now a model module and should be called from the unified trainer.")