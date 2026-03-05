# PCE.py

import os
import json
import time
import joblib
import numpy as np
from numpy.polynomial.legendre import legval
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import psutil
import logging

from model import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------------- DATA PREPROCESSING ----------------
def split_data(features, targets, test_size=0.2, random_state=None):
    return train_test_split(features, targets, test_size=test_size, random_state=random_state)

def normalize_data_sets(feature_train, feature_test, target_train, target_test):
    feature_scaler = StandardScaler()
    target_scaler = StandardScaler()

    f_train_n = feature_scaler.fit_transform(feature_train)
    f_test_n = feature_scaler.transform(feature_test)

    t_train_n = target_scaler.fit_transform(target_train)
    t_test_n = target_scaler.transform(target_test)

    return f_train_n, f_test_n, t_train_n, t_test_n, feature_scaler, target_scaler

# ---------------- PCE BASIS ----------------
def build_legendre_basis(X, degree):
    basis_list = [np.ones((X.shape[0], 1))]
    for d in range(1, degree + 1):
        for j in range(X.shape[1]):
            coeff = [0]*d + [1]
            col = legval(X[:, j], coeff).reshape(-1, 1)
            basis_list.append(col)
    return np.hstack(basis_list)

# ---------------- PCE MODEL TRAINING ----------------
def train_pce_models(feature_train, target_train, degree=3):
    n_outputs = target_train.shape[1]
    models = []
    X_basis = build_legendre_basis(feature_train, degree)

    for i in range(n_outputs):
        model = LinearRegression()
        model.fit(X_basis, target_train[:, i])
        models.append(model)
        logger.info(f"Trained PCE for output {i+1}/{n_outputs}")

    return models

# ---------------- PCE PREDICTION ----------------
def predict_pce(models, feature_data, degree=3):
    X_basis = build_legendre_basis(feature_data, degree)
    predictions = np.zeros((feature_data.shape[0], len(models)))
    for i, model in enumerate(models):
        predictions[:, i] = model.predict(X_basis)
    return predictions

# ---------------- PCE REPORT ----------------
def generate_pce_report(models, X_train, X_test, y_train, y_test,
                        f_scaler, t_scaler, params, train_duration, save_path, model_name="PCE_MODEL"):

    # Normalize test features
    X_test_norm = f_scaler.transform(X_test)

    # Predict
    preds_norm = predict_pce(models, X_test_norm, degree=params["degree"])
    preds = t_scaler.inverse_transform(preds_norm)

    # Metrics
    perf_metrics = {
        "Aggregate": report.calculate_metrics(y_test, preds)["Aggregate"]
    }

    # Hardware & system info
    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)
    sys_info = report.get_system_info()

    # Data info
    total_samples = X_train.shape[0] + X_test.shape[0]
    train_samples = X_train.shape[0]
    test_samples = X_test.shape[0]

    # ---------------- MODEL SIZE ----------------
    # Save temporary models to compute size if not already saved
    model_files = []
    os.makedirs(save_path, exist_ok=True)
    models_path = os.path.join(save_path, "models.pkl")
    joblib.dump(models, models_path)
    model_files.append(models_path)
    model_files.append(os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(f_scaler, model_files[-1])
    model_files.append(os.path.join(save_path, "target_scaler.pkl"))
    joblib.dump(t_scaler, model_files[-1])

    total_model_size_bytes = sum(os.path.getsize(f) for f in model_files)
    total_model_size_mb = round(total_model_size_bytes / (1024**2), 2)

    full_report = {
        "model_info": {
            "model_name": model_name,
            "model_type": "PCE",
            "trainable_parameters": sum([m.coef_.size + 1 for m in models]),
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model_size_mb": total_model_size_mb   # <-- added
        },
        "data_info": {
            "input_dim": X_train.shape[1],
            "output_dim": y_train.shape[1],
            "total_samples": total_samples,
            "train_samples": train_samples,
            "test_samples": test_samples,
            "split_strategy": "train_test_split",
            "test_size": round(test_samples / total_samples, 2)
        },
        "training_summary": {
            "degree": params["degree"],
            "n_outputs": y_train.shape[1]
        },
        "performance": {
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "evaluation_dataset": "held-out test set",
                "predictions_inverse_transformed": True,
                "normalization_used": True
            }
        },
        "system_info": sys_info,
        "hardware_info": {
            "cpu_utilized": True,
            "peak_process_ram_gb": peak_ram_gb
        },
        "configuration": params
    }

    return full_report

# ---------------- PCE PIPELINE ----------------
def train_model_pipeline(file_path, model_base_dir, train_config):
    X, y, _, _, _ = data_translator.prepare_ffi_data(file_path)
    f_train, f_test, t_train, t_test = split_data(X, y, test_size=0.2, random_state=42)

    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train, f_test, t_train, t_test
    )

    start_time = time.time()
    models = train_pce_models(f_train_n, t_train_n, degree=train_config.get("degree", 3))
    train_duration = time.time() - start_time
    logger.info(f"PCE training completed in {train_duration:.2f} seconds.")

    # Save artifacts
    save_path = os.path.join(model_base_dir, train_config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(models, os.path.join(save_path, "models.pkl"))
    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(train_config, f, indent=4)

    # Generate & save report
    report_data = generate_pce_report(
        models, f_train, f_test, t_train, t_test, f_scaler, t_scaler,
        train_config, train_duration, save_path,
        model_name=train_config["model_name"]
    )

    report.save_report(report_data, save_path)

    # Log metrics
    report.log_metric(report_data["performance"]["metrics"], train_config.get("model_type", "PCE"), logger)
    logger.info("PCE pipeline finished successfully.")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_PCE",
        "model_type": "PCE",
        "degree": 3
    }

    train_model_pipeline(FILE_PATH, MODEL_BASE_DIR, train_config)