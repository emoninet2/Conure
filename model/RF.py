# RF.py

import os
import json
import joblib
import time
import logging
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

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
        "standard": StandardScaler
    }
    f_scaler = scalers[feature_method.lower()]()
    t_scaler = scalers[target_method.lower()]()

    f_train_norm = f_scaler.fit_transform(feature_train)
    f_test_norm = f_scaler.transform(feature_test)

    t_train_norm = t_scaler.fit_transform(target_train)
    t_test_norm = t_scaler.transform(target_test)

    return f_train_norm, f_test_norm, t_train_norm, t_test_norm, f_scaler, t_scaler

# ---------------- TRAIN MODEL ----------------
def train_rf_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    models = []
    for i in range(n_outputs):
        model = RandomForestRegressor(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        logger.info(f"Trained RF for output {i+1}/{n_outputs}")
    return models

# ---------------- PREDICT ----------------
def predict_rf(models, feature_test):
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

    per_sample_rmse = np.sqrt(np.mean((target_test - predictions)**2, axis=1))
    per_sample_r2   = np.array([r2_score(target_test[i], predictions[i])
                                for i in range(target_test.shape[0])])

    per_sample_summary = {
        "RMSE mean": np.mean(per_sample_rmse),
        "RMSE max": np.max(per_sample_rmse),
        "RMSE min": np.min(per_sample_rmse),
        "R2 mean": np.mean(per_sample_r2),
        "R2 min": np.min(per_sample_r2)
    }

    per_output_rmse = np.sqrt(np.mean((target_test - predictions)**2, axis=0))
    per_output_mae  = np.mean(np.abs(target_test - predictions), axis=0)

    per_output_summary = {
        "RMSE mean": np.mean(per_output_rmse),
        "RMSE max": np.max(per_output_rmse),
        "RMSE min": np.min(per_output_rmse),
        "MAE mean": np.mean(per_output_mae)
    }

    metrics_dict = {
        "Aggregate": {"R2": r2, "RMSE": rmse, "MAE": mae},
        "Per-sample summary": per_sample_summary,
        "Per-output summary": per_output_summary
    }

    return metrics_dict

# ---------------- PIPELINE ----------------
# ---------------- PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):
    import psutil
    import math

    # Helper to sanitize NaN/Inf
    def sanitize_json(obj):
        if isinstance(obj, dict):
            return {k: sanitize_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_json(x) for x in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        else:
            return obj

    # Split
    f_train, f_test, t_train, t_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Normalize
    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train, f_test, t_train, t_test, **config["normalization"]
    )

    # Train
    start_time = time.time()
    rf_models = train_rf_models(f_train_n, t_train_n, config["rf_params"])
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # Predict & Metrics
    preds_norm = predict_rf(rf_models, f_test_n)
    preds = t_scaler.inverse_transform(preds_norm)
    perf_metrics = get_model_metrics(t_test, preds)

    # Save models
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    joblib.dump(rf_models, os.path.join(save_path, "rf_models_list.pkl"))



    # ---------------- FULL REPORT ----------------
    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)
    system_info = report.get_system_info()

    # Compute total size of all model files in MB
    model_files = [f for f in os.listdir(save_path) if f.endswith(".pkl")]
    model_size_mb = round(sum(os.path.getsize(os.path.join(save_path, f)) for f in model_files) / (1024**2), 2)


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
                "predictions_inverse_transformed": True,
                "normalization_used": True
            }
        },
        "system_info": system_info,
        "hardware_info": {
            "peak_process_ram_gb": peak_ram_gb,
            "gpu_used": False
        },
        "configuration": config
    }

    # Sanitize NaN/Inf
    full_report = sanitize_json(full_report)

    # Save report
    report.save_report(full_report, save_path)
    report.log_metric(perf_metrics, config["model_type"], logger)
    logger.info("Random Forest training pipeline completed.")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_RF_SIMPLE",
        "model_type": "RandomForest",
        "normalization": {"feature_method": "standard", "target_method": "standard"},
        "rf_params": {
            "n_estimators": 200,
            "max_depth": 20,
            "min_samples_split": 5,
            "min_samples_leaf": 5,
            "max_features": "sqrt",
            "bootstrap": True,
            "random_state": 42,
            "n_jobs": -1
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Run pipeline
    #train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)


    # Reduce dataset size for ultra-fast test
    num_samples = 5
    num_outputs = 10

    # Run training pipeline
    train_model_pipeline(X[:num_samples], y[:num_samples, :num_outputs], train_config, MODEL_BASE_DIR)

