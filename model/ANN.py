# ANN.py

import os
import json
import joblib
import time
import logging
import psutil
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.optimizers import Adam

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

# ---------------- MODEL GENERATION ----------------
def generate_model(train_features, train_targets, config):
    val_size = config["training"].get("validation_split", 0.2)
    train_f, val_f, train_t, val_t = train_test_split(
        train_features, train_targets, test_size=val_size, random_state=42
    )

    model = Sequential()
    for i, layer in enumerate(config["architecture"]):
        if layer["type"] == "Dense":
            if i == 0:
                model.add(Dense(layer["units"], activation=layer["activation"],
                                input_shape=(train_features.shape[1],)))
            else:
                model.add(Dense(layer["units"], activation=layer["activation"]))
        elif layer["type"] == "Dropout":
            model.add(Dropout(layer["rate"]))

    optimizer = Adam(learning_rate=config["training"]["learning_rate"])
    model.compile(optimizer=optimizer, loss=config["training"]["loss"], metrics=config["training"]["metrics"])

    callbacks = []
    if config.get("early_stopping"):
        callbacks.append(tf.keras.callbacks.EarlyStopping(**config["early_stopping"]))

    history = model.fit(
        train_f, train_t,
        validation_data=(val_f, val_t),
        epochs=config["training"]["epochs"],
        batch_size=config["training"]["batch_size"],
        callbacks=callbacks,
        verbose=1
    )

    return model, history

# ---------------- REPORT GENERATION ----------------
def generate_report(model, history, f_train, f_test, t_train, t_test,
                    f_scaler, t_scaler, config, train_duration, save_path):

    # Predict on test set
    f_test_norm = f_scaler.transform(f_test)
    y_pred_norm = model.predict(f_test_norm, verbose=0)
    y_pred = t_scaler.inverse_transform(y_pred_norm)

    # Performance metrics
    perf_metrics = report.calculate_metrics(t_test, y_pred)

    # Hardware info
    gpu_devices = tf.config.list_physical_devices("GPU")
    gpu_details = []
    if gpu_devices:
        for gpu in gpu_devices:
            details = tf.config.experimental.get_device_details(gpu)
            gpu_details.append({
                "name": details.get("device_name", "Unknown GPU"),
                "compute_capability": details.get("compute_capability", None)
            })

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)

    # Model size
    model_path = os.path.join(save_path, f"{config['model_name']}.keras")
    if os.path.exists(model_path):
        model_size_mb = round(os.path.getsize(model_path) / (1024**2), 2)
    else:
        model_size_mb = None

    # Data info
    total_samples = f_train.shape[0] + f_test.shape[0]
    val_split = config["training"]["validation_split"]
    train_samples = int(f_train.shape[0] * (1 - val_split))
    validation_samples = int(f_train.shape[0] * val_split)

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "TensorFlow",
            "framework_version": tf.__version__,
            "trainable_parameters": model.count_params(),
            "model_size_mb": model_size_mb,
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
        "training_summary": {
            "epochs_completed": len(history.history["loss"]),
            "final_train_loss": float(history.history["loss"][-1]),
            "final_val_loss": float(history.history["val_loss"][-1]),
            "best_val_loss": float(min(history.history["val_loss"]))
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
            "gpu_utilized": len(gpu_details) > 0,
            "gpu_count": len(gpu_details),
            "gpu_details": gpu_details if gpu_details else "CPU Mode",
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

    # 3. Adjust last layer
    if config["architecture"][-1]["units"] == "AUTO":
        config["architecture"][-1]["units"] = y.shape[1]

    # 4. Train
    start_time = time.time()
    model, history = generate_model(f_train_n, t_train_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    # 5. Save artifacts
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    model_file = os.path.join(save_path, f"{config['model_name']}.keras")
    model.save(model_file)
    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(config, f, indent=4)

    # Save training history
    history_file = os.path.join(save_path, "history.json")
    with open(history_file, "w") as f:
        json.dump(history.history, f, indent=4)

    # 6. Generate & save report
    report_data = generate_report(model, history, f_train, f_test, t_train, t_test,
                                  f_scaler, t_scaler, config, train_duration, save_path)
    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)

    logger.info("Report successfully generated.")

# ---------------- MAIN ----------------
if __name__ == "__main__":

    FILE_PATH = "/home/emon/projects/Conure/data/raw/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/home/emon/projects/Conure/data/model_library/"

    train_config = {
        "model_name": "TX11_ANN",
        "model_type": "ANN",
        "normalization": {
            "feature_method": "standard",
            "target_method": "standard"
        },
        "training": {
            "epochs": 100,
            "batch_size": 32,
            "learning_rate": 0.001,
            "loss": "mse",
            "metrics": ["mae"],
            "validation_split": 0.2
        },
        "early_stopping": {
            "monitor": "val_loss",
            "patience": 15,
            "restore_best_weights": True
        },
        "architecture": [
            {"type": "Dense", "units": 128, "activation": "relu"},
            {"type": "Dropout", "rate": 0.1},
            {"type": "Dense", "units": 512, "activation": "relu"},
            {"type": "Dense", "units": "AUTO", "activation": "linear"}
        ]
    }

    # Load data (specific to your data format)
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Call training pipeline
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)