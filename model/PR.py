# PR_pipeline.py

import os
import json
import joblib
import time
import logging
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import LinearRegression
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
def train_pr_models(feature_train, target_train, params):
    n_outputs = target_train.shape[1]
    poly = PolynomialFeatures(**params)
    X_poly = poly.fit_transform(feature_train)
    models = []

    for i in range(n_outputs):
        model = LinearRegression()
        model.fit(X_poly, target_train[:, i])
        models.append(model)
        logger.info(f"Trained PR for output {i+1}/{n_outputs}")

    return models, poly

# ---------------- PREDICT ----------------
def predict_pr(models, poly, feature_test):
    X_poly = poly.transform(feature_test)
    predictions = np.zeros((feature_test.shape[0], len(models)))
    for i, model in enumerate(models):
        predictions[:, i] = model.predict(X_poly)
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
    pr_models, poly = train_pr_models(f_train_n, t_train_n, config["pr_params"])
    train_duration = time.time() - start_time
    logger.info(f"PR training completed in {train_duration:.2f} seconds.")

    # Predict & Metrics
    preds_norm = predict_pr(pr_models, poly, f_test_n)
    preds = t_scaler.inverse_transform(preds_norm)
    metrics_dict = get_model_metrics(t_test, preds)

    # Save everything
    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))
    joblib.dump({"models": pr_models, "poly": poly}, os.path.join(save_path, "pr_models_list.pkl"))

    # Config & metrics
    config["training_duration_sec"] = train_duration
    with open(os.path.join(save_path, "config.json"), "w") as f:
        json.dump(config, f, indent=4)
    with open(os.path.join(save_path, "metrics.json"), "w") as f:
        json.dump(metrics_dict, f, indent=4)

    report.log_metric(metrics_dict, config["model_type"], logger)
    logger.info("PR pipeline completed.")




def predict(model_dir, X_new):
    """
    Predict using saved Polynomial Regression models.

    Parameters
    ----------
    model_dir : str
        Path to the saved model directory.
    X_new : np.ndarray
        Input features with shape (n_samples, n_features) or (n_features,).

    Returns
    -------
    np.ndarray
        Predictions with shape (n_samples, n_outputs).
    """
    X_new = np.asarray(X_new, dtype=np.float64)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    # Load saved artifacts
    f_scaler_file = os.path.join(model_dir, "feature_scaler.pkl")
    t_scaler_file = os.path.join(model_dir, "target_scaler.pkl")
    model_file = os.path.join(model_dir, "pr_models_list.pkl")

    if not os.path.exists(f_scaler_file):
        raise FileNotFoundError(f"Feature scaler not found: {f_scaler_file}")
    if not os.path.exists(t_scaler_file):
        raise FileNotFoundError(f"Target scaler not found: {t_scaler_file}")
    if not os.path.exists(model_file):
        raise FileNotFoundError(f"PR model file not found: {model_file}")

    f_scaler = joblib.load(f_scaler_file)
    t_scaler = joblib.load(t_scaler_file)
    saved_obj = joblib.load(model_file)

    pr_models = saved_obj["models"]
    poly = saved_obj["poly"]

    if len(pr_models) == 0:
        raise ValueError("Loaded PR model list is empty.")

    expected_features = getattr(f_scaler, "n_features_in_", None)
    if expected_features is not None and X_new.shape[1] != expected_features:
        raise ValueError(
            f"Feature mismatch: model expects {expected_features}, got {X_new.shape[1]}"
        )

    # Normalize input
    X_norm = f_scaler.transform(X_new)

    # Predict in normalized space
    y_pred_norm = predict_pr(pr_models, poly, X_norm)

    # Inverse transform to original scale
    y_pred = t_scaler.inverse_transform(y_pred_norm)

    return y_pred



    
# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz"
    MODEL_BASE_DIR = "/mnt/storage/emon/model_library/"

    train_config = {
        "model_name": "TX11_PR",
        "model_type": "PR",
        "normalization": {"feature_method": "standard", "target_method": "standard"},
        "pr_params": {
            "degree": 2,
            "include_bias": False
        }
    }

    # Load data
    X, y, _, _, _ = data_translator.prepare_ffi_data(FILE_PATH)

    # Run pipeline
    train_model_pipeline(X, y, train_config, MODEL_BASE_DIR)