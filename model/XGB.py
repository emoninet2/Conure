# XGB.py

import os
import json
import joblib
import time
import logging
import numpy as np
import xgboost as xgb
import psutil

from sklearn.model_selection import train_test_split

import data_translator
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


def get_xgb_params(config):
    params = dict(config.get("xgb_params", {}) or {})

    int_keys = [
        "n_estimators",
        "max_depth",
        "max_leaves",
        "max_bin",
        "num_parallel_tree",
        "random_state",
        "n_jobs",
        "verbosity",
    ]
    float_keys = [
        "learning_rate",
        "subsample",
        "colsample_bytree",
        "colsample_bylevel",
        "colsample_bynode",
        "gamma",
        "min_child_weight",
        "reg_alpha",
        "reg_lambda",
        "scale_pos_weight",
        "base_score",
    ]
    bool_keys = [
        "enable_categorical",
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
        params["objective"] = "reg:squarederror"

    if "eval_metric" not in params:
        params["eval_metric"] = "rmse"

    return params


def _json_safe_xgb_params(params):
    out = {}
    for k, v in params.items():
        if isinstance(v, (np.integer, np.floating)):
            out[k] = v.item()
        else:
            out[k] = v
    return out


# ============================================================
# TRAIN XGBOOST
# ============================================================
def train_xgb_models(feature_train, target_train, feature_val, target_val, config):
    n_outputs = target_train.shape[1]
    models = []
    histories = {}

    params = get_xgb_params(config)

    for i in range(n_outputs):
        model = xgb.XGBRegressor(**params)

        eval_set = [
            (feature_train, target_train[:, i]),
            (feature_val, target_val[:, i]),
        ]

        model.fit(
            feature_train,
            target_train[:, i],
            eval_set=eval_set,
            verbose=False,
        )

        models.append(model)
        histories[f"output_{i}"] = model.evals_result()
        logger.info(f"Trained XGB for output {i + 1}/{n_outputs}")

    return models, histories


# ============================================================
# REPORT
# ============================================================
def generate_report(
    xgb_models,
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

    preds_norm = np.zeros((f_test_eval.shape[0], len(xgb_models)), dtype=np.float64)
    for i, model in enumerate(xgb_models):
        preds_norm[:, i] = model.predict(f_test_eval)

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(t_test, preds)
    system_info = report.get_system_info()

    process = psutil.Process(os.getpid())
    peak_ram = round(process.memory_info().rss / (1024**3), 2)

    model_files = [
        os.path.join(save_path, "xgb_models_list.pkl"),
        os.path.join(save_path, "config.json"),
        os.path.join(save_path, "history.json"),
    ]
    if f_scaler is not None:
        model_files.append(os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        model_files.append(os.path.join(save_path, "target_scaler.pkl"))

    model_size_mb = round(
        sum(os.path.getsize(p) for p in model_files if os.path.exists(p)) / (1024**2),
        2,
    )

    test_size, random_state = get_data_split_config(config)
    feature_norm_used, target_norm_used = normalization.normalization_usage_flags(
        config,
        n_features=int(f_train.shape[1]),
        n_targets=int(t_train.shape[1]),
        feature_default="none",
        target_default="none",
    )

    device = str(config.get("xgb_params", {}).get("device", "cpu")).lower()

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "xgboost",
            "framework_version": xgb.__version__,
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
            "observed_ranges": report.observed_ranges_for_report(
                f_train, f_test, t_train, t_test, feature_names, target_names
            ),
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
            "peak_process_ram_gb": peak_ram,
            "gpu_used": device != "cpu",
        },
        "configuration": {
            **config,
            "xgb_params": _json_safe_xgb_params(config.get("xgb_params", {})),
        },
    }

    return full_report


# ============================================================
# TRAINING PIPELINE
# ============================================================
def train_model_pipeline(X, y, config, model_base_dir, feature_names=None, target_names=None):
    max_threads = config.get("max_cpu_threads")
    if max_threads:
        max_threads = int(max_threads)
        os.environ["OMP_NUM_THREADS"] = str(max_threads)
        os.environ["MKL_NUM_THREADS"] = str(max_threads)
        os.environ["NUMEXPR_NUM_THREADS"] = str(max_threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(max_threads)
        logger.info(f"CPU threads limited to {max_threads}")

    test_size, random_state = get_data_split_config(config)

    # 1. Split data
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
        feature_default="none",
        target_default="none",
    )

    # 3. Train models
    device = str(config.get("xgb_params", {}).get("device", "cpu"))
    logger.info(f"Starting XGBoost training for {y.shape[1]} outputs on {device}...")

    start_time = time.time()
    xgb_models, histories = train_xgb_models(f_train_n, t_train_n, f_test_n, t_test_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Total training time: {train_duration:.2f} seconds.")

    # 4. Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    joblib.dump(xgb_models, os.path.join(save_path, "xgb_models_list.pkl"))

    json_config = dict(config)
    json_config["xgb_params"] = _json_safe_xgb_params(config.get("xgb_params", {}))

    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(json_config, f, indent=4)

    history_file = os.path.join(save_path, "history.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(histories, f, indent=4)
    logger.info(f"Training history saved to {history_file}")

    # 5. Generate report
    report_data = generate_report(
        xgb_models=xgb_models,
        f_train=f_train,
        f_test=f_test,
        t_train=t_train,
        t_test=t_test,
        f_scaler=f_scaler,
        t_scaler=t_scaler,
        config=json_config,
        train_duration=train_duration,
        save_path=save_path,
        feature_names=feature_names,
        target_names=target_names,
    )

    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)
    logger.info("Report successfully generated.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new):
    """
    Predict using saved XGBoost models.

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

    model_file = os.path.join(model_dir, "xgb_models_list.pkl")
    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")

    if not os.path.exists(model_file):
        raise FileNotFoundError(f"XGB model file not found: {model_file}")

    xgb_models = joblib.load(model_file)
    f_scaler = joblib.load(f_scaler_file) if os.path.exists(f_scaler_file) else None
    t_scaler = joblib.load(t_scaler_file) if os.path.exists(t_scaler_file) else None

    if len(xgb_models) == 0:
        raise ValueError("Loaded XGBoost model list is empty.")

    expected_features = getattr(xgb_models[0], "n_features_in_", None)
    if expected_features is not None and X_new.shape[1] != expected_features:
        raise ValueError(
            f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
        )

    if f_scaler is not None:
        X_eval = f_scaler.transform(X_new)
    else:
        X_eval = X_new.astype(np.float32)

    y_pred_norm = np.zeros((X_eval.shape[0], len(xgb_models)), dtype=np.float32)
    for i, model in enumerate(xgb_models):
        y_pred_norm[:, i] = model.predict(X_eval)

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
        "model_name": "TX11_XGB",
        "model_type": "XGB",
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "none",   # standard / minmax / robust / maxabs / none
            "target_method": "none",    # standard / minmax / robust / maxabs / none
        },
        "max_cpu_threads": 8,
        "xgb_params": {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "eval_metric": "rmse",
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "gamma": 0.0,
            "reg_alpha": 0.0,
            "reg_lambda": 1.0,
            "random_state": 42,
            "tree_method": "hist",
            "device": "cpu",
            "objective": "reg:squarederror",
        },
    }

    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Example: reduce dataset for quick testing
    # num_samples = 200
    # num_outputs = 10
    # train_model_pipeline(X[:num_samples], y[:num_samples, :num_outputs], train_config, MODEL_BASE_DIR)

    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)