import numpy as np
import rf.rf as rfProcess



from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import r2_score,mean_absolute_error, mean_squared_error
from keras.models import Sequential, load_model
from keras.layers import Dense, Flatten
from keras.optimizers import Adam
from keras.losses import MeanSquaredError
from tensorflow import keras
#from kerastuner import tuners as kt
from keras.callbacks import EarlyStopping

import os
import joblib
import json
import matplotlib.pyplot as plt
import numpy as np  # Added missing numpy import

import keras
#import kerastuner as kt


def load_data(filename):
    t = np.load(filename)

    designParameters = np.array(t["designParameters"])
    sParameters = np.array(t["sParameters"])
    frequency = np.array(t["frequency"])
    
    return designParameters, sParameters, frequency




def create_sets_for_training(features, target, test_size, train_size, random_state):
    feature_train, feature_test, target_train, target_test = train_test_split(features, target, test_size=test_size, train_size=train_size,  random_state=random_state)
    return feature_train, feature_test, target_train, target_test



def normalize_data_sets(feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"):
    """
    Normalizes feature and target datasets using the specified scaling methods.

    Parameters:
    - feature_train: Training feature data
    - feature_test: Testing feature data
    - target_train: Training target data
    - target_test: Testing target data
    - feature_method: Normalization method for features ("standard" or "minmax")
    - target_method: Normalization method for targets ("standard" or "minmax")

    Returns:
    - feature_train_norm: Normalized training features
    - feature_test_norm: Normalized testing features
    - target_train_norm: Normalized training targets
    - target_test_norm: Normalized testing targets
    - feature_scaler: Scaler used for features
    - target_scaler: Scaler used for targets
    """

    # Select the appropriate scaler for features
    if feature_method == "standard":
        feature_scaler = StandardScaler()
    elif feature_method == "minmax":
        feature_scaler = MinMaxScaler()
    else:
        raise ValueError("Invalid feature normalization method. Choose 'standard' or 'minmax'.")

    # Select the appropriate scaler for targets
    if target_method == "standard":
        target_scaler = StandardScaler()
    elif target_method == "minmax":
        target_scaler = MinMaxScaler()
    else:
        raise ValueError("Invalid target normalization method. Choose 'standard' or 'minmax'.")

    # Fit and transform feature data
    feature_train_norm = feature_scaler.fit_transform(feature_train)
    feature_test_norm = feature_scaler.transform(feature_test)

    # Fit and transform target data
    target_train_norm = target_scaler.fit_transform(target_train)
    target_test_norm = target_scaler.transform(target_test)

    return feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler


# def normalize_data(feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"):

#     # Choose normalization method for features
#     if feature_method == "standard":
#         feature_scaler = StandardScaler().fit(feature_train)
#     elif feature_method == "minmax":
#         feature_scaler = MinMaxScaler().fit(feature_train)
#     else:
#         raise ValueError("Invalid feature_method. Choose either 'standard' or 'minmax'.")
        
#     feature_train_normalized = feature_scaler.transform(feature_train)
#     feature_test_normalized = feature_scaler.transform(feature_test)

#     # Normalize target data
#     target_train_normalized = np.empty_like(target_train)
#     target_test_normalized = np.empty_like(target_test)
#     target_scalers = []

#     for i in range(target_train.shape[1]):
#         # Choose normalization method for targets
#         if target_method == "standard":
#             scaler = StandardScaler().fit(target_train[:, i, :])
#         elif target_method == "minmax":
#             scaler = MinMaxScaler().fit(target_train[:, i, :])
#         else:
#             raise ValueError("Invalid target_method. Choose either 'standard' or 'minmax'.")
            
#         target_train_normalized[:, i, :] = scaler.transform(target_train[:, i, :])
#         target_test_normalized[:, i, :] = scaler.transform(target_test[:, i, :])
#         target_scalers.append(scaler)
    
#     return feature_train_normalized, feature_test_normalized, target_train_normalized, target_test_normalized, feature_scaler, target_scalers





# def denormalize_data(data_normalized, scalers):
#     if data_normalized.ndim == 3:  # Shape is [a:b:c]
#         data_denormalized = np.zeros_like(data_normalized)
#         for i, scaler in enumerate(scalers):
#             data_denormalized[:, i, :] = scaler.inverse_transform(data_normalized[:, i, :])
#     elif data_normalized.ndim == 2:  # Shape is [a:b]
#         data_denormalized = np.zeros_like(data_normalized)
#         for i, scaler in enumerate(scalers):
#             data_denormalized[:, i] = scaler.inverse_transform(data_normalized[:, i].reshape(-1, 1)).flatten()
#     else:
#         raise ValueError(f"Unexpected number of dimensions: {data_normalized.ndim}")
    
#     return data_denormalized


def denormalize_data(data_normalized, scaler):
    """
    Reverses normalization using the provided scaler.

    Parameters:
    - data_normalized: The normalized data.
    - scaler: The scaler object used for normalization.

    Returns:
    - data_original: The denormalized (original scale) data.
    """
    
    if scaler is None:
        raise ValueError("Scaler object is required for denormalization.")

    return scaler.inverse_transform(data_normalized)

def generate_model(feature_train, feature_test, target_train, target_test, 
                   epochs=50, batch_size=32, optimizer='adam', 
                   loss='mse', metrics=['mae'], learning_rate=0.001):
    """
    Generate and train a simple neural network model.
    
    Args:
    - feature_train, feature_test, target_train, target_test : Training and test data
    - epochs : Number of epochs for training
    - batch_size : Size of batches for training
    - optimizer : Optimizer for training
    - loss : Loss function
    - metrics : List of metrics to monitor
    - learning_rate : Learning rate for optimizer
    
    Returns:
    - model : Trained Keras model
    - history : History object with training/validation loss and metrics data
    """
    
    # Ensure input data shapes are compatible
    if feature_train.shape[0] != target_train.shape[0] or feature_test.shape[0] != target_test.shape[0]:
        raise ValueError("Mismatched data shapes: check sample counts.")
    if feature_train.shape[1] != feature_test.shape[1]:
        raise ValueError("Mismatched feature dimensions between train and test sets.")
    
    # If optimizer is 'adam', define the Adam optimizer with the custom learning rate
    if optimizer == 'adam':
        optimizer = Adam(learning_rate=learning_rate)
    # You can add more optimizers here if you want to support others, e.g., SGD, RMSprop


    # # 1. Define the Model Architecture (selected after hyperparameter tuning)
    # model = Sequential([
    #     Dense(288, activation='relu', input_shape=(feature_train.shape[1],)),  # Input layer
    #     Dense(3584, activation='relu'),  # Hidden layer
    #     Dense(3584, activation='relu'),  # Hidden layer
    #     Dense(target_train.shape[1], activation='linear')  # Output layer
    # ])


    # Define the Model Architecture
    model = Sequential([
        Dense(1000, activation='relu', input_shape=(feature_train.shape[1],)),  # Input layer
        Dense(100, activation='relu'),
        Dense(4000, activation='relu'),
        Dense(100, activation='relu'),
        Dense(target_train.shape[1], activation='linear')  # Output layer
    ])

    # Compile the model with the specified optimizer and loss function
    model.compile(optimizer=optimizer, loss=loss, metrics=metrics)

    # Optional: Early Stopping to prevent overfitting
    early_stopping = EarlyStopping(monitor='val_loss', patience=50, restore_best_weights=True)



    # Train the model
    history = model.fit(
        feature_train, 
        target_train, 
        validation_data=(feature_test, target_test), 
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stopping]  # Optional: Early stopping callback
    )
    
    return model, history






def optimize_model(feature_train, feature_test, target_train, target_test, directory, project_name):
   # Define a function to create the Keras model for hyperparameter tuning
    def build_model(hp):
        model = keras.Sequential([
            keras.layers.Dense(
                units=hp.Int('units_first_layer', min_value=32, max_value=512, step=128),
                activation='relu',
                input_shape=(feature_train.shape[1],)
            ),
        ])
        
        # Add multiple hidden layers with different numbers of neurons
        for i in range(hp.Int('num_hidden_layers', min_value=1, max_value=3)):  # Example: Up to 3 hidden layers
            model.add(keras.layers.Dense(
                units=hp.Int(f'units_hidden_layer_{i}', min_value=512, max_value=4096, step=1024),
                activation=hp.Choice('activation', values=['relu', 'tanh']),
            ))

        model.add(keras.layers.Dense(target_train.shape[1], activation='linear'))
        
        # Add a hyperparameter for learning rate
        hp_learning_rate = hp.Choice('learning_rate', values=[1e-2, 1e-3, 1e-4])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=hp_learning_rate),  # Use the learning rate hyperparameter
            loss=hp.Choice('loss', values=['mse', 'mae']),
            metrics=['mae']
        )
        
        return model

    ########## #For HYPERBAND optimisation
    # # Create a tuner
    # tuner = kt.Hyperband(
    #     build_model,
    #     objective='val_loss',
    #     max_epochs=100,
    #     factor=3,
    #     directory='my_dir',
    #     project_name='my_project'
    # )

    # # Search for the best hyperparameters, including learning rate
    # tuner.search(feature_train, target_train, epochs=50, validation_data=(feature_test, target_test))



    ########## For BAYESIAN optimisation
    # Create a tuner with BayesianOptimization
    tuner = kt.BayesianOptimization(
        build_model,
        objective='val_loss',
        max_trials=100, # Number of hyperparameter combinations to test
        directory='my_dir',
        project_name='my_project'
    )

    # Create early stopping callback
    early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    # Search for the best hyperparameters, adding the early stopping callback
    tuner.search(feature_train, target_train, epochs=50, validation_data=(feature_test, target_test), callbacks=[early_stopping])


    # Get the best model and hyperparameters
    best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]

    # Build and compile the best model using the best hyperparameters
    best_model = tuner.hypermodel.build(best_hps)

    # Print the best hyperparameters for each hidden layer
    print("Best Hyperparameters:")
    print(f"Units (First Layer): {best_hps.get('units_first_layer')}")
    for i in range(best_hps.get('num_hidden_layers')):
        print(f"Units (Hidden Layer {i + 1}): {best_hps.get(f'units_hidden_layer_{i}')}")
    print(f"Activation: {best_hps.get('activation')}")
    print(f"Learning Rate: {best_hps.get('learning_rate')}")
    print(f"Loss: {best_hps.get('loss')}")

    return best_model



def predict_from_model(model_name, model_path, feature, target_shape):
    loaded_model = load_model(model_path + "/" + model_name +  ".keras")
    
    # To load them back:
    feature_scaler_loaded = joblib.load(model_path + '/feature_scaler.pkl')
    target_scalers_loaded = joblib.load(model_path + '/target_scalers.pkl')

    # Load the history
    with open(model_path + '/history.json', 'r') as f:
        loaded_history = json.load(f)


    new_feature_data_reshaped = feature.reshape(1, -1)

    # Normalize the reshaped feature data using the same scaler used for training data
    new_feature_data_norm = feature_scaler_loaded.transform(new_feature_data_reshaped)


    # Predict using the model
    predictions = loaded_model.predict(new_feature_data_norm)

    # If you want to reshape the predictions to the original shape (before reshaping for training)
    predictions_reshaped = predictions.reshape(-1, target_shape[1], target_shape[2])

    # If you normalized the target data using MinMaxScaler and you want to denormalize predictions to original scale
    denormalized_predictions = denormalize_data(predictions_reshaped, target_scalers_loaded)

    return denormalized_predictions

def predict_from_model_new(model_name, model_path, feature):
    # Load the model
    loaded_model = load_model(model_path + "/" + model_name + ".keras")
    
    # Load scalers
    feature_scaler_loaded = joblib.load(model_path + '/feature_scaler.pkl')
    target_scaler_loaded = joblib.load(model_path + '/target_scalers.pkl')

    # Load the history (optional, you can remove if you don't need it)
    with open(model_path + '/history.json', 'r') as f:
        loaded_history = json.load(f)

    # Reshape the feature input for prediction if it's a single sample
    if feature.ndim == 1:  # Single sample
        new_feature_data_reshaped = feature.reshape(1, -1)
    else:  # Multiple samples
        new_feature_data_reshaped = feature

    # Normalize the feature input using the trained scaler
    new_feature_data_norm = feature_scaler_loaded.transform(new_feature_data_reshaped)

    # Make predictions
    predictions_norm = loaded_model.predict(new_feature_data_norm)

    # If predictions are 1D (for single sample), reshape them to 2D for inverse transformation
    if predictions_norm.ndim == 1:
        predictions_norm = predictions_norm.reshape(1, -1)

    # Denormalize the predictions using the target scaler
    predictions_reshaped = target_scaler_loaded.inverse_transform(predictions_norm)

    return predictions_reshaped

    

# def print_model_metrics(model_name, model_path, feature_test, target_test ):


#     model = load_model(model_path + "/" + model_name +  ".h5")
#     feature_scaler = joblib.load(model_path + '/feature_scaler.pkl')
#     target_scaler = joblib.load(model_path + '/target_scalers.pkl')



#     # Normalize features using the feature_scaler
#     feature_test_norm = feature_scaler.transform(feature_test)
    
#     # Predict using the model
#     predictions_norm = model.predict(feature_test_norm)
    
#     # Reshape the predictions to the original target_test shape
#     predictions_norm_reshaped = predictions_norm.reshape(target_test.shape)
    
#     # Denormalize the predictions
#     predictions = denormalize_data(predictions_norm_reshaped, target_scaler)
    
#     # Flatten the arrays for metric computation
#     target_test_flat = target_test.reshape(-1)
#     predictions_flat = predictions.reshape(-1)
    
#     # Calculate and print metrics
#     r2 = r2_score(target_test_flat, predictions_flat)
#     mae = mean_absolute_error(target_test_flat, predictions_flat)
#     mse = mean_squared_error(target_test_flat, predictions_flat)
    
#     print(f"R^2 Score: {r2:.4f}")
#     print(f"Mean Absolute Error (MAE): {mae:.4f}")
#     print(f"Mean Squared Error (MSE): {mse:.4f}")

#     # Calculate RMSE
#     rmse = np.sqrt(mse)
#     print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")

#     # Calculate MAPE
#     mape = 100 * np.mean(np.abs((target_test_flat - predictions_flat) / target_test_flat))
#     print(f"Mean Absolute Percentage Error (MAPE): {mape:.4f}%")

#     # Calculate standard deviation of errors
#     errors = target_test_flat - predictions_flat
#     std_errors = np.std(errors)
#     print(f"Standard Deviation of Errors: {std_errors:.4f}")


def get_model_metrics(model_name, model_path, feature_test, target_test):
    # Load the model
    model = load_model(model_path + "/" + model_name + ".keras")
    
    # Load the feature and target scalers
    feature_scaler = joblib.load(model_path + '/feature_scaler.pkl')
    target_scaler = joblib.load(model_path + '/target_scalers.pkl')

    # Normalize features using the feature_scaler
    feature_test_norm = feature_scaler.transform(feature_test)

    # Predict using the model
    predictions_norm = model.predict(feature_test_norm)

    # Reshape the predictions to match the target_test shape
    predictions_norm_reshaped = predictions_norm.reshape(target_test.shape)

    # Denormalize the predictions
    predictions = denormalize_data(predictions_norm_reshaped, target_scaler)

    # Flatten the arrays for metric computation
    target_test_flat = target_test.reshape(-1)
    predictions_flat = predictions.reshape(-1)

    # Calculate metrics
    r2 = r2_score(target_test_flat, predictions_flat)
    mae = mean_absolute_error(target_test_flat, predictions_flat)
    mse = mean_squared_error(target_test_flat, predictions_flat)
    rmse = np.sqrt(mse)

    # Avoid division by zero in MAPE calculation by adding a small epsilon
    epsilon = 1e-8
    mape = 100 * np.mean(np.abs((target_test_flat - predictions_flat) / (target_test_flat + epsilon)))

    # Standard deviation of errors
    std_errors = np.std(target_test_flat - predictions_flat)

    #Print metrics
    print(f"R^2 Score: {r2:.4f}")
    print(f"Mean Absolute Error (MAE): {mae:.4f}")
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")
    print(f"Mean Absolute Percentage Error (MAPE): {mape:.4f}%")
    print(f"Standard Deviation of Errors: {std_errors:.4f}")

    return r2,mae,mse



def get_inverse_model_metrics(model_name, model_path, target_test, feature_test):
    # Load the model
    model = load_model(model_path + "/" + model_name + ".keras")
    
    # Load the feature and target scalers
    feature_scaler = joblib.load(model_path + '/feature_scaler.pkl')
    target_scaler = joblib.load(model_path + '/target_scalers.pkl')

    # Normalize features using the feature_scaler
    feature_test_norm = feature_scaler.transform(feature_test)

    # Predict using the model
    predictions_norm = model.predict(feature_test_norm)

    # Reshape the predictions to match the target_test shape
    predictions_norm_reshaped = predictions_norm.reshape(target_test.shape)

    # Denormalize the predictions
    predictions = denormalize_data(predictions_norm_reshaped, target_scaler)

    # Flatten the arrays for metric computation
    target_test_flat = target_test.reshape(-1)
    predictions_flat = predictions.reshape(-1)

    # Calculate metrics
    r2 = r2_score(target_test_flat, predictions_flat)
    mae = mean_absolute_error(target_test_flat, predictions_flat)
    mse = mean_squared_error(target_test_flat, predictions_flat)
    rmse = np.sqrt(mse)

    # Avoid division by zero in MAPE calculation by adding a small epsilon
    epsilon = 1e-8
    mape = 100 * np.mean(np.abs((target_test_flat - predictions_flat) / (target_test_flat + epsilon)))

    # Standard deviation of errors
    std_errors = np.std(target_test_flat - predictions_flat)

    #Print metrics
    print(f"R^2 Score: {r2:.4f}")
    print(f"Mean Absolute Error (MAE): {mae:.4f}")
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")
    print(f"Mean Absolute Percentage Error (MAPE): {mape:.4f}%")
    print(f"Standard Deviation of Errors: {std_errors:.4f}")

    return r2,mae,mse


def print_model_metrics(model_name, model_path, feature_test, target_test):
    # Load the model
    model = load_model(model_path + "/" + model_name + ".keras")
    
    # Load the feature and target scalers
    feature_scaler = joblib.load(model_path + '/feature_scaler.pkl')
    target_scaler = joblib.load(model_path + '/target_scalers.pkl')

    # Normalize features using the feature_scaler
    feature_test_norm = feature_scaler.transform(feature_test)

    # Predict using the model
    predictions_norm = model.predict(feature_test_norm)

    # Reshape the predictions to match the target_test shape
    predictions_norm_reshaped = predictions_norm.reshape(target_test.shape)

    # Denormalize the predictions
    predictions = denormalize_data(predictions_norm_reshaped, target_scaler)

    # Flatten the arrays for metric computation
    target_test_flat = target_test.reshape(-1)
    predictions_flat = predictions.reshape(-1)

    # Calculate metrics
    r2 = r2_score(target_test_flat, predictions_flat)
    mae = mean_absolute_error(target_test_flat, predictions_flat)
    mse = mean_squared_error(target_test_flat, predictions_flat)
    rmse = np.sqrt(mse)

    # Avoid division by zero in MAPE calculation by adding a small epsilon
    epsilon = 1e-8
    mape = 100 * np.mean(np.abs((target_test_flat - predictions_flat) / (target_test_flat + epsilon)))

    # Standard deviation of errors
    std_errors = np.std(target_test_flat - predictions_flat)

    # Print metrics
    print(f"R^2 Score: {r2:.4f}")
    print(f"Mean Absolute Error (MAE): {mae:.4f}")
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")
    print(f"Mean Absolute Percentage Error (MAPE): {mape:.4f}%")
    print(f"Standard Deviation of Errors: {std_errors:.4f}")


    

    
def plot_model_learning_curves(model_path, plot_path):
 
    with open(model_path + '/history.json', 'r') as f:
        history = json.load(f)

    if not os.path.exists(plot_path):
    # If not, create the path
        os.makedirs(plot_path)


    # Extract loss (and accuracy if available) from history
    train_loss = history['loss']
    val_loss = history.get('val_loss', [])  # It will be empty if validation loss is not available
    mae = history.get('mae', [])  # It will be empty if validation loss is not available
    val_mae = history.get('val_mae', [])  # It will be empty if validation loss is not available

    # Plot training & validation loss values
    plt.figure(figsize=(12, 5))
    plt.plot(train_loss)
    plt.plot(val_loss)
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'], loc='upper left')
    plt.tight_layout()
    plt.savefig(plot_path + "/learning_curve_loss_and_val_loss.png")


    # Plot training & validation loss values
    plt.figure(figsize=(12, 5))
    plt.plot(mae)
    plt.plot(val_mae)
    plt.title('Model Loss (MAE)')
    plt.ylabel('MAE')
    plt.xlabel('Val Mae')
    plt.legend(['Train', 'Validation'], loc='upper left')
    plt.tight_layout()
    plt.savefig(plot_path + "/learning_curve_mae_and_val_mae.png")