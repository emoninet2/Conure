import os
import json
import random
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
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


svr_params = {
    "kernel": "rbf",
    "C": 10.0,
    "epsilon": 0.01,
    "gamma": "scale"
}


def train_svr_models(feature_train, target_train, params=svr_params):
    n_outputs = target_train.shape[1]
    models = []

    for i in range(n_outputs):
        model = SVR(**params)
        model.fit(feature_train, target_train[:, i])
        models.append(model)
        print(f"Trained SVR for output {i+1}/{n_outputs}")

    return models


def predict_svr(models, feature_test):
    predictions = np.zeros((feature_test.shape[0], len(models)))

    for i, model in enumerate(models):
        predictions[:, i] = model.predict(feature_test)

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

    models = train_svr_models(X_train, y_train)
    preds_norm = predict_svr(models, X_test)
    preds = t_scaler.inverse_transform(preds_norm)

    metrics = get_model_metrics(y_test, preds)
    print(json.dumps(metrics, indent=4))

    os.makedirs("SVR_MODEL", exist_ok=True)
    joblib.dump(models, "SVR_MODEL/models.pkl")