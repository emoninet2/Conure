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

# Custom modules
import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ---------------- MODEL TRAINING ----------------
def train_cat_models(feature_train, target_train, config, save_path):
    """
    Train separate CatBoost models for each output dimension.
    """
    n_outputs = target_train.shape[1]
    models = []
    params = config["cat_params"]

    # Create a dedicated folder for CatBoost internal logs
    catboost_info_dir = os.path.join(save_path, "catboost_info")
    os.makedirs(catboost_info_dir, exist_ok=True)
    params["train_dir"] = catboost_info_dir  # <--- key change

    for i in range(n_outputs):
        model = CatBoostRegressor(**params)
        model.fit(feature_train, target_train[:, i], verbose=False)
        models.append(model)
        logger.info(f"Trained CatBoost for output {i+1}/{n_outputs}")

    return models


# ---------------- PREDICT ----------------
def predict_cat(models, feature_test):
    n_samples = feature_test.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs))

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_test)

    return predictions


# ---------------- REPORT GENERATION ----------------
def generate_report(cat_models, f_train, f_test, t_train, t_test,
                    config, train_duration):

    # Predict on test set
    preds = predict_cat(cat_models, f_test)

    # Performance metrics
    perf_metrics = report.calculate_metrics(t_test, preds)

    # Hardware info
    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)

    total_samples = f_train.shape[0] + f_test.shape[0]

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "CatBoost",
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "data_info": {
            "input_dim": f_train.shape[1],
            "output_dim": t_train.shape[1],
            "total_samples": total_samples,
            "train_samples": f_train.shape[0],
            "test_samples": f_test.shape[0],
            "split_strategy": "train_test_split",
            "test_size": 0.2,
            "random_state": 42
        },
        "performance": {
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "evaluation_dataset": "held-out test set",
                "predictions_inverse_transformed": False,
                "normalization_used": False
            }
        },
        "system_info": report.get_system_info(),
        "hardware_info": {
            "gpu_utilized": config["cat_params"].get("task_type", "").upper() == "GPU",
            "gpu_count": 1 if config["cat_params"].get("task_type", "").upper() == "GPU" else 0,
            "gpu_details": "GPU Mode"
                if config["cat_params"].get("task_type", "").upper() == "GPU"
                else "CPU Mode",
            "peak_process_ram_gb": peak_ram_gb
        },
        "configuration": config
    }

    return full_report


# ---------------- TRAINING PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):

    # 1. Split data
    f_train, f_test, t_train, t_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 2. Prepare save folder
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    # 3. Train
    start_time = time.time()
    cat_models = train_cat_models(f_train, t_train, config, save_path)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # 4. Save artifacts
    joblib.dump(cat_models, os.path.join(save_path, "cat_models_list.pkl"))

    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(config, f, indent=4)

    # 5. Generate & save report
    report_data = generate_report(
        cat_models, f_train, f_test, t_train, t_test,
        config, train_duration
    )

    report.save_report(report_data, save_path)
    report.log_metric(
        report_data["performance"]["metrics"],
        config["model_type"],
        logger
    )

    logger.info("CatBoost training pipeline completed.")


# ---------------- MAIN ----------------
if __name__ == "__main__":

    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_CAT",
        "model_type": "CatBoost",
        "cat_params": {
            "iterations": 1000,
            "learning_rate": 0.05,
            "depth": 6,
            "l2_leaf_reg": 3,
            "random_seed": 42,
            "task_type": "GPU",  # change to "CPU" if needed
            "devices": "0"
            # removed train_dir here; handled inside train_cat_models
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Ultra-fast test
    num_samples = 100
    num_outputs = 10

    train_model_pipeline(
        X[:num_samples],
        y[:num_samples, :num_outputs],
        train_config,
        MODEL_BASE_DIR
    )