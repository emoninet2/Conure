# report.py

import os
import json
import platform
import psutil
import sys
import numpy as np
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


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
    y_true, y_pred = np.array(y_true), np.array(y_pred)

    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))

    per_out_rmse = np.sqrt(np.mean((y_true - y_pred) ** 2, axis=0))
    per_sample_rmse = np.sqrt(np.mean((y_true - y_pred) ** 2, axis=1))

    return {
        "Aggregate": {
            "R2": float(r2),
            "RMSE": float(rmse),
            "MAE": float(mae)
        },
        "Per-Output": {
            "RMSE_Mean": float(np.mean(per_out_rmse)),
            "RMSE_Max": float(np.max(per_out_rmse)),
            "RMSE_Min": float(np.min(per_out_rmse))
        },
        "Per-Sample": {
            "RMSE_Mean": float(np.mean(per_sample_rmse)),
            "RMSE_Max": float(np.max(per_sample_rmse))
        }
    }


# ------------------------------------------------------------
# SAVE REPORT
# ------------------------------------------------------------

def save_report(report_data, save_path):
    os.makedirs(save_path, exist_ok=True)
    file_full_path = os.path.join(save_path, "report.json")

    try:
        with open(file_full_path, "w") as f:
            json.dump(report_data, f, indent=4)
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
        f"\n{'='*60}\n"
        f"📊 PERFORMANCE REPORT: {model_label.upper()}\n"
        f"{'='*60}\n"
        f"R²   : {agg['R2']:.6f}\n"
        f"RMSE : {agg['RMSE']:.6f}\n"
        f"MAE  : {agg['MAE']:.6f}\n"
        f"{'='*60}"
    )

    if logger:
        logger.info(log_msg)
    else:
        print(log_msg)