# LGBM.py

import os
import time
import logging
import numpy as np
import psutil
import joblib
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from model import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------------- TRAIN MODEL ----------------
def train_lgb_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    models = []
    for i in range(n_outputs):
        model = lgb.LGBMRegressor(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        logger.info(f"Trained LGBM for output {i+1}/{n_outputs}")
    return models

# ---------------- PREDICT ----------------
def predict_lgb(models, feature_test):
    n_samples = feature_test.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs))
    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_test)
    return predictions

# ---------------- PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):
    # Split dataset
    f_train, f_test, t_train, t_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train LightGBM models
    start_time = time.time()
    lgb_models = train_lgb_models(f_train, t_train, config["lgb_params"])
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # Predict
    preds = predict_lgb(lgb_models, f_test)

    # Calculate metrics using report.py
    perf_metrics = report.calculate_metrics(t_test, preds)

    # Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(lgb_models, os.path.join(save_path, "lgb_models_list.pkl"))

    # System info and memory usage
    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)
    system_info = report.get_system_info()

    # Full report
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
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "dataset": "held-out test set",
                "normalization_used": False
            }
        },
        "system_info": system_info,
        "hardware_info": {
            "peak_process_ram_gb": peak_ram_gb,
            "gpu_used": False
        },
        "configuration": config
    }

    # Save report
    report.save_report(full_report, save_path)
    report.log_metric(perf_metrics, config["model_type"], logger)
    logger.info("LightGBM training pipeline completed.")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_LGBM",
        "model_type": "LGBM",
        "lgb_params": {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "max_depth": 6,
            "num_leaves": 31,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Reduce dataset size for ultra-fast test
    num_samples = 50
    num_outputs = 100

    # Run training pipeline
    train_model_pipeline(X[:num_samples], y[:num_samples, :num_outputs], train_config, MODEL_BASE_DIR)