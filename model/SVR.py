# SVR.py

import os
import json
import joblib
import time
import logging
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import data_translator, report

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
    scalers = {"standard": StandardScaler}
    f_scaler = scalers[feature_method.lower()]()
    t_scaler = scalers[target_method.lower()]()

    f_train_norm = f_scaler.fit_transform(feature_train)
    f_test_norm = f_scaler.transform(feature_test)

    t_train_norm = t_scaler.fit_transform(target_train)
    t_test_norm = t_scaler.transform(target_test)

    return f_train_norm, f_test_norm, t_train_norm, t_test_norm, f_scaler, t_scaler

# ---------------- TRAIN ----------------
def train_svr_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    models = []
    for i in range(n_outputs):
        model = SVR(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        logger.info(f"Trained SVR for output {i+1}/{n_outputs}")
    return models

# ---------------- PREDICT ----------------
def predict_svr(models, feature_test):
    n_samples = feature_test.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs))
    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_test)
    return predictions

# ---------------- METRICS ----------------
def get_model_metrics(target_test, predictions):
    r2  = r2_score(target_test, predictions)
    mae = mean_absolute_error(target_test, predictions)
    rmse = np.sqrt(mean_squared_error(target_test, predictions))
    return {"Aggregate": {"R2": r2, "RMSE": rmse, "MAE": mae}}

# ---------------- PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):
    # Split
    f_train, f_test, t_train, t_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train, f_test, t_train, t_test, **config["normalization"]
    )

    # Train
    start_time = time.time()
    svr_models = train_svr_models(f_train_n, t_train_n, config["svr_params"])
    train_duration = time.time() - start_time
    logger.info(f"SVR training completed in {train_duration:.2f} seconds.")

    # Predict & Metrics
    preds_norm = predict_svr(svr_models, f_test_n)
    preds = t_scaler.inverse_transform(preds_norm)
    metrics_dict = get_model_metrics(t_test, preds)

    # Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    joblib.dump(svr_models, os.path.join(save_path, "svr_models_list.pkl"))

    # Save config and metrics
    config["training_duration_sec"] = train_duration
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(config, f, indent=4)
    with open(os.path.join(save_path, "metrics.json"), "w") as f:
        json.dump(metrics_dict, f, indent=4)

    report.log_metric(metrics_dict, config["model_type"], logger)
    logger.info("SVR pipeline completed.")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_SVR",
        "model_type": "SVR",
        "normalization": {"feature_method": "standard", "target_method": "standard"},
        "svr_params": {
            "kernel": "rbf",
            "C": 100.0,
            "epsilon": 0.001,
            "gamma": "scale"
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Run pipeline
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)