import sys
import numpy as np
import os
import joblib
import json
import matplotlib.pyplot as plt
import random

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler  
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

from keras.models import Sequential, load_model
from keras.layers import Dense
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, Flatten, Dropout, LSTM, BatchNormalization
from tensorflow.keras.optimizers import Adam

from model import data_translator

# ------------------------------------------------------------
# 🔹 Function to Split Data into Two Sets (Train/Test or Train/Validation)
# ------------------------------------------------------------
def split_data(features, target, primary_size, secondary_size, random_state=None):
    """
    Splits data into two subsets.

    Args:
    - features (array-like): Input feature set.
    - target (array-like): Target labels.
    - primary_size (float): Proportion of data for the primary set.
    - secondary_size (float): Proportion of data for the secondary set.
    - random_state (int, optional): Random seed for reproducibility.

    Returns:
    - X_primary, X_secondary: Feature subsets.
    - y_primary, y_secondary: Target subsets.
    """
    return train_test_split(features, target, train_size=primary_size, test_size=secondary_size, random_state=random_state)


# ------------------------------------------------------------
# 🔹 Function to Normalize Data
# ------------------------------------------------------------
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler

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
# 🔹 Function to Denormalize Data
# ------------------------------------------------------------
def denormalize_data(data_normalized, scaler):
    """
    Reverses normalization using the provided scaler.

    Args:
    - data_normalized: The normalized data.
    - scaler: The scaler object used for normalization.

    Returns:
    - data_original: The denormalized (original scale) data.
    """
    if not hasattr(scaler, "inverse_transform"):
        raise TypeError("Scaler object is invalid. Ensure it is a fitted StandardScaler or MinMaxScaler.")
    
    return scaler.inverse_transform(data_normalized)


# ------------------------------------------------------------
# 🔹 Function to Generate & Train a Model
# ------------------------------------------------------------
def generate_model(train_features, train_targets, model_architecture, 
                   epochs=50, batch_size=32, optimizer='adam', 
                   loss='mse', metrics=['mae'], learning_rate=0.001, 
                   early_stopping_params=None):
    """
    Generate and train a neural network model with customizable architecture and early stopping.

    Args:
    - train_features: Training feature set.
    - train_targets: Training target set.
    - model_architecture: List of dictionaries defining the model layers.
    - epochs: Number of training epochs.
    - batch_size: Size of batches for training.
    - optimizer: Optimizer for training.
    - loss: Loss function.
    - metrics: List of metrics to monitor.
    - learning_rate: Learning rate for optimizer.
    - early_stopping_params: Dictionary for EarlyStopping options.

    Returns:
    - model: Trained Keras model.
    - history: Training history object.
    """

    # Split training data into training and validation sets (80-20 split)
    train_features_final, val_features, train_targets_final, val_targets = train_test_split(
        train_features, train_targets, test_size=0.2, random_state=None
    )

    # Configure optimizer
    if optimizer == 'adam':
        optimizer = Adam(learning_rate=learning_rate)
    elif optimizer == 'sgd':
        optimizer = SGD(learning_rate=learning_rate, momentum=0.9)  # Added momentum
    elif optimizer == 'rmsprop':
        optimizer = RMSprop(learning_rate=learning_rate)
    elif optimizer == 'adagrad':
        optimizer = Adagrad(learning_rate=learning_rate)
    elif optimizer == 'adadelta':
        optimizer = Adadelta(learning_rate=learning_rate)
    elif optimizer == 'adamax':
        optimizer = Adamax(learning_rate=learning_rate)
    elif optimizer == 'nadam':
        optimizer = Nadam(learning_rate=learning_rate)
    elif optimizer == 'ftrl':
        optimizer = Ftrl(learning_rate=learning_rate)
    else:
        raise ValueError(f"Unsupported optimizer: {optimizer}")

    # Build the model dynamically based on model_architecture
    model = Sequential()
    for layer in model_architecture:
        if layer["type"] == "Dense":
            if "input_shape" in layer:
                model.add(Dense(layer["units"], activation=layer["activation"], input_shape=layer["input_shape"]))
            else:
                model.add(Dense(layer["units"], activation=layer["activation"]))
        elif layer["type"] == "Dropout":
            model.add(Dropout(layer["rate"]))

    # Compile the model
    model.compile(optimizer=optimizer, loss=loss, metrics=metrics)

    # Set up early stopping if parameters are provided
    early_stopping = None
    if early_stopping_params:
        early_stopping = EarlyStopping(
            monitor=early_stopping_params.get("monitor", "val_loss"),
            patience=early_stopping_params.get("patience", 10),
            restore_best_weights=early_stopping_params.get("restore_best_weights", True)
        )

    # Train the model
    callbacks = [early_stopping] if early_stopping else []
    history = model.fit(
        train_features_final, train_targets_final,
        validation_data=(val_features, val_targets),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks
    )
    
    return model, history




# ------------------------------------------------------------
# 🔹 Function to Load a Model & Make Predictions
# ------------------------------------------------------------
def predict_from_model(model_name, model_path, feature):
    """
    Loads a trained model and makes predictions on new data.

    Args:
    - model_name (str): Name of the saved model.
    - model_path (str): Path to the model directory.
    - feature (array-like): New input data for prediction.

    Returns:
    - predictions_reshaped (array-like): Denormalized predictions.
    """

    # Load the model
    loaded_model = load_model(os.path.join(model_path, model_name + ".keras"))

    # Load scalers
    feature_scaler = joblib.load(os.path.join(model_path, 'feature_scaler.pkl'))
    target_scaler = joblib.load(os.path.join(model_path, 'target_scaler.pkl'))

    # Load the training history (optional)
    history_path = os.path.join(model_path, 'history.json')
    loaded_history = None
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            loaded_history = json.load(f)

    # Ensure feature input has the correct shape
    new_feature_data_reshaped = np.array(feature)
    if new_feature_data_reshaped.ndim == 1:  
        new_feature_data_reshaped = new_feature_data_reshaped.reshape(1, -1)

    # Normalize the feature input
    new_feature_data_norm = feature_scaler.transform(new_feature_data_reshaped)

    # Make predictions
    predictions_norm = loaded_model.predict(new_feature_data_norm)

    # Ensure proper shape for inverse transformation
    if predictions_norm.ndim == 1:
        predictions_norm = predictions_norm.reshape(-1, 1)

    # Denormalize predictions
    predictions_reshaped = target_scaler.inverse_transform(predictions_norm)

    return predictions_reshaped


# ------------------------------------------------------------
# 🔹 Function to Get Simplified Model Metrics
# ------------------------------------------------------------
def get_model_metrics(model_name, model_path, feature_test, target_test):
    """
    Loads a trained Keras model, evaluates it on test data, and returns simplified performance metrics.

    Computes:
    - Aggregate metrics (all outputs flattened)
    - Per-sample summary (mean, max, min RMSE, mean & min R²)
    - Per-output summary (mean, max, min RMSE, mean MAE)

    Args:
        model_name (str): Name of the saved Keras model (without extension)
        model_path (str): Path to the folder containing the model and scalers
        feature_test (np.ndarray): Test features, shape (num_samples, num_features)
        target_test (np.ndarray): Test targets, shape (num_samples, num_outputs)

    Returns:
        metrics_dict (dict): Dictionary containing simplified metrics
    """

    # Load the trained model
    model = load_model(os.path.join(model_path, model_name + ".keras"))

    # Load scalers
    feature_scaler = joblib.load(os.path.join(model_path, 'feature_scaler.pkl'))
    target_scaler  = joblib.load(os.path.join(model_path, 'target_scaler.pkl'))

    # Normalize test features
    feature_test_norm = feature_scaler.transform(feature_test)

    # Make predictions
    predictions_norm = model.predict(feature_test_norm)

    # Ensure 2D for inverse transform
    if predictions_norm.ndim == 1:
        predictions_norm = predictions_norm.reshape(-1, 1)

    # Denormalize predictions
    predictions = target_scaler.inverse_transform(predictions_norm)

    # ----------------- Aggregate Metrics -----------------
    r2 = r2_score(target_test, predictions)
    mae = mean_absolute_error(target_test, predictions)
    mse = mean_squared_error(target_test, predictions)
    rmse = np.sqrt(mse)

    # ----------------- Per-Sample Metrics -----------------
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

    # ----------------- Per-Output Metrics -----------------
    per_output_rmse = np.sqrt(np.mean((target_test - predictions)**2, axis=0))
    per_output_mae  = np.mean(np.abs(target_test - predictions), axis=0)

    per_output_summary = {
        "RMSE mean": np.mean(per_output_rmse),
        "RMSE max": np.max(per_output_rmse),
        "RMSE min": np.min(per_output_rmse),
        "MAE mean": np.mean(per_output_mae)
    }

    # ----------------- Build Simplified Metrics Dictionary -----------------
    metrics_dict = {
        "Aggregate": {
            "R2": r2,
            "RMSE": rmse,
            "MAE": mae
        },
        "Per-sample summary": per_sample_summary,
        "Per-output summary": per_output_summary
    }

    return metrics_dict





data = np.load("/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz")


# Generate 3 noisy variants for FFD
X_ffd, y_ffd, feat_names, targ_names, freqs_ffd = data_translator.prepare_ffi_data("/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz")




features = X_ffd
targets =  y_ffd

# targets = s_parameters.reshape(s_parameters.shape[0], -1)
# features = geometric_parameters[:,:-1] #this is to remove the fourth member "N" which is the number of rings and is redundant for now


print(np.shape(features))
print(np.shape(targets))
#print(np.shape(targets_flattened))
#print(features)


model_name = "TX11_FFI"
model_path = "/mnt/storage/emon/model_library/TEST/" + model_name

# Create the directory if it does not exist
if not os.path.exists(model_path):
    os.makedirs(model_path)

feature_train, feature_test, target_train, target_test = split_data(features, targets,  0.8 , 0.2,  random.randint(0, 1000))

print(np.shape(feature_train))
print(np.shape(feature_test))
print(np.shape(target_train))
print(np.shape(target_test))



feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = normalize_data_sets(
    feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="standard"
)




print(np.shape(feature_train_norm))
print(np.shape(feature_test_norm))
print(np.shape(target_train_norm))
print(np.shape(target_test_norm))



# Reshape target data for dense network
target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)



# Define architecture
# architecture = [
#     {"type": "Dense", "units": 2000, "activation": "relu", "input_shape": (feature_train.shape[1],)},
#     {"type": "Dense", "units": 4000, "activation": "relu"},
#     {"type": "Dense", "units": 8000, "activation": "relu"},
#     {"type": "Dense", "units": target_train.shape[1], "activation": "linear"}
# ]

architecture = [
    {"type": "Dense", "units": 50, "activation": "relu", "input_shape": (feature_train.shape[1],)},
    {"type": "Dropout", "rate": 0.2},  # Dropout layer with 20% dropout
    {"type": "Dense", "units": 1000, "activation": "relu"},
    {"type": "Dropout", "rate": 0.2},  # Dropout layer with 20% dropout
    {"type": "Dense", "units": 100, "activation": "relu"},
    {"type": "Dense", "units": 1000, "activation": "relu"},
    {"type": "Dense", "units": target_train.shape[1], "activation": "linear"}
]

# Define early stopping parameters
early_stopping_config = {
    "monitor": "val_loss",  # Monitor validation loss
    "patience": 20,         # Stop if no improvement for 20 epochs
    "restore_best_weights": True
}

# Train model
model, history = generate_model(
    feature_train_norm, target_train_norm, 
    model_architecture=architecture, 
    epochs=200, batch_size=32, optimizer='adam', 
    loss='mse', metrics=['mae'], learning_rate=0.001, 
    early_stopping_params=early_stopping_config
)



# Save model, history, and scaler values
model.save(model_path + "/" + model_name +  ".keras")

joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
joblib.dump(target_scaler, model_path + '/target_scaler.pkl')

# Save the history
with open(model_path + '/history.json', 'w') as f:
    json.dump(history.history, f)


#modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test)
metrics_dict =get_model_metrics(model_name, model_path, feature_test, target_test)
#metrics_dict = modelProcess.get_model_metrics(model_name, model_path, feature_train, target_train)
# Round to 4 decimal places


print(metrics_dict)