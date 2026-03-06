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

# Custom modules
from model import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------------- TRAIN XGBOOST ----------------
def train_xgb_models(feature_train, target_train, feature_val, target_val, config):
    n_outputs = target_train.shape[1]
    models = []
    histories = {}
    params = config["xgb_params"].copy()  # copy to avoid mutation

    if "eval_metric" not in params:
        params["eval_metric"] = "rmse"

    for i in range(n_outputs):
        model = xgb.XGBRegressor(**params)

        eval_set = [(feature_train, target_train[:, i]), (feature_val, target_val[:, i])]

        model.fit(
            feature_train,
            target_train[:, i],
            eval_set=eval_set,
            verbose=False
        )

        models.append(model)
        histories[f"output_{i}"] = model.evals_result()
        logger.info(f"Trained XGB for output {i+1}/{n_outputs}")

    return models, histories

# ---------------- TRAINING PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):
    # Limit CPU threads if specified
    max_threads = config.get("max_cpu_threads")
    if max_threads:
        os.environ["OMP_NUM_THREADS"] = str(max_threads)
        os.environ["MKL_NUM_THREADS"] = str(max_threads)
        os.environ["NUMEXPR_NUM_THREADS"] = str(max_threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(max_threads)
        logger.info(f"CPU threads limited to {max_threads}")

    # 1. Split data
    f_train, f_test, t_train, t_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 2. Train models
    device = config["xgb_params"].get("device", "cpu")
    logger.info(f"Starting XGBoost training for {y.shape[1]} outputs on {device}...")
    start_time = time.time()
    xgb_models, histories = train_xgb_models(f_train, t_train, f_test, t_test, config)
    train_duration = time.time() - start_time
    logger.info(f"Total training time: {train_duration:.2f} seconds.")

    # 3. Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(xgb_models, os.path.join(save_path, "xgb_models_list.pkl"))

    # Save config
    json_config = config.copy()
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(json_config, f, indent=4)

    # Save training history
    history_file = os.path.join(save_path, "history.json")
    with open(history_file, "w") as f:
        json.dump(histories, f, indent=4)
    logger.info(f"Training history saved to {history_file}")

    # 4. Evaluate
    preds = np.zeros((f_test.shape[0], len(xgb_models)))
    for i, m in enumerate(xgb_models):
        preds[:, i] = m.predict(f_test)

    # 5. Generate report
    perf_metrics = report.calculate_metrics(t_test, preds)
    system_info = report.get_system_info()
    process = psutil.Process(os.getpid())
    peak_ram = round(process.memory_info().rss / (1024**3), 2)

    model_size_mb = round(sum([os.path.getsize(os.path.join(save_path, f)) 
                               for f in os.listdir(save_path)
                               if f.endswith(".pkl")]) / (1024**2), 2)

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "trainable_outputs": y.shape[1],
            "training_duration_sec": train_duration,
            "model_size_mb": model_size_mb,
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
            "peak_process_ram_gb": peak_ram,
            "gpu_used": device != "cpu"
        },
        "configuration": json_config
    }

    report.save_report(full_report, save_path)
    logger.info("Report successfully generated.")

    # After report.save_report(full_report, save_path)
    report.log_metric(perf_metrics, config["model_type"], logger)
    logger.info("Report successfully generated.")

# ---------------- MAIN ----------------
if __name__ == "__main__":

    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    # ---------------- ULTRA-FAST TEST CONFIG ----------------
    train_config = {
        "model_name": "TX11_XGB",
        "model_type": "XGBoost",
        "xgb_params": {
            "n_estimators": 1,      
            "max_depth": 1,         
            "learning_rate": 1.0,   
            "eval_metric": "rmse",  
            "subsample": 0.2,       
            "colsample_bytree": 0.2,
            "gamma": 0.0,
            "reg_alpha": 0.0,
            "reg_lambda": 1.0,
            "random_state": 42,
            "tree_method": "hist",
            "device": "cpu"
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Reduce dataset size and outputs
    num_samples = 200   
    num_outputs = 10  

    # Run the fast training pipeline
    train_model_pipeline(X[:num_samples], y[:num_samples, :num_outputs], train_config, MODEL_BASE_DIR)