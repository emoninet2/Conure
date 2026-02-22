import os
import json
import random
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from model import data_translator


# ----------------------------
# Split Data
# ----------------------------
def split_data(features, targets, primary_size=0.8, secondary_size=0.2, random_state=None):
    return train_test_split(features, targets,
                            train_size=primary_size,
                            test_size=secondary_size,
                            random_state=random_state)


# ----------------------------
# Normalize Data
# ----------------------------
def normalize_data_sets(feature_train, feature_test, target_train, target_test):
    feature_scaler = StandardScaler()
    target_scaler = StandardScaler()

    feature_train_norm = feature_scaler.fit_transform(feature_train)
    feature_test_norm = feature_scaler.transform(feature_test)

    target_train_norm = target_scaler.fit_transform(target_train)
    target_test_norm = target_scaler.transform(target_test)

    return feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler


# ----------------------------
# PR Parameters
# ----------------------------
pr_params = {
    "degree": 2,
    "include_bias": False
}


# ----------------------------
# Train PR
# ----------------------------
def train_pr_models(feature_train, target_train, params=pr_params):
    n_outputs = target_train.shape[1]
    models = []

    poly = PolynomialFeatures(**params)
    X_poly = poly.fit_transform(feature_train)

    for i in range(n_outputs):
        model = LinearRegression()
        model.fit(X_poly, target_train[:, i])
        models.append(model)
        print(f"Trained PR for output {i+1}/{n_outputs}")

    return models, poly


# ----------------------------
# Predict
# ----------------------------
def predict_pr(models, poly, feature_test):
    X_poly = poly.transform(feature_test)
    predictions = np.zeros((feature_test.shape[0], len(models)))

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(X_poly)

    return predictions


# ----------------------------
# Metrics
# ----------------------------
def get_model_metrics(target_test, predictions):
    r2 = r2_score(target_test, predictions)
    mae = mean_absolute_error(target_test, predictions)
    rmse = np.sqrt(mean_squared_error(target_test, predictions))

    return {
        "Aggregate": {"R2": r2, "RMSE": rmse, "MAE": mae}
    }


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    file_path = "/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz"
    X, y, feat_names, targ_names, freqs = data_translator.prepare_ffi_data(file_path)

    X_train, X_test, y_train, y_test = split_data(X, y, 0.8, 0.2, random.randint(0, 1000))
    X_train, X_test, y_train, y_test, f_scaler, t_scaler = normalize_data_sets(X_train, X_test, y_train, y_test)

    models, poly = train_pr_models(X_train, y_train)
    preds_norm = predict_pr(models, poly, X_test)
    preds = t_scaler.inverse_transform(preds_norm)

    metrics = get_model_metrics(y_test, preds)
    print(json.dumps(metrics, indent=4))


    model_path = "/mnt/storage/emon/model_library/PR_TX11"
    os.makedirs(model_path, exist_ok=True)
    joblib.dump(models,  os.path.join(model_path, "models.pkl") )
    joblib.dump(models,  os.path.join(model_path, "poly.pkl") )