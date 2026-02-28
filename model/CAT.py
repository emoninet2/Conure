# CAT.py

import os
import json
import joblib
import time
import logging
import numpy as np
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler

# Custom modules
from model import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
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

# ---------------- MODEL TRAINING ----------------
def train_cat_models(feature_train, target_train, config):
    """
    Train separate CatBoost models for each output dimension.
    """
    n_outputs = target_train.shape[1]
    models = []
    params = config["cat_params"]

    for i in range(n_outputs):
        model = CatBoostRegressor(**params)
        model.fit(feature_train, target_train[:, i], silent=True)
        models.append(model)
        logger.info(f"Trained CatBoost for output {i+1}/{n_outputs}")

    return models

# ---------------- REPORT GENERATION ----------------
def generate_report(cat_models, f_train, f_test, t_train, t_test,
                    f_scaler, t_scaler, config, train_duration, save_path):
    # Predict on test set
    preds_norm = np.zeros((f_test.shape[0], len(cat_models)))
    for i, m in enumerate(cat_models):
        preds_norm[:, i] = m.predict(f_test)
    preds = t_scaler.inverse_transform(preds_norm)

    # Performance metrics
    perf_metrics = report.calculate_metrics(t_test, preds)

    # Hardware info (no GPU detection for CatBoost Python API)
    import psutil
    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)

    # Data info
    total_samples = f_train.shape[0] + f_test.shape[0]
    val_split = config.get("training", {}).get("validation_split", 0.0)
    train_samples = f_train.shape[0]
    validation_samples = int(f_train.shape[0] * val_split) if val_split > 0 else 0

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "CatBoost",
            "trainable_parameters": "N/A",
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "data_info": {
            "input_dim": f_train.shape[1],
            "output_dim": t_train.shape[1],
            "total_samples": total_samples,
            "train_samples": train_samples,
            "validation_samples": validation_samples,
            "test_samples": f_test.shape[0],
            "split_strategy": "train_test_split",
            "test_size": 0.2,
            "validation_split": val_split,
            "random_state": 42
        },
        "performance": {
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "evaluation_dataset": "held-out test set",
                "predictions_inverse_transformed": True,
                "normalization_used": True
            }
        },
        "system_info": report.get_system_info(),
        "hardware_info": {
            "gpu_utilized": config["cat_params"].get("task_type", "").upper() == "GPU",
            "gpu_count": 1 if config["cat_params"].get("task_type", "").upper() == "GPU" else 0,
            "gpu_details": "GPU Mode" if config["cat_params"].get("task_type", "").upper() == "GPU" else "CPU Mode",
            "peak_process_ram_gb": peak_ram_gb
        },
        "configuration": config
    }

    return full_report

# ---------------- TRAINING PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):

    # 1. Split data
    f_train, f_test, t_train, t_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 2. Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train, f_test, t_train, t_test, **config["normalization"]
    )

    # 3. Train
    start_time = time.time()
    cat_models = train_cat_models(f_train_n, t_train_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # 4. Save artifacts
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    joblib.dump(cat_models, os.path.join(save_path, "cat_models_list.pkl"))

    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(config, f, indent=4)

    # 5. Generate & save report
    report_data = generate_report(cat_models, f_train, f_test, t_train, t_test,
                                  f_scaler, t_scaler, config, train_duration, save_path)
    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)
    logger.info("Report successfully generated.")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_CAT",
        "model_type": "CatBoost",
        "normalization": {"feature_method": "standard", "target_method": "standard"},
        "cat_params": {
            "iterations": 1000,
            "learning_rate": 0.05,
            "depth": 6,
            "l2_leaf_reg": 3,
            "random_seed": 42,
            "task_type": "GPU",  # Set to CPU if GPU not available
            "devices": "0"
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Run pipeline
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)