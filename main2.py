import sys
import numpy as np
import os
import random
import rf.rf as rfProcess
import rf.inductor as inductor
import model.model as modelProcess
import matplotlib.pyplot as plt


import joblib
import json
from keras.models import load_model

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import KFold
import skrf as rf




def generate_RI_model_cv(npz_file_path,model_name, n_splits=5):

    # Load the npz file
    data = np.load(npz_file_path)
    
    # Get the frequency points and target names
    frequency_points = data['frequency_points']
    feature_names = data['feature_names']
    target_names = data['target_names']
    
    features = data['features']
    targets = data['targets']

    nSamples = np.shape(features)[0]
    print(nSamples)

    features = data['features'][:,:-1]
    #targets_flattened = targets.reshape(nSamples, -1)
    targets_flattened = targets

    print(np.shape(targets_flattened))
    print(features)

    #model_name = "transformer32"
    model_path = "model_library/" + model_name

    # Create the directory if it does not exist
    if not os.path.exists(model_path):
        os.makedirs(model_path)


    kfold = KFold(n_splits=5, shuffle=True, random_state=random.randint(0, 1000))

    r2_scores, mae_scores, mse_scores = [], [], []


    fold_idx = 1
    for train_idx, test_idx in kfold.split(features):
        # Split data into training and testing for the current fold
        feature_train, feature_test = features[train_idx], features[test_idx]
        target_train, target_test = targets_flattened[train_idx], targets_flattened[test_idx]


        print(np.shape(feature_train))
        print(np.shape(feature_test))
        print(np.shape(target_train))
        print(np.shape(target_test))

    
        feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"
        )
    
    
        # Reshape target data for dense network
        target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
        target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)


        model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=200, batch_size=32, optimizer='adam', 
                  loss='mse', metrics=['mae'])
    
        # Save model, history, and scaler values
        model.save(model_path + "/" + model_name +  ".keras")

        joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
        joblib.dump(target_scaler, model_path + '/target_scalers.pkl')

        # Save the history
        with open(model_path + '/history.json', 'w') as f:
            json.dump(history.history, f)


        r2,mae,mse = modelProcess.get_model_metrics(model_name, model_path, feature_test, target_test)

        # Append the fold metrics
        r2_scores.append(r2)
        mae_scores.append(mae)
        mse_scores.append(mse)

        print(f"Fold {fold_idx} - R2: {r2}, MAE: {mae}, MSE: {mse}")

        fold_idx += 1


      # Average metrics across all folds
    avg_r2 = np.mean(r2_scores)
    avg_mae = np.mean(mae_scores)
    avg_mse = np.mean(mse_scores)

    print(f"\nAverage R2 score across {n_splits} folds: {avg_r2}")
    print(f"Average MAE across {n_splits} folds: {avg_mae}")
    print(f"Average MSE across {n_splits} folds: {avg_mse}")




def generate_RI_model(npz_file_path,model_name, train_portion= 0.8):

  # Load the npz file
    data = np.load(npz_file_path)
    
    geometric_paremeters_names = data['geometric_paremeters_names']
    geometric_parameters = data['geometric_parameters']
    s_parameter_names = data['s_parameter_names']
    s_parameters = data['s_parameters']
    frequency_points = data['frequency_points']

    # Get the frequency points and target names
    frequency_points = data['frequency_points']
    feature_names = data['geometric_paremeters_names']
    target_names = data['s_parameter_names']
    
    #features = s_parameters.reshape(s_parameters.shape[0], -1)
    #targets =  geometric_parameters[:,:-1]
    

    targets = s_parameters.reshape(s_parameters.shape[0], -1)
    features = geometric_parameters[:,:-1] #this is to remove the fourth member "N" which is the number of rings and is redundant for now


    print(np.shape(features))
    print(np.shape(targets))
    #print(np.shape(targets_flattened))
    #print(features)

    
    #model_name = "transformer32"
    model_path = "model_library/" + model_name

    # Create the directory if it does not exist
    if not os.path.exists(model_path):
        os.makedirs(model_path)

    feature_train, feature_test, target_train, target_test = modelProcess.create_sets_for_training(features, targets, 0.2, train_portion , random.randint(0, 1000))

    print(np.shape(feature_train))
    print(np.shape(feature_test))
    print(np.shape(target_train))
    print(np.shape(target_test))



    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data_sets(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"
    )




    print(np.shape(feature_train_norm))
    print(np.shape(feature_test_norm))
    print(np.shape(target_train_norm))
    print(np.shape(target_test_norm))



    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)

    model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=200, batch_size=32, optimizer='adam', 
                  loss='mse', metrics=['mae'])

    # Save model, history, and scaler values
    model.save(model_path + "/" + model_name +  ".keras")

    joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
    joblib.dump(target_scaler, model_path + '/target_scalers.pkl')

    # Save the history
    with open(model_path + '/history.json', 'w') as f:
       json.dump(history.history, f)


    #modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test)
    r2,mae,mse = modelProcess.get_model_metrics(model_name, model_path, feature_test, target_test)
    # Round to 4 decimal places

    return r2,mae,mse






def generate_inverse_RI_model(npz_file_path, model_name, train_portion=0.8):
    # Load the npz file
    data = np.load(npz_file_path)
    
    geometric_paremeters_names = data['geometric_paremeters_names']
    geometric_parameters = data['geometric_parameters']
    s_parameter_names = data['s_parameter_names']
    s_parameters = data['s_parameters']
    frequency_points = data['frequency_points']

    # Get the frequency points and target names
    frequency_points = data['frequency_points']
    feature_names = data['geometric_paremeters_names']
    target_names = data['s_parameter_names']
    
    #features = s_parameters.reshape(s_parameters.shape[0], -1)
    #targets =  geometric_parameters[:,:-1]
    

    features = s_parameters.reshape(s_parameters.shape[0], -1)
    targets  = geometric_parameters[:,:-1] #this is to remove the fourth member "N" which is the number of rings and is redundant for now


    print(np.shape(features))
    print(np.shape(targets))
    #print(np.shape(targets_flattened))
    #print(features)

    
    #model_name = "transformer32"
    model_path = "model_library/" + model_name

    # Create the directory if it does not exist
    if not os.path.exists(model_path):
        os.makedirs(model_path)

    feature_train, feature_test, target_train, target_test = modelProcess.create_sets_for_training(features, targets, 0.2, train_portion , random.randint(0, 1000))

    print(np.shape(feature_train))
    print(np.shape(feature_test))
    print(np.shape(target_train))
    print(np.shape(target_test))



    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data_sets(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="standard"
    )




    print(np.shape(feature_train_norm))
    print(np.shape(feature_test_norm))
    print(np.shape(target_train_norm))
    print(np.shape(target_test_norm))



    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)

    model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=1000, batch_size=64, optimizer='adam', 
                  loss='mse', metrics=['mae'], learning_rate=0.001)

    # Save model, history, and scaler values
    model.save(model_path + "/" + model_name +  ".keras")

    joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
    joblib.dump(target_scaler, model_path + '/target_scalers.pkl')

    # Save the history
    with open(model_path + '/history.json', 'w') as f:
       json.dump(history.history, f)


    #modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test)
    r2,mae,mse = modelProcess.get_model_metrics(model_name, model_path, feature_test, target_test)
    # Round to 4 decimal places

    return r2,mae,mse


    

def learning_curve_formation(npz_file_path, model_name):

    r2_data = []
    mae_data = []
    mse_data = []

    # Define train portions from 1% to 80% for training
    #train_portions = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    train_portions = [0.01, 0.02, 0.03, 0.04, 0.05,  0.1, 0.5, 0.8]
  
    # Number of runs to average results
    n_runs = 3

    for p in train_portions:
        r2_sum = 0
        mae_sum = 0
        mse_sum = 0

        for i in range(n_runs):
            # Generate model and get metrics
            r2, mae, mse = generate_RI_model(npz_file_path, model_name, p)
            r2_sum += r2
            mae_sum += mae
            mse_sum += mse

        # Calculate averages
        r2_avg = r2_sum / n_runs
        mae_avg = mae_sum / n_runs
        mse_avg = mse_sum / n_runs

        # Append the averages to the respective lists
        r2_data.append(round(r2_avg,4))
        mae_data.append(round(mae_avg,4))
        mse_data.append(round(mse_avg,4))

    # Print the arrays for R2, MAE, and MSE
    print(f"Train Protions: {train_portions}")
    print(f"R2 data: {r2_data}")
    print(f"MAE data: {mae_data}")
    print(f"MSE data: {mse_data}")

    # Return the collected data for further use
    return r2_data, mae_data, mse_data


def compare_model(npz_file_path, model_name, sampleId):
    pass

    data = np.load(npz_file_path)


    features = data['features']
    targets = data['targets']
    frequency_points = data['frequency_points']


    
    nSamples = np.shape(features)[0]
    print(nSamples)

    features = data['features'][:,:-1]
    targets_flattened = targets.reshape(nSamples, -1)

    print(np.shape(targets_flattened))
    print(features)


    model_path = "model_library/" + model_name

    denormalized_predictions = modelProcess.predict_from_model(model_name, model_path, features[sampleId], targets.shape)


    original_data = targets[sampleId]

    print(np.shape(original_data))
    print(np.shape(np.squeeze(denormalized_predictions)))


    plot_s_params_comparison(original_data, denormalized_predictions, frequency_points, save_path="myplot.png")


def calculate_magnitude_db(real, imag):
    """Calculate the magnitude in dB from real and imaginary parts."""
    magnitude = np.sqrt(real**2 + imag**2)
    magnitude_db = 20 * np.log10(magnitude)
    return magnitude_db



def plot_s_params_comparison(original_data, denormalized_predictions, x_axis, save_path="s_param_comparison.png"):
    """
    Plots S11, S21, and S22 in dB from the original and predicted data.
    
    Parameters:
    - original_data: (8, n) array (real and imaginary parts for S11, S12, S21, S22)
    - denormalized_predictions: (1, 8, n) array, predicted real and imaginary parts
    - x_axis: array for X-axis values (e.g., frequency points)
    - save_path: path to save the comparison plot
    """
    
    # Set larger font sizes
    plt.rcParams.update({
        'font.size': 18,        # Increase default font size
        'axes.titlesize': 22,   # Larger title font size
        'axes.labelsize': 18,   # Larger label size for axes
        'legend.fontsize': 16,  # Larger legend font size
        'xtick.labelsize': 18,  # Larger X-axis tick size
        'ytick.labelsize': 18   # Larger Y-axis tick size
    })
    
    # Squeeze the predictions to match original data
    denormalized_predictions_squeezed = np.squeeze(denormalized_predictions)
    
    # Separate the real and imaginary parts for each S-parameter
    s11_real_original, s11_imag_original = original_data[0], original_data[1]
    s21_real_original, s21_imag_original = original_data[4], original_data[5]
    s22_real_original, s22_imag_original = original_data[6], original_data[7]
    
    s11_real_pred, s11_imag_pred = denormalized_predictions_squeezed[0], denormalized_predictions_squeezed[1]
    s21_real_pred, s21_imag_pred = denormalized_predictions_squeezed[4], denormalized_predictions_squeezed[5]
    s22_real_pred, s22_imag_pred = denormalized_predictions_squeezed[6], denormalized_predictions_squeezed[7]
    
    # Calculate the magnitudes in dB for each S-parameter
    s11_db_original = calculate_magnitude_db(s11_real_original, s11_imag_original)
    s21_db_original = calculate_magnitude_db(s21_real_original, s21_imag_original)
    s22_db_original = calculate_magnitude_db(s22_real_original, s22_imag_original)
    
    s11_db_pred = calculate_magnitude_db(s11_real_pred, s11_imag_pred)
    s21_db_pred = calculate_magnitude_db(s21_real_pred, s21_imag_pred)
    s22_db_pred = calculate_magnitude_db(s22_real_pred, s22_imag_pred)
    
    # Create subplots for S11, S21, S22 comparisons
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    
    # Plot S11
    axs[0].plot(x_axis, s11_db_original, label="Original S11", color='blue')
    axs[0].plot(x_axis, s11_db_pred, label="Predicted S11", color='orange', linestyle='--')
    axs[0].set_title("S11 (dB)")
    axs[0].set_xlabel("Frequency")
    axs[0].legend()
    
    # Plot S21 (since S12 is similar to S21, only S21 is shown)
    axs[1].plot(x_axis, s21_db_original, label="Original S21", color='blue')
    axs[1].plot(x_axis, s21_db_pred, label="Predicted S21", color='orange', linestyle='--')
    axs[1].set_title("S21 (dB)")
    axs[1].set_xlabel("Frequency")
    axs[1].legend()
    
    # Plot S22
    axs[2].plot(x_axis, s22_db_original, label="Original S22", color='blue')
    axs[2].plot(x_axis, s22_db_pred, label="Predicted S22", color='orange', linestyle='--')
    axs[2].set_title("S22 (dB)")
    axs[2].set_xlabel("Frequency")
    axs[2].legend()

    # Adjust layout and save the figure
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Comparison plot saved to {save_path}")


import numpy as np



r2,mae,mse = generate_inverse_RI_model('/mnt/storage/conure_data/tsmc65/transformers/transformer_3_3/s_parameters_data.npz',"Fmodel", train_portion= 0.8)
r2,mae,mse = generate_RI_model('/mnt/storage/conure_data/tsmc65/transformers/transformer_3_3/s_parameters_data.npz',"Imodel", train_portion= 0.8)
print(r2,mae,mse)

exit()


npz_file_path = '/mnt/storage/conure_data/tsmc65/transformers/transformer_3_3/s_parameters_data.npz'
data = np.load(npz_file_path)




geometric_paremeters_names = data['geometric_paremeters_names']
geometric_parameters = data['geometric_parameters']
s_parameter_names = data['s_parameter_names']
s_parameters = data['s_parameters']
frequency_points = data['frequency_points']

# Get the frequency points and target names
frequency_points = data['frequency_points']
feature_names = data['geometric_paremeters_names']
target_names = data['s_parameter_names']

#features = s_parameters.reshape(s_parameters.shape[0], -1)
#targets =  geometric_parameters[:,:-1]


features = s_parameters.reshape(s_parameters.shape[0], -1)
targets = geometric_parameters[:,:-1] #this is to remove the fourth member "N" which is the number of rings and is redundant for now




predictions = modelProcess.predict_from_model_new("test", '/projects/bitstream/emon/projects/conure/model_library/test', features[72])
print(predictions)
exit()




#compare_model('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727866838645/s_parameters_data.npz', 'transformer11', 90)
#compare_model('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727886947419/s_parameters_data.npz', 'transformer43', 90)
#compare_model('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727976329579/s_parameters_data.npz', 'transformer22', 100)
#compare_model('/projects/bitstream/emon/conure_workspace/sessions/c8b07d3d-21c5-478e-b5e9-7df39b02041c/sweep/1727834955638/s_parameters_data.npz', 'transformer21', 80)
#compare_model('/projects/bitstream/emon/conure_workspace/sessions/3f2c7233-b711-4f27-a0f5-4eed414967d9/sweep/1729092265708/s_parameters_data.npz', 'transformer32', 60)
#compare_model('/projects/bitstream/emon/conure_workspace/sessions/3f2c7233-b711-4f27-a0f5-4eed414967d9/sweep/1729128630730/s_parameters_data.npz', 'transformer33', 100)



#1_1
#learning_curve_formation('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727866838645/s_parameters_data.npz', 'transformer11')

#4_3
#learning_curve_formation('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727886947419/s_parameters_data.npz','transformer43')

#2_2
#learning_curve_formation('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727976329579/s_parameters_data.npz','transformer22')


#1_2
#learning_curve_formation('/projects/bitstream/emon/conure_workspace/sessions/c8b07d3d-21c5-478e-b5e9-7df39b02041c/sweep/1727834955638/s_parameters_data.npz','transformer21')



#3_2
#learning_curve_formation('/projects/bitstream/emon/conure_workspace/sessions/3f2c7233-b711-4f27-a0f5-4eed414967d9/sweep/1729092265708/s_parameters_data.npz','transformer32')



#3_3
#learning_curve_formation('/projects/bitstream/emon/conure_workspace/sessions/3f2c7233-b711-4f27-a0f5-4eed414967d9/sweep/1729128630730/s_parameters_data.npz','transformer33')


