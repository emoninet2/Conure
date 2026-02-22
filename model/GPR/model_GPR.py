import os
import sys
import json
import random
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler  
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C, WhiteKernel



import matplotlib.pyplot as plt

from model import data_translator  # your data translation functions


# ------------------------------------------------------------
# 🔹 Function to Split Data
# ------------------------------------------------------------
def split_data(features, targets, primary_size=0.8, secondary_size=0.2, random_state=None):
    return train_test_split(features, targets, train_size=primary_size, test_size=secondary_size, random_state=random_state)


# ------------------------------------------------------------
# 🔹 Function to Normalize Data
# ------------------------------------------------------------

def normalize_data_sets(feature_train, feature_test, target_train, target_test, 
                        feature_method="standard", target_method="standard"):
    """
    Normalizes feature and target datasets using the specified scaling methods.

    Args:
    - feature_train: Training feature data
    - feature_test: Testing feature data
    - target_train: Training target data
    - target_test: Testing target data
    - feature_method: Normalization method for features ("standard", "minmax", "robust", "maxabs")
    - target_method: Normalization method for targets ("standard", "minmax", "robust", "maxabs")

    Returns:
    - feature_train_norm, feature_test_norm: Normalized feature sets
    - target_train_norm, target_test_norm: Normalized target sets
    - feature_scaler: Scaler used for features
    - target_scaler: Scaler used for targets
    """

    # Define a common scalers dictionary for both feature and target methods
    scalers = {
        "standard": StandardScaler,
        "minmax": MinMaxScaler,
        "robust": RobustScaler,
        "maxabs": MaxAbsScaler
    }

    # Ensure valid normalization methods
    feature_method = feature_method.strip().lower()  # Ensure no extra spaces or case issues
    target_method = target_method.strip().lower()  # Ensure no extra spaces or case issues

    # Validate normalization methods
    if feature_method not in scalers:
        raise ValueError(f"Invalid feature normalization method '{feature_method}'. Choose from {list(scalers.keys())}.")
    if target_method not in scalers:
        raise ValueError(f"Invalid target normalization method '{target_method}'. Choose from {list(scalers.keys())}.")

    # Select and create new instances of scalers for feature and target
    feature_scaler = scalers[feature_method]()  # Create new instance of the selected scaler
    target_scaler = scalers[target_method]()    # Create new instance of the selected scaler

    # Fit and transform feature data
    feature_train_norm = feature_scaler.fit_transform(feature_train)
    feature_test_norm = feature_scaler.transform(feature_test)

    # Fit and transform target data
    target_train_norm = target_scaler.fit_transform(target_train)
    target_test_norm = target_scaler.transform(target_test)

    return feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler

# ------------------------------------------------------------
# 🔹 Function to Train GPR Model
# ------------------------------------------------------------
def train_gpr_model(feature_train, target_train):
    """
    Train a separate GPR model for each output dimension.
    Returns a list of trained models.
    """
    n_outputs = target_train.shape[1]
    models = []

    for i in range(n_outputs):

        # Kernel: Constant * RBF + WhiteKernel (noise)
        # kernel = C(1.0, (1e-3, 1e3)) * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2)) + WhiteKernel(noise_level=1e-5)
        # gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, alpha=0.0, normalize_y=True)

        # Example kernel with larger bounds
        kernel = C(1.0, (1e-3, 1e4)) * RBF(length_scale=1.0, length_scale_bounds=(1e-3, 1e3)) \
         + WhiteKernel(noise_level=1e-5, noise_level_bounds=(1e-6, 1e-2))

        gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, normalize_y=True)




        gpr.fit(feature_train, target_train[:, i])
        models.append(gpr)
        print(f"Trained GPR for output {i+1}/{n_outputs}")

    return models


# ------------------------------------------------------------
# 🔹 Function to Make Predictions
# ------------------------------------------------------------
def predict_gpr(models, feature_test):
    n_samples = feature_test.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs))

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_test)

    return predictions


# ------------------------------------------------------------
# 🔹 Function to Get Metrics
# ------------------------------------------------------------
def get_model_metrics(target_test, predictions):
    # Aggregate metrics
    r2  = r2_score(target_test, predictions)
    mae = mean_absolute_error(target_test, predictions)
    rmse = np.sqrt(mean_squared_error(target_test, predictions))

    # Per-sample metrics
    per_sample_rmse = np.sqrt(np.mean((target_test - predictions)**2, axis=1))
    per_sample_r2   = np.array([r2_score(target_test[i], predictions[i]) for i in range(target_test.shape[0])])
    per_sample_summary = {
        "RMSE mean": np.mean(per_sample_rmse),
        "RMSE max": np.max(per_sample_rmse),
        "RMSE min": np.min(per_sample_rmse),
        "R2 mean": np.mean(per_sample_r2),
        "R2 min": np.min(per_sample_r2)
    }

    # Per-output metrics
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


# ------------------------------------------------------------
# 🔹 Main Script
# ------------------------------------------------------------
if __name__ == "__main__":
    # Load data
    file_path = "/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz"

    X, y, feat_names, targ_names, freqs = data_translator.prepare_ffi_data(file_path)

    print("Features shape:", X.shape)
    print("Targets shape:", y.shape)

    # Split into train/test
    feature_train, feature_test, target_train, target_test = split_data(X, y, 0.8, 0.2, random.randint(0, 1000))

    # Normalize data
    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = normalize_data_sets(
        feature_train, feature_test, target_train, target_test
    )

    # Train GPR models
    gpr_models = train_gpr_model(feature_train_norm, target_train_norm)

    # Make predictions
    predictions_norm = predict_gpr(gpr_models, feature_test_norm)

    # Denormalize predictions
    predictions = target_scaler.inverse_transform(predictions_norm)

    # Get metrics
    metrics_dict = get_model_metrics(target_test, predictions)
    print(json.dumps(metrics_dict, indent=4))

    # Save models
    model_path = "/mnt/storage/emon/model_library/GPR_TX11"
    os.makedirs(model_path, exist_ok=True)

    # Save scalers
    joblib.dump(feature_scaler, os.path.join(model_path, 'feature_scaler.pkl'))
    joblib.dump(target_scaler, os.path.join(model_path, 'target_scaler.pkl'))

    # Save trained GPR models
    for i, model in enumerate(gpr_models):
        joblib.dump(model, os.path.join(model_path, f'gpr_model_output_{i}.pkl'))