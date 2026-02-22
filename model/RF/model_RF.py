import os
import json
import random
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from model import data_translator

# ----------------------------
# Split Data
# ----------------------------
def split_data(features, targets, primary_size=0.8, secondary_size=0.2, random_state=None):
    return train_test_split(
        features, targets,
        train_size=primary_size,
        test_size=secondary_size,
        random_state=random_state
    )

# ----------------------------
# Normalize Data
# ----------------------------
def normalize_data_sets(feature_train, feature_test, target_train, target_test):
    feature_scaler = StandardScaler()
    target_scaler  = StandardScaler()

    feature_train_norm = feature_scaler.fit_transform(feature_train)
    feature_test_norm  = feature_scaler.transform(feature_test)

    target_train_norm = target_scaler.fit_transform(target_train)
    target_test_norm  = target_scaler.transform(target_test)

    return feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler

# ----------------------------
# Random Forest Hyperparameters
# ----------------------------
rf_params = {
    "n_estimators": 500,
    "max_depth": None,          # None = expand until pure
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt",     # common good default
    "bootstrap": True,
    "random_state": 42,
    "n_jobs": -1
}

# ----------------------------
# Train Multi-output Random Forest
# ----------------------------
def train_rf_models(feature_train, target_train, params=rf_params):
    n_outputs = target_train.shape[1]
    models = []

    for i in range(n_outputs):
        model = RandomForestRegressor(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        print(f"Trained RF for output {i+1}/{n_outputs}")

    return models

# ----------------------------
# Predict
# ----------------------------
def predict_rf(models, feature_test):
    n_samples = feature_test.shape[0]
    n_outputs = len(models)
    predictions = np.zeros((n_samples, n_outputs))

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_test)

    return predictions

# ----------------------------
# Metrics
# ----------------------------
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

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    file_path = "/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz"

    X, y, feat_names, targ_names, freqs = data_translator.prepare_ffi_data(file_path)

    feature_train, feature_test, target_train, target_test = split_data(
        X, y, 0.8, 0.2, random.randint(0, 1000)
    )

    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = normalize_data_sets(
        feature_train, feature_test, target_train, target_test
    )

    rf_models = train_rf_models(feature_train_norm, target_train_norm)
    predictions_norm = predict_rf(rf_models, feature_test_norm)
    predictions = target_scaler.inverse_transform(predictions_norm)

    metrics_dict = get_model_metrics(target_test, predictions)
    print(json.dumps(metrics_dict, indent=4))

    # Save models
    model_path = "/mnt/storage/emon/model_library/RF_TX11"
    os.makedirs(model_path, exist_ok=True)

    joblib.dump(feature_scaler, os.path.join(model_path, 'feature_scaler.pkl'))
    joblib.dump(target_scaler, os.path.join(model_path, 'target_scaler.pkl'))

    for i, model in enumerate(rf_models):
        joblib.dump(model, os.path.join(model_path, f'rf_model_output_{i}.pkl'))