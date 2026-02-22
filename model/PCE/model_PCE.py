import os
import json
import random
import joblib
import numpy as np
from numpy.polynomial.legendre import legval
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from model import data_translator


def split_data(features, targets, primary_size=0.8, secondary_size=0.2, random_state=None):
    return train_test_split(features, targets,
                            train_size=primary_size,
                            test_size=secondary_size,
                            random_state=random_state)


def normalize_data_sets(feature_train, feature_test, target_train, target_test):
    feature_scaler = StandardScaler()
    target_scaler = StandardScaler()

    feature_train_norm = feature_scaler.fit_transform(feature_train)
    feature_test_norm = feature_scaler.transform(feature_test)

    target_train_norm = target_scaler.fit_transform(target_train)
    target_test_norm = target_scaler.transform(target_test)

    return feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler


pce_params = {
    "degree": 3
}


def build_legendre_basis(X, degree):
    basis_list = [np.ones((X.shape[0], 1))]

    for d in range(1, degree + 1):
        for j in range(X.shape[1]):
            coeff = [0]*d + [1]
            col = legval(X[:, j], coeff).reshape(-1, 1)
            basis_list.append(col)

    return np.hstack(basis_list)


def train_pce_models(feature_train, target_train, params=pce_params):
    n_outputs = target_train.shape[1]
    models = []

    X_basis = build_legendre_basis(feature_train, params["degree"])

    for i in range(n_outputs):
        model = LinearRegression()
        model.fit(X_basis, target_train[:, i])
        models.append(model)
        print(f"Trained PCE for output {i+1}/{n_outputs}")

    return models


def predict_pce(models, feature_test, params=pce_params):
    X_basis = build_legendre_basis(feature_test, params["degree"])
    predictions = np.zeros((feature_test.shape[0], len(models)))

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(X_basis)

    return predictions


def get_model_metrics(target_test, predictions):
    r2 = r2_score(target_test, predictions)
    mae = mean_absolute_error(target_test, predictions)
    rmse = np.sqrt(mean_squared_error(target_test, predictions))

    return {
        "Aggregate": {"R2": r2, "RMSE": rmse, "MAE": mae}
    }


if __name__ == "__main__":
    file_path = "/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz"
    X, y, feat_names, targ_names, freqs = data_translator.prepare_ffi_data(file_path)

    X_train, X_test, y_train, y_test = split_data(X, y, 0.8, 0.2, random.randint(0, 1000))
    X_train, X_test, y_train, y_test, f_scaler, t_scaler = normalize_data_sets(X_train, X_test, y_train, y_test)

    models = train_pce_models(X_train, y_train)
    preds_norm = predict_pce(models, X_test)
    preds = t_scaler.inverse_transform(preds_norm)

    metrics = get_model_metrics(y_test, preds)
    print(json.dumps(metrics, indent=4))

    os.makedirs("PCE_MODEL", exist_ok=True)
    joblib.dump(models, "PCE_MODEL/models.pkl")