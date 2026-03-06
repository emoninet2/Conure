# gpr.py

import os
import json
import joblib
import time
import logging
import warnings
import threadpoolctl  # optional: enforce thread limits
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel
from sklearn.exceptions import ConvergenceWarning
import psutil

# Suppress convergence warnings
warnings.filterwarnings("ignore", category=ConvergenceWarning)
os.environ['PYTHONWARNINGS'] = 'ignore'

# Custom modules
import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------------- NORMALIZATION ----------------
def normalize_data_sets(feature_train, feature_test, target_train, target_test,
                        feature_method="standard", target_method="standard"):
    scalers = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler,
        "maxabs": MaxAbsScaler
    }
    f_scaler = scalers[feature_method.lower()]()
    t_scaler = scalers[target_method.lower()]()

    f_train_norm = f_scaler.fit_transform(feature_train)
    f_test_norm = f_scaler.transform(feature_test)
    t_train_norm = t_scaler.fit_transform(target_train)
    t_test_norm = t_scaler.transform(target_test)

    return f_train_norm, f_test_norm, t_train_norm, t_test_norm, f_scaler, t_scaler

# ---------------- TRAIN GPR ----------------
def train_gpr_model(feature_train, target_train, config):
    n_outputs = target_train.shape[1]
    models = []
    params = config["gpr_params"]

    for i in range(n_outputs):
        gpr = GaussianProcessRegressor(**params)
        gpr.fit(feature_train, target_train[:, i])
        models.append(gpr)
        logger.info(f"Trained GPR for output {i+1}/{n_outputs}")

    return models

# ---------------- TRAINING PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):

    # Limit CPU threads if provided
    max_threads = config.get("max_cpu_threads")
    if max_threads:
        os.environ["OMP_NUM_THREADS"] = str(max_threads)   # OpenMP
        os.environ["MKL_NUM_THREADS"] = str(max_threads)   # Intel MKL
        os.environ["NUMEXPR_NUM_THREADS"] = str(max_threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(max_threads)
        
        threadpoolctl.threadpool_limits(limits=max_threads)
        logger.info(f"CPU threads limited to {max_threads}")


    # 1. Split data
    f_train, f_test, t_train, t_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 2. Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train, f_test, t_train, t_test, **config["normalization"]
    )

    # 3. Train GPR models
    logger.info(f"Starting GPR training for {y.shape[1]} outputs...")
    start_time = time.time()
    gpr_models = train_gpr_model(f_train_n, t_train_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Total training time: {train_duration:.2f} seconds.")

    # 4. Save models & scalers
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    joblib.dump(gpr_models, os.path.join(save_path, "gpr_models_list.pkl"))

    # Save config (omit kernel object for JSON)
    json_config = config.copy()
    json_config["gpr_params"] = {k: v for k, v in config["gpr_params"].items() if k != "kernel"}
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(json_config, f, indent=4)

    # 5. Evaluate
    preds_norm = np.array([m.predict(f_test_n) for m in gpr_models]).T
    preds = t_scaler.inverse_transform(preds_norm)

    # 6. Generate report
    report_data = report.calculate_metrics(t_test, preds)
    system_info = report.get_system_info()
    process = psutil.Process(os.getpid())
    peak_ram = round(process.memory_info().rss / (1024**3), 2)

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "trainable_outputs": y.shape[1],
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "data_info": {
            "input_dim": f_train.shape[1],
            "output_dim": t_train.shape[1],
            "total_samples": X.shape[0],
            "train_samples": f_train.shape[0],
            "test_samples": f_test.shape[0],
            "split_strategy": "train_test_split",
            "test_size": 0.2,
            "random_state": 42
        },
        "performance": {
            "metrics": report_data,
            "evaluation_protocol": {
                "dataset": "held-out test set",
                "predictions_inverse_transformed": True,
                "normalization_used": True
            }
        },
        "system_info": system_info,
        "hardware_info": {
            "peak_process_ram_gb": peak_ram
        },
        "configuration": json_config
    }

    report.save_report(full_report, save_path)
    logger.info("Report successfully generated.")

# ---------------- PREDICT ----------------
def predict(model_dir, X_new, return_std=False):
    """
    Predict using saved GPR models.

    Parameters
    ----------
    model_dir : str
        Path to the saved model directory.
    X_new : np.ndarray
        Input features of shape (n_samples, n_features) or (n_features,).
    return_std : bool, optional
        If True, also return predictive standard deviation in original target scale.

    Returns
    -------
    y_pred : np.ndarray
        Predictions in original target scale, shape (n_samples, n_outputs)

    y_std : np.ndarray, optional
        Predictive standard deviation in original target scale,
        returned only if return_std=True
    """
    # Convert input
    X_new = np.asarray(X_new, dtype=np.float64)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    # Load saved artifacts
    feature_scaler_path = os.path.join(model_dir, "feature_scaler.pkl")
    target_scaler_path = os.path.join(model_dir, "target_scaler.pkl")
    model_list_path = os.path.join(model_dir, "gpr_models_list.pkl")

    if not os.path.exists(feature_scaler_path):
        raise FileNotFoundError(f"Feature scaler not found: {feature_scaler_path}")
    if not os.path.exists(target_scaler_path):
        raise FileNotFoundError(f"Target scaler not found: {target_scaler_path}")
    if not os.path.exists(model_list_path):
        raise FileNotFoundError(f"GPR model list not found: {model_list_path}")

    f_scaler = joblib.load(feature_scaler_path)
    t_scaler = joblib.load(target_scaler_path)
    gpr_models = joblib.load(model_list_path)

    # Validate feature dimension
    expected_features = getattr(gpr_models[0], "n_features_in_", None)
    if expected_features is not None and X_new.shape[1] != expected_features:
        raise ValueError(
            f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
        )

    # Normalize input
    X_new_norm = f_scaler.transform(X_new)

    # Predict each output independently
    if return_std:
        pred_means = []
        pred_stds = []

        for model in gpr_models:
            mean_i, std_i = model.predict(X_new_norm, return_std=True)
            pred_means.append(mean_i)
            pred_stds.append(std_i)

        y_pred_norm = np.column_stack(pred_means)   # (n_samples, n_outputs)
        y_std_norm = np.column_stack(pred_stds)     # (n_samples, n_outputs)

        # Inverse transform mean prediction
        y_pred = t_scaler.inverse_transform(y_pred_norm)

        # Scale std back to original target scale
        # For sklearn scalers:
        # original = normalized * scale_ + mean_
        # so std_original = std_normalized * scale_
        if hasattr(t_scaler, "scale_"):
            y_std = y_std_norm * t_scaler.scale_
        else:
            # Fallback: approximate via inverse transform of zero + std
            zeros = np.zeros_like(y_std_norm)
            y_std = t_scaler.inverse_transform(zeros + y_std_norm) - t_scaler.inverse_transform(zeros)

        return y_pred, y_std

    else:
        y_pred_norm = np.column_stack([
            model.predict(X_new_norm) for model in gpr_models
        ])

        y_pred = t_scaler.inverse_transform(y_pred_norm)
        return y_pred


# ---------------- MAIN ----------------
if __name__ == "__main__":

    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    # Config
    train_config = {
        "model_name": "TX11_GPR",
        "model_type": "GPR",
        "normalization": {"feature_method": "standard", "target_method": "standard"},
        "max_cpu_threads": 8,  # <--- Limit CPU threads here
        "gpr_params": {
            "kernel": C(1.0, (1e-2, 1e7)) * RBF(1.0, (1e-2, 1e4)) + WhiteKernel(1e-3, (1e-5, 1e-1)),
            "n_restarts_optimizer": 3,
            "normalize_y": True,
            "alpha": 1e-8
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Run GPR training pipeline
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)