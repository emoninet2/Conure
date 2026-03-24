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
import data_translator, report

# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ---------------- NORMALIZATION ----------------
def normalize_data_sets(
    feature_train,
    feature_test,
    target_train,
    target_test,
    feature_method="standard",
    target_method="standard",
):
    scalers = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler,
        "maxabs": MaxAbsScaler,
        "none": None,
    }

    feature_method = str(feature_method).strip().lower()
    target_method = str(target_method).strip().lower()

    if feature_method not in scalers:
        raise ValueError(f"Unsupported feature normalization method: {feature_method}")
    if target_method not in scalers:
        raise ValueError(f"Unsupported target normalization method: {target_method}")

    # Features
    if scalers[feature_method] is None:
        f_scaler = None
        f_train_norm = np.asarray(feature_train, dtype=np.float32)
        f_test_norm = np.asarray(feature_test, dtype=np.float32)
    else:
        f_scaler = scalers[feature_method]()
        f_train_norm = f_scaler.fit_transform(feature_train).astype(np.float32)
        f_test_norm = f_scaler.transform(feature_test).astype(np.float32)

    # Targets
    if scalers[target_method] is None:
        t_scaler = None
        t_train_norm = np.asarray(target_train, dtype=np.float32)
        t_test_norm = np.asarray(target_test, dtype=np.float32)
    else:
        t_scaler = scalers[target_method]()
        t_train_norm = t_scaler.fit_transform(target_train).astype(np.float32)
        t_test_norm = t_scaler.transform(target_test).astype(np.float32)

    return f_train_norm, f_test_norm, t_train_norm, t_test_norm, f_scaler, t_scaler


# ---------------- MODEL GENERATION ----------------
def generate_model(train_features, train_targets, config):
    from keras import regularizers
    from keras import optimizers

    val_size = float(config["training"].get("validation_split", 0.2))
    if not (0.0 < val_size < 1.0):
        raise ValueError(f"training.validation_split must be between 0 and 1, got {val_size}")

    random_state = int(
        config.get("data_split", {}).get("random_state", config.get("random_state", 42))
    )

    train_f, val_f, train_t, val_t = train_test_split(
        train_features,
        train_targets,
        test_size=val_size,
        random_state=random_state,
    )

    model = Sequential()

    for i, layer in enumerate(config["architecture"]):
        layer_type = layer["type"]

        if layer_type == "Dense":
            reg = None
            if "regularizer" in layer:
                r = layer["regularizer"]
                r_type = str(r.get("type", "")).lower()

                if r_type == "l1":
                    reg = regularizers.l1(r["value"])
                elif r_type == "l2":
                    reg = regularizers.l2(r["value"])
                elif r_type == "l1_l2":
                    reg = regularizers.l1_l2(
                        l1=r.get("l1", 0.0),
                        l2=r.get("l2", 0.0),
                    )

            if i == 0:
                model.add(
                    Dense(
                        units=layer["units"],
                        activation=layer["activation"],
                        input_shape=(train_features.shape[1],),
                        kernel_regularizer=reg,
                    )
                )
            else:
                model.add(
                    Dense(
                        units=layer["units"],
                        activation=layer["activation"],
                        kernel_regularizer=reg,
                    )
                )

        elif layer_type == "Dropout":
            model.add(Dropout(layer["rate"]))

        else:
            raise ValueError(f"Unsupported layer type: {layer_type}")

    opt_conf = config["training"].get(
        "optimizer",
        {"type": "Adam", "learning_rate": 0.001},
    )
    opt_type = str(opt_conf.get("type", "Adam")).lower()
    lr = float(opt_conf.get("learning_rate", 0.001))

    if opt_type == "adam":
        optimizer = optimizers.Adam(learning_rate=lr)
    elif opt_type == "sgd":
        momentum = float(opt_conf.get("momentum", 0.0))
        optimizer = optimizers.SGD(learning_rate=lr, momentum=momentum)
    elif opt_type == "rmsprop":
        optimizer = optimizers.RMSprop(learning_rate=lr)
    elif opt_type == "adagrad":
        optimizer = optimizers.Adagrad(learning_rate=lr)
    else:
        raise ValueError(f"Unsupported optimizer type: {opt_type}")

    model.compile(
        optimizer=optimizer,
        loss=config["training"]["loss"],
        metrics=config["training"]["metrics"],
    )

    callbacks = []
    if config.get("early_stopping"):
        callbacks.append(tf.keras.callbacks.EarlyStopping(**config["early_stopping"]))

    history = model.fit(
        train_f,
        train_t,
        validation_data=(val_f, val_t),
        epochs=config["training"]["epochs"],
        batch_size=config["training"]["batch_size"],
        callbacks=callbacks,
        verbose=1,
    )

    return model, history


# ---------------- PREDICT ----------------
def predict(model_dir, X_new):
    """
    Run prediction using a trained ANN model.
    """
    X_new = np.asarray(X_new, dtype=np.float32)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    model_path = os.path.join(model_dir, "model.keras")
    legacy_model_path = os.path.join(model_dir, os.path.basename(model_dir) + ".keras")
    feature_scaler_path = os.path.join(model_dir, "feature_scaler.pkl")
    target_scaler_path = os.path.join(model_dir, "target_scaler.pkl")

    if not os.path.exists(model_path):
        if os.path.exists(legacy_model_path):
            model_path = legacy_model_path
        else:
            raise FileNotFoundError(
                f"ANN model file not found. Checked: {model_path} and {legacy_model_path}"
            )

    model = tf.keras.models.load_model(model_path)

    f_scaler = None
    if os.path.exists(feature_scaler_path):
        f_scaler = joblib.load(feature_scaler_path)

    t_scaler = None
    if os.path.exists(target_scaler_path):
        t_scaler = joblib.load(target_scaler_path)

    if f_scaler is not None:
        X_norm = f_scaler.transform(X_new).astype(np.float32)
    else:
        X_norm = X_new.astype(np.float32)

    y_pred_norm = model.predict(X_norm, verbose=0)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    return y_pred


# ---------------- REPORT GENERATION ----------------
def generate_report(
    model,
    history,
    f_train,
    f_test,
    t_train,
    t_test,
    f_scaler,
    t_scaler,
    config,
    train_duration,
    save_path,
):
    if f_scaler is not None:
        f_test_eval = f_scaler.transform(f_test).astype(np.float32)
    else:
        f_test_eval = np.asarray(f_test, dtype=np.float32)

    y_pred_norm = model.predict(f_test_eval, verbose=0)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    perf_metrics = report.calculate_metrics(t_test, y_pred)

    gpu_devices = tf.config.list_physical_devices("GPU")
    gpu_details = []
    if gpu_devices:
        for gpu in gpu_devices:
            details = tf.config.experimental.get_device_details(gpu)
            gpu_details.append(
                {
                    "name": details.get("device_name", "Unknown GPU"),
                    "compute_capability": details.get("compute_capability", None),
                }
            )

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024**3), 2)

    model_path = os.path.join(save_path, "model.keras")
    model_size_mb = round(os.path.getsize(model_path) / (1024**2), 2) if os.path.exists(model_path) else None

    total_samples = f_train.shape[0] + f_test.shape[0]
    val_split = float(config["training"].get("validation_split", 0.2))
    train_samples = int(f_train.shape[0] * (1 - val_split))
    validation_samples = int(f_train.shape[0] * val_split)

    test_size = float(config.get("data_split", {}).get("test_size", 0.2))
    random_state = int(config.get("data_split", {}).get("random_state", config.get("random_state", 42)))

    normalization_cfg = config.get("normalization", {})
    feature_norm_used = str(normalization_cfg.get("feature_method", "standard")).lower() != "none"
    target_norm_used = str(normalization_cfg.get("target_method", "standard")).lower() != "none"

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "TensorFlow",
            "framework_version": tf.__version__,
            "trainable_parameters": model.count_params(),
            "model_size_mb": model_size_mb,
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "data_info": {
            "input_dim": f_train.shape[1],
            "output_dim": t_train.shape[1],
            "total_samples": total_samples,
            "train_samples": train_samples,
            "validation_samples": validation_samples,
            "test_samples": f_test.shape[0],
            "split_strategy": "train_test_split",
            "test_size": test_size,
            "validation_split": val_split,
            "random_state": random_state,
        },
        "training_summary": {
            "epochs_completed": len(history.history["loss"]),
            "final_train_loss": float(history.history["loss"][-1]),
            "final_val_loss": float(history.history["val_loss"][-1]),
            "best_val_loss": float(min(history.history["val_loss"])),
        },
        "performance": {
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "evaluation_dataset": "held-out test set",
                "predictions_inverse_transformed": target_norm_used,
                "normalization_used": feature_norm_used or target_norm_used,
                "feature_normalization_used": feature_norm_used,
                "target_normalization_used": target_norm_used,
            },
        },
        "system_info": report.get_system_info(),
        "hardware_info": {
            "gpu_utilized": len(gpu_details) > 0,
            "gpu_count": len(gpu_details),
            "gpu_details": gpu_details if gpu_details else "CPU Mode",
            "peak_process_ram_gb": peak_ram_gb,
        },
        "configuration": config,
    }

    return full_report


# ---------------- TRAINING PIPELINE ----------------
def train_model_pipeline(X, y, config, model_base_dir):
    data_split_cfg = config.get("data_split", {})
    test_size = float(data_split_cfg.get("test_size", 0.2))
    random_state = int(data_split_cfg.get("random_state", config.get("random_state", 42)))

    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    normalization_cfg = config.get(
        "normalization",
        {
            "feature_method": "standard",
            "target_method": "standard",
        },
    )

    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalize_data_sets(
        f_train,
        f_test,
        t_train,
        t_test,
        **normalization_cfg,
    )

    config = json.loads(json.dumps(config))
    if config["architecture"][-1]["units"] == "AUTO":
        config["architecture"][-1]["units"] = y.shape[1]

    start_time = time.time()
    model, history = generate_model(f_train_n, t_train_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    model_file = os.path.join(save_path, "model.keras")
    model.save(model_file)

    # Save scalers only if they exist
    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    history_file = os.path.join(save_path, "history.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history.history, f, indent=4)

    report_data = generate_report(
        model,
        history,
        f_train,
        f_test,
        t_train,
        t_test,
        f_scaler,
        t_scaler,
        config,
        train_duration,
        save_path,
    )
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
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "standard",   # standard / minmax / robust / maxabs / none
            "target_method": "standard",    # standard / minmax / robust / maxabs / none
        },
        "training": {
            "epochs": 100,
            "batch_size": 32,
            "loss": "mse",
            "metrics": ["mae"],
            "validation_split": 0.2,
            "optimizer": {
                "type": "Adam",
                "learning_rate": 0.001,
                "momentum": 0.9,
            },
        },
        "early_stopping": {
            "monitor": "val_loss",
            "patience": 15,
            "restore_best_weights": True,
        },
        "architecture": [
            {"type": "Dense", "units": 128, "activation": "relu", "regularizer": {"type": "l2", "value": 0.01}},
            {"type": "Dropout", "rate": 0.1},
            {"type": "Dense", "units": 512, "activation": "relu", "regularizer": {"type": "l1_l2", "l1": 0.001, "l2": 0.01}},
            {"type": "Dense", "units": "AUTO", "activation": "linear"},
        ],
    }

    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)