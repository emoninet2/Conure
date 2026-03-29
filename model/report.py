# report.py

import json
import os
import platform
import sys

import numpy as np
import psutil
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ------------------------------------------------------------
# JSON SERIALIZATION HELPERS
# ------------------------------------------------------------
def _to_serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_serializable(v) for v in value]
    return value


# ------------------------------------------------------------
# SYSTEM INFORMATION
# ------------------------------------------------------------
def get_system_info():
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "processor": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "python_version": sys.version.split()[0],
    }


# ------------------------------------------------------------
# PERFORMANCE METRICS
# ------------------------------------------------------------
def calculate_metrics(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))

    per_out_rmse = np.sqrt(np.mean((y_true - y_pred) ** 2, axis=0))
    per_sample_rmse = np.sqrt(np.mean((y_true - y_pred) ** 2, axis=1))

    # Important diagnostics
    per_out_var = np.var(y_true, axis=0)
    per_out_r2 = r2_score(y_true, y_pred, multioutput="raw_values")

    bad_var_mask = per_out_var < 1e-12
    finite_r2 = per_out_r2[np.isfinite(per_out_r2)]

    # Aggregate R2 from sklearn default
    r2 = r2_score(y_true, y_pred)

    return {
        "Aggregate": {
            "R2": float(r2),
            "RMSE": float(rmse),
            "MAE": float(mae),
        },
        "Per-Output": {
            "RMSE_Mean": float(np.mean(per_out_rmse)),
            "RMSE_Max": float(np.max(per_out_rmse)),
            "RMSE_Min": float(np.min(per_out_rmse)),
            "R2_Mean_Finite": float(np.mean(finite_r2)) if finite_r2.size else None,
            "R2_Min_Finite": float(np.min(finite_r2)) if finite_r2.size else None,
            "Variance_Min": float(np.min(per_out_var)),
            "Variance_Max": float(np.max(per_out_var)),
            "Near_Zero_Variance_Count": int(np.sum(bad_var_mask)),
        },
        "Per-Sample": {
            "RMSE_Mean": float(np.mean(per_sample_rmse)),
            "RMSE_Max": float(np.max(per_sample_rmse)),
        },
    }


# ------------------------------------------------------------
# OBSERVED DATA RANGES (domain covered by training material)
# ------------------------------------------------------------
def observed_ranges_for_report(
    f_train, f_test, t_train, t_test, feature_names=None, target_names=None
):
    """
    Per-column min/max over all rows used to build the model (train and test splits
    combined), in original units before feature/target normalization.

    Names come from translation/selection when provided; otherwise ``feature_i`` /
    ``target_i`` placeholders are used.
    """
    f_train = np.asarray(f_train)
    f_test = np.asarray(f_test)
    t_train = np.asarray(t_train)
    t_test = np.asarray(t_test)
    if f_train.ndim != 2 or f_test.ndim != 2:
        raise ValueError("f_train and f_test must be 2D arrays.")
    if t_train.ndim != 2 or t_test.ndim != 2:
        raise ValueError("t_train and t_test must be 2D arrays.")
    f_all = np.vstack([f_train, f_test])
    t_all = np.vstack([t_train, t_test])
    nf = int(f_all.shape[1])
    nt = int(t_all.shape[1])

    if feature_names is not None and len(feature_names) == nf:
        fnames = [str(x) for x in feature_names]
    else:
        fnames = [f"feature_{i}" for i in range(nf)]
    if target_names is not None and len(target_names) == nt:
        tnames = [str(x) for x in target_names]
    else:
        tnames = [f"target_{i}" for i in range(nt)]

    f_min = np.min(f_all, axis=0)
    f_max = np.max(f_all, axis=0)
    t_min = np.min(t_all, axis=0)
    t_max = np.max(t_all, axis=0)

    def _entry(name, vmin, vmax):
        return {"name": name, "min": float(vmin), "max": float(vmax)}

    return {
        "note": (
            "Per-dimension min/max over all samples used to build this model (train and test "
            "splits combined), in original units before feature/target normalization. Values "
            "outside these ranges are extrapolation relative to the data the model was fit on."
        ),
        "features": [_entry(fnames[i], f_min[i], f_max[i]) for i in range(nf)],
        "targets": [_entry(tnames[i], t_min[i], t_max[i]) for i in range(nt)],
    }


# ------------------------------------------------------------
# LOAD / SAVE REPORT
# ------------------------------------------------------------
def load_report(path_or_dir):
    report_path = path_or_dir
    if os.path.isdir(path_or_dir):
        report_path = os.path.join(path_or_dir, "report.json")

    if not os.path.isfile(report_path):
        return {}

    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)



def save_report(report_data, save_path):
    os.makedirs(save_path, exist_ok=True)
    file_full_path = os.path.join(save_path, "report.json")

    try:
        with open(file_full_path, "w", encoding="utf-8") as f:
            json.dump(_to_serializable(report_data), f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving report: {e}")
        return False


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
def log_metric(performance_metrics, model_label, logger=None):
    agg = performance_metrics["Aggregate"]

    log_msg = (
        f"\n{'=' * 60}\n"
        f"📊 PERFORMANCE REPORT: {model_label.upper()}\n"
        f"{'=' * 60}\n"
        f"R²   : {agg['R2']:.6f}\n"
        f"RMSE : {agg['RMSE']:.6f}\n"
        f"MAE  : {agg['MAE']:.6f}\n"
        f"{'=' * 60}"
    )

    if logger:
        logger.info(log_msg)
    else:
        print(log_msg)
