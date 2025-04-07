import numpy as np
import os
import joblib
import json
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

from keras.models import Sequential, load_model
from keras.layers import Dense
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, Flatten, Dropout, LSTM, BatchNormalization
from tensorflow.keras.optimizers import Adam

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
# 🔹 Function to Get the Model Metrics
# ------------------------------------------------------------
def get_model_metrics(model_name, model_path, feature_test, target_test):
    """
    Loads a trained model, evaluates it on test data, and returns performance metrics.

    Args:
    - model_name (str): Name of the saved model.
    - model_path (str): Path to the model directory.
    - feature_test (array-like): Feature test dataset.
    - target_test (array-like): Target test dataset.

    Returns:
    - metrics_dict (dict): Dictionary containing R² score, MAE, RMSE, and MSE.
    """

    print(np.shape(feature_test))  # Should show something like (num_samples, 3)
    print(np.shape(target_test))   # Should show something like (num_samples, 3)

    # Load the trained model
    model = load_model(os.path.join(model_path, model_name + ".keras"))

    # Load scalers
    feature_scaler = joblib.load(os.path.join(model_path, 'feature_scaler.pkl'))
    target_scaler = joblib.load(os.path.join(model_path, 'target_scaler.pkl'))

    # Normalize the test features


    print("GOTCHAAAA: ", np.shape(feature_test))

    feature_test_norm = feature_scaler.transform(feature_test)

    # Make predictions on normalized test data
    predictions_norm = model.predict(feature_test_norm)

    # Reshape predictions for inverse transformation
    if predictions_norm.ndim == 1:
        predictions_norm = predictions_norm.reshape(-1, 1)

    # Denormalize predictions
    predictions = target_scaler.inverse_transform(predictions_norm)

    # Compute error metrics
    r2 = r2_score(target_test, predictions)
    mae = mean_absolute_error(target_test, predictions)
    mse = mean_squared_error(target_test, predictions)
    rmse = np.sqrt(mse)

    # Store metrics in a dictionary
    metrics_dict = {
        "R2 Score": r2,
        "Mean Absolute Error (MAE)": mae,
        "Mean Squared Error (MSE)": mse,
        "Root Mean Squared Error (RMSE)": rmse
    }

    return metrics_dict
