# GPR.py

import os
import json
import joblib
import time
import logging
import warnings
import threadpoolctl
import numpy as np
import psutil

from sklearn.model_selection import train_test_split
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    RBF,
    Matern,
    RationalQuadratic,
    WhiteKernel,
    ConstantKernel as C,
)
from sklearn.exceptions import ConvergenceWarning

import data_translator
import normalization
import report


# ============================================================
# WARNINGS
# ============================================================
warnings.filterwarnings("ignore", category=ConvergenceWarning)
os.environ["PYTHONWARNINGS"] = "ignore"


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
# SPLIT HELPERS
# ============================================================
def get_split_config(config):
    split_cfg = config.get("data_split", {}) or {}

    test_size = float(split_cfg.get("test_size", 0.2))
    random_state = split_cfg.get("random_state", 42)

    if not (0.0 < test_size < 1.0):
        raise ValueError(f"data_split.test_size must be between 0 and 1, got {test_size}")

    return {
        "test_size": test_size,
        "random_state": random_state,
    }


# ============================================================
# KERNEL BUILDER
# ============================================================
def build_gpr_kernel(kernel_config):
    """
    Convert a JSON-friendly kernel config into a sklearn kernel object.

    Supported string values:
        "RBF"
        "RBF+WHITE"
        "MATERN"
        "MATERN+WHITE"
        "RQ"
        "RQ+WHITE"

    Supported dict examples:
        {"type": "RBF"}
        {"type": "RBF+WHITE"}
        {"type": "MATERN", "nu": 1.5}
        {"type": "MATERN+WHITE", "nu": 2.5}
        {"type": "RQ", "alpha": 1.0}
        {"type": "RQ+WHITE", "alpha": 1.0}

    If kernel_config is already a sklearn kernel object, it is returned as-is.
    """
    if kernel_config is None:
        return None

    if hasattr(kernel_config, "get_params"):
        return kernel_config

    if isinstance(kernel_config, str):
        kernel_type = kernel_config.strip().upper()
        kernel_params = {}
    elif isinstance(kernel_config, dict):
        kernel_type = str(kernel_config.get("type", "RBF")).strip().upper()
        kernel_params = dict(kernel_config)
    else:
        raise TypeError(
            f"Unsupported kernel config type: {type(kernel_config)}. "
            "Expected None, str, dict, or sklearn kernel object."
        )

    const = C(
        kernel_params.get("constant_value", 1.0),
        kernel_params.get("constant_value_bounds", (1e-2, 1e7)),
    )

    rbf = RBF(
        length_scale=kernel_params.get("length_scale", 1.0),
        length_scale_bounds=kernel_params.get("length_scale_bounds", (1e-2, 1e4)),
    )

    matern = Matern(
        length_scale=kernel_params.get("length_scale", 1.0),
        length_scale_bounds=kernel_params.get("length_scale_bounds", (1e-2, 1e4)),
        nu=kernel_params.get("nu", 1.5),
    )

    rq = RationalQuadratic(
        length_scale=kernel_params.get("length_scale", 1.0),
        alpha=kernel_params.get("alpha", 1.0),
    )

    white = WhiteKernel(
        noise_level=kernel_params.get("noise_level", 1e-3),
        noise_level_bounds=kernel_params.get("noise_level_bounds", (1e-5, 1e-1)),
    )

    if kernel_type == "RBF":
        return const * rbf
    if kernel_type in {"RBF+WHITE", "RBF_WHITE", "RBF_WITH_WHITE"}:
        return const * rbf + white
    if kernel_type == "MATERN":
        return const * matern
    if kernel_type in {"MATERN+WHITE", "MATERN_WHITE", "MATERN_WITH_WHITE"}:
        return const * matern + white
    if kernel_type in {"RQ", "RATIONALQUADRATIC", "RATIONAL_QUADRATIC"}:
        return const * rq
    if kernel_type in {"RQ+WHITE", "RATIONALQUADRATIC+WHITE", "RATIONAL_QUADRATIC+WHITE"}:
        return const * rq + white

    raise ValueError(
        f"Unsupported GPR kernel: {kernel_config}. "
        "Supported values: RBF, RBF+WHITE, MATERN, MATERN+WHITE, RQ, RQ+WHITE."
    )


def _json_safe_gpr_params(params):
    out = {}
    for k, v in params.items():
        if k == "kernel":
            if isinstance(v, (dict, str)) or v is None:
                out[k] = v
            else:
                out[k] = str(v)
        else:
            out[k] = v
    return out


# ============================================================
# THREAD CONTROL
# ============================================================
def apply_thread_limits(config):
    max_threads = config.get("max_cpu_threads")
    if not max_threads:
        return

    max_threads = int(max_threads)

    os.environ["OMP_NUM_THREADS"] = str(max_threads)
    os.environ["MKL_NUM_THREADS"] = str(max_threads)
    os.environ["NUMEXPR_NUM_THREADS"] = str(max_threads)
    os.environ["OPENBLAS_NUM_THREADS"] = str(max_threads)

    threadpoolctl.threadpool_limits(limits=max_threads)
    logger.info(f"CPU threads limited to {max_threads}")


# ============================================================
# PARAM HELPERS
# ============================================================
def build_gpr_params(config):
    raw_params = dict(config.get("gpr_params", {}) or {})
    params = dict(raw_params)
    params["kernel"] = build_gpr_kernel(raw_params.get("kernel"))

    if "n_restarts_optimizer" in params:
        params["n_restarts_optimizer"] = int(params["n_restarts_optimizer"])

    if "normalize_y" in params:
        params["normalize_y"] = bool(params["normalize_y"])

    if "alpha" in params:
        params["alpha"] = float(params["alpha"])

    return params


# ============================================================
# TRAIN GPR
# ============================================================
def train_gpr_model(feature_train, target_train, config):
    n_outputs = target_train.shape[1]
    models = []
    params = build_gpr_params(config)

    for i in range(n_outputs):
        gpr = GaussianProcessRegressor(**params)
        gpr.fit(feature_train, target_train[:, i])
        models.append(gpr)
        logger.info(f"Trained GPR for output {i + 1}/{n_outputs}")

    return models


# ============================================================
# REPORT GENERATION
# ============================================================
def generate_report(
    gpr_models,
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

    preds_norm = np.column_stack([m.predict(f_test_eval) for m in gpr_models])

    if t_scaler is not None:
        preds = t_scaler.inverse_transform(preds_norm)
    else:
        preds = preds_norm

    perf_metrics = report.calculate_metrics(t_test, preds)

    system_info = report.get_system_info()
    process = psutil.Process(os.getpid())
    peak_ram = round(process.memory_info().rss / (1024**3), 2)

    model_files = [
        os.path.join(save_path, "gpr_models_list.pkl"),
        os.path.join(save_path, "config.json"),
    ]

    if f_scaler is not None:
        model_files.append(os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        model_files.append(os.path.join(save_path, "target_scaler.pkl"))

    model_size_bytes = sum(os.path.getsize(p) for p in model_files if os.path.exists(p))
    model_size_mb = round(model_size_bytes / (1024**2), 2)

    split_cfg = get_split_config(config)
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
            "test_size": split_cfg["test_size"],
            "random_state": split_cfg["random_state"],
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
        },
        "configuration": {
            **config,
            "gpr_params": _json_safe_gpr_params(config.get("gpr_params", {})),
        },
    }

    return full_report


# ============================================================
# TRAINING PIPELINE
# ============================================================
def train_model_pipeline(X, y, config, model_base_dir):
    apply_thread_limits(config)

    split_cfg = get_split_config(config)

    # 1. Split data
    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=split_cfg["test_size"],
        random_state=split_cfg["random_state"],
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
    logger.info(f"Starting GPR training for {y.shape[1]} outputs...")
    start_time = time.time()
    gpr_models = train_gpr_model(f_train_n, t_train_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Total training time: {train_duration:.2f} seconds.")

    # 4. Save artifacts
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    joblib.dump(gpr_models, os.path.join(save_path, "gpr_models_list.pkl"))

    json_config = dict(config)
    json_config["gpr_params"] = _json_safe_gpr_params(config.get("gpr_params", {}))

    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(json_config, f, indent=4)

    # 5. Report
    report_data = generate_report(
        gpr_models=gpr_models,
        f_train=f_train,
        f_test=f_test,
        t_train=t_train,
        t_test=t_test,
        f_scaler=f_scaler,
        t_scaler=t_scaler,
        config=config,
        train_duration=train_duration,
        save_path=save_path,
    )

    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)
    logger.info("Report successfully generated.")


# ============================================================
# PREDICT
# ============================================================
def predict(model_dir, X_new, return_std=False):
    X_new = np.asarray(X_new, dtype=np.float64)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    feature_scaler_path = os.path.join(model_dir, "feature_scaler.pkl")
    target_scaler_path = os.path.join(model_dir, "target_scaler.pkl")
    model_list_path = os.path.join(model_dir, "gpr_models_list.pkl")

    if not os.path.exists(model_list_path):
        raise FileNotFoundError(f"GPR model list not found: {model_list_path}")

    f_scaler = joblib.load(feature_scaler_path) if os.path.exists(feature_scaler_path) else None
    t_scaler = joblib.load(target_scaler_path) if os.path.exists(target_scaler_path) else None
    gpr_models = joblib.load(model_list_path)

    expected_features = getattr(gpr_models[0], "n_features_in_", None)
    if expected_features is not None and X_new.shape[1] != expected_features:
        raise ValueError(
            f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
        )

    if f_scaler is not None:
        X_new_norm = f_scaler.transform(X_new)
    else:
        X_new_norm = X_new.astype(np.float64)

    if return_std:
        pred_means = []
        pred_stds = []

        for model in gpr_models:
            mean_i, std_i = model.predict(X_new_norm, return_std=True)
            pred_means.append(mean_i)
            pred_stds.append(std_i)

        y_pred_norm = np.column_stack(pred_means)
        y_std_norm = np.column_stack(pred_stds)

        if t_scaler is not None:
            y_pred = t_scaler.inverse_transform(y_pred_norm)

            if hasattr(t_scaler, "propagate_std_from_norm"):
                y_std = t_scaler.propagate_std_from_norm(y_std_norm)
            elif hasattr(t_scaler, "scale_"):
                y_std = y_std_norm * t_scaler.scale_
            else:
                zeros = np.zeros_like(y_std_norm)
                y_std = (
                    t_scaler.inverse_transform(zeros + y_std_norm)
                    - t_scaler.inverse_transform(zeros)
                )
        else:
            y_pred = y_pred_norm
            y_std = y_std_norm

        return y_pred, y_std

    y_pred_norm = np.column_stack([model.predict(X_new_norm) for model in gpr_models])

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    return y_pred


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    FILE_PATH = "/mnt/storage/emon/projects/Conure/data/workspace/tx33/sweep/TX33/simulation_data.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_GPR",
        "model_type": "GPR",
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "standard",   # standard / minmax / robust / maxabs / none
            "target_method": "standard",    # standard / minmax / robust / maxabs / none
        },
        "max_cpu_threads": 8,
        "gpr_params": {
            "kernel": "RBF+WHITE",
            "n_restarts_optimizer": 3,
            "normalize_y": True,
            "alpha": 1e-8,
        },
    }

    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)