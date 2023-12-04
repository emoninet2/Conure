import sys
import numpy as np


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


def generate_RIQ_model_with_kfold(k_folds):
    model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ"
    model_path = "model_library/" + model_name
    
    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')
    [Q, L] = inductor.s_real_imag_to_q_and_l(sParameters, frequency, Z0=100)
    RIQ_data = np.stack((sParameters[:,0,:], sParameters[:,1,:], Q), axis=1)

    # Define k-folds
    #k_folds = 5
    kfold = KFold(n_splits=k_folds, shuffle=True, random_state=42)
    
    histories = []

    # Initialize lists to store validation losses and MAE for each fold
    val_losses = []
    val_maes = []

    for fold_num, (train_index, val_index) in enumerate(kfold.split(designParameters), 1):
        feature_train, feature_val = designParameters[train_index], designParameters[val_index]
        target_train, target_val = RIQ_data[train_index], RIQ_data[val_index]

        feature_train_norm, feature_val_norm, target_train_norm, target_val_norm, feature_scaler, target_scaler = modelProcess.normalize_data(
            feature_train, feature_val, target_train, target_val, feature_method="standard", target_method="minmax"
        )

        # Reshape target data for the dense network
        target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
        target_val_norm_reshaped = target_val_norm.reshape(target_val.shape[0], -1)

        model, history = modelProcess.generate_model(feature_train_norm, feature_val_norm, target_train_norm_reshaped, target_val_norm_reshaped, 
                      epochs=50, batch_size=32, optimizer='adam', 
                      loss='mse', metrics=['mae'])
        
        # Evaluating the model on the current fold's validation set
        val_loss, val_mae = model.evaluate(feature_val_norm, target_val_norm_reshaped, verbose=0)
        
        print(f"Fold {fold_num} - Validation Loss (MSE): {val_loss:.4f}, Validation MAE: {val_mae:.4f}")
        
        val_losses.append(val_loss)
        val_maes.append(val_mae)

        histories.append(history.history)

        model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ_kfold_" + str(fold_num) 
        model_path = "model_library/" + model_name
        # For demonstration purposes, saving the last model:
        model.save(model_path + "/" + model_name + ".h5")
        joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
        joblib.dump(target_scaler, model_path + '/target_scalers.pkl')

    # Calculate the average validation loss (MSE) and average validation MAE
    avg_val_loss = sum(val_losses) / len(val_losses)
    avg_val_mae = sum(val_maes) / len(val_maes)

    print(f"Average Validation Loss (MSE): {avg_val_loss:.4f}")
    print(f"Average Validation MAE: {avg_val_mae:.4f}")

    # Here you can save or analyze the `histories` list for more insights.
    
    
    
    # If you wish to save all histories:
    with open(model_path + '/all_histories.json', 'w') as f:
        json.dump(histories, f)


def generate_Q_model():
    model_name = "Inductor_Coplanar_1N_to_5N_model_Q"
    model_path = "model_library/" + model_name
    

    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    [Q,L] = inductor.s_real_imag_to_q_and_l(sParameters, frequency, Z0=100)

    Q_reshaped = Q.reshape(Q.shape[0],1, Q.shape[1])

    feature_train, feature_test, target_train, target_test = modelProcess.create_sets_for_training(designParameters, Q_reshaped, 0.2, 0.8, 25)

    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"
    )


    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)


    model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=50, batch_size=32, optimizer='adam', 
                  loss='mse', metrics=['mae'])


    #save model, history, and scalar values 
    model.save(model_path+ "/" + model_name +  ".h5")

    joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
    joblib.dump(target_scaler, model_path + '/target_scalers.pkl')
    #Save the history
    with open(model_path + '/history.json', 'w') as f:
       json.dump(history.history, f)
    
    modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test )


def generate_RIQ_model(tune=0):
    model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ"
    model_path = "model_library/" + model_name
    

    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    [Q,L] = inductor.s_real_imag_to_q_and_l(sParameters, frequency, Z0=100)

    RIQ_data = np.stack((sParameters[:,0,:],sParameters[:,1,:], Q), axis=1)

    feature_train, feature_test, target_train, target_test = modelProcess.create_sets_for_training(designParameters, RIQ_data, 0.2, 0.8, 25)

    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"
    )

    
    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)

    model = []
    if tune == 1:
        print("Tuning Hyperparametes")
        model = modelProcess.optimize_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped)
    else:
        model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=50, batch_size=32, optimizer='adam', 
                  loss='mse', metrics=['mae'])



    #save model, history, and scalar values 
    model.save(model_path+ "/" + model_name +  ".h5")
    joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
    joblib.dump(target_scaler, model_path + '/target_scalers.pkl')
    #Save the history
    with open(model_path + '/history.json', 'w') as f:
       json.dump(history.history, f)
    
    modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test )






def compare_RIQ_model(dataId):
    id = dataId


    model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ"
    model_path = "model_library/" + model_name
    pass


    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    new_feature_data = np.array(designParameters[id])
    actual_data = sParameters[id]

    print(sParameters.shape)
    denormalized_predictions = modelProcess.predict_from_model(model_name, model_path, new_feature_data, (sParameters.shape[0], 3, sParameters.shape[2]))


    S11_real_pred = denormalized_predictions[0][0]
    S11_imag_pred =denormalized_predictions[0][1]
    Q_pred =denormalized_predictions[0][2]
    S11_real_pred =actual_data[0]
    S11_imag_pred =actual_data[1]

    [_,L_pred] = inductor.s_real_imag_to_q_and_l(denormalized_predictions, frequency, Z0=100)
    [Q_actual,L_actual] = inductor.s_real_imag_to_q_and_l(sParameters[id], frequency, Z0=100)


    L_pred = L_pred.reshape(2000)
    #Q_pred = Q_pred.reshape(2000)

     # Plotting L and Q comparison
    plt.figure(figsize=(12, 6))
    
    # Subplot for L comparison
    plt.subplot(1, 2, 1)
    plt.plot(frequency, L_pred, label='Predicted L', color='blue')
    plt.plot(frequency, L_actual, label='Actual L', color='red', linestyle='--')
    plt.xlabel('Frequency')
    plt.ylabel('Inductance (L)')
    plt.title('L Comparison: Predicted vs Actual')
    plt.legend()
    
    # Subplot for Q comparison
    plt.subplot(1, 2, 2)
    plt.plot(frequency, Q_pred, label='Predicted Q', color='blue')
    plt.plot(frequency, Q_actual, label='Actual Q', color='red', linestyle='--')
    plt.ylim(-50, 50)
    plt.xlabel('Frequency')
    plt.ylabel('Quality Factor (Q)')
    plt.title('Q Comparison: Predicted vs Actual')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("L_and_Q_Comparision_model_RIQ.png")

    return Q_pred, L_pred

def generate_RI_model():
    model_name = "Inductor_Coplanar_1N_to_5N_model_RI"
    model_path = "model_library/" + model_name
    

    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')
    feature_train, feature_test, target_train, target_test = modelProcess.create_sets_for_training(designParameters, sParameters, 0.2, 0.8, 25)



    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"
    )


    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)


    model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=50, batch_size=32, optimizer='adam', 
                  loss='mse', metrics=['mae'])


    #save model, history, and scalar values 
    model.save(model_path+ "/" + model_name +  ".h5")

    joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
    joblib.dump(target_scaler, model_path + '/target_scalers.pkl')
    #Save the history
    with open(model_path + '/history.json', 'w') as f:
       json.dump(history.history, f)
    
    modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test )

def compare_RI_model(dataId):
    id = dataId


    model_name = "Inductor_Coplanar_1N_to_5N_model_RI"
    model_path = "model_library/" + model_name
    pass


    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    new_feature_data = np.array(designParameters[id])
    actual_data = sParameters[id]


    denormalized_predictions = modelProcess.predict_from_model(model_name, model_path, new_feature_data, sParameters.shape)


    S11_real_pred = denormalized_predictions[0][0]
    S11_imag_pred =denormalized_predictions[0][1]
    S11_real_actual =actual_data[0]
    S11_imag_actual =actual_data[1]


    [Q_pred,L_pred] = inductor.s_real_imag_to_q_and_l(denormalized_predictions, frequency, Z0=100)
    [Q_actual,L_actual] = inductor.s_real_imag_to_q_and_l(sParameters[id], frequency, Z0=100)

    L_pred = L_pred.reshape(2000)
    Q_pred = Q_pred.reshape(2000)

    # Plotting L and Q comparison
    plt.figure(figsize=(12, 6))
    
    # Subplot for L comparison
    plt.subplot(1, 2, 1)
    plt.plot(frequency, L_pred, label='Predicted L', color='blue')
    plt.plot(frequency, L_actual, label='Actual L', color='red', linestyle='--')
    plt.xlabel('Frequency')
    plt.ylabel('Inductance (L)')
    plt.title('L Comparison: Predicted vs Actual')
    plt.legend()
    
    # Subplot for Q comparison
    plt.subplot(1, 2, 2)
    plt.plot(frequency, Q_pred, label='Predicted Q', color='blue')
    plt.plot(frequency, Q_actual, label='Actual Q', color='red', linestyle='--')
    plt.ylim(-50, 50)
    plt.xlabel('Frequency')
    plt.ylabel('Quality Factor (Q)')
    plt.title('Q Comparison: Predicted vs Actual')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("L_and_Q_Comparision_model_RI.png")

    # Plotting Real and Imaginary comparison
    plt.figure(figsize=(12, 6))
    
    # Subplot for Real part comparison
    plt.subplot(1, 2, 1)
    plt.plot(frequency, S11_real_pred, label='Predicted Real Part', color='blue')
    plt.plot(frequency, S11_real_actual, label='Actual Real Part', color='red', linestyle='--')
    plt.xlabel('Frequency')
    plt.ylabel('Real Part')
    plt.title('S11 Real Part: Predicted vs Actual')
    plt.legend()
    
    # Subplot for Imaginary part comparison
    plt.subplot(1, 2, 2)
    plt.plot(frequency, S11_imag_pred, label='Predicted Imaginary Part', color='blue')
    plt.plot(frequency, S11_imag_actual, label='Actual Imaginary Part', color='red', linestyle='--')
    plt.xlabel('Frequency')
    plt.ylabel('Imaginary Part')
    plt.title('S11 Imaginary Part: Predicted vs Actual')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("Re_and_Im_Comparision_model_RI.png")

    return Q_pred, L_pred


def generate_QL_model():
    print("HOLLAAAAAA")
    model_name = "Inductor_Coplanar_1N_to_5N_model_LQ"
    model_path = "model_library/" + model_name
    

    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')


    [Q,L] = inductor.s_real_imag_to_q_and_l(sParameters, frequency, Z0=100)
    LQ_data = np.stack((L, Q), axis=1)


    feature_train, feature_test, target_train, target_test = modelProcess.create_sets_for_training(designParameters, LQ_data, 0.2, 0.8, 25)


    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data(
        feature_train, feature_test, target_train, target_test, feature_method="standard", target_method="minmax"
    )


    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)


    model, history = modelProcess.generate_model(feature_train_norm, feature_test_norm, target_train_norm_reshaped, target_test_norm_reshaped, 
                  epochs=50, batch_size=32, optimizer='adam', 
                  loss='mse', metrics=['mae'])


    #save model, history, and scalar values 
    model.save(model_path+ "/" + model_name +  ".h5")

    joblib.dump(feature_scaler, model_path + '/feature_scaler.pkl')
    joblib.dump(target_scaler, model_path + '/target_scalers.pkl')
    #Save the history
    with open(model_path + '/history.json', 'w') as f:
       json.dump(history.history, f)
    
    modelProcess.print_model_metrics(model_name, model_path, feature_test, target_test )

def compare_QL_model(dataId):
    id = dataId


    model_name = "Inductor_Coplanar_1N_to_5N_model_LQ"
    model_path = "model_library/" + model_name
    pass


    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    new_feature_data = np.array(designParameters[id])
    actual_data = sParameters[id]


    denormalized_predictions = modelProcess.predict_from_model(model_name, model_path, new_feature_data, sParameters.shape)


    L_pred = denormalized_predictions[0][0]
    Q_pred =denormalized_predictions[0][1]
    S11_real_pred =actual_data[0]
    S11_imag_pred =actual_data[1]



    #[Q_pred,L_pred] = inductor.s_real_imag_to_q_and_l(denormalized_predictions, frequency, Z0=100)
    [Q_actual,L_actual] = inductor.s_real_imag_to_q_and_l(sParameters[id], frequency, Z0=100)


    #L_pred = L_pred.reshape(2000)
    #Q_pred = Q_pred.reshape(2000)

    # Plotting L and Q comparison
    plt.figure(figsize=(12, 6))
    
    # Subplot for L comparison
    plt.subplot(1, 2, 1)
    plt.plot(frequency, L_pred, label='Predicted L', color='blue')
    plt.plot(frequency, L_actual, label='Actual L', color='red', linestyle='--')
    plt.xlabel('Frequency')
    plt.ylabel('Inductance (L)')
    plt.title('L Comparison: Predicted vs Actual')
    plt.legend()
    
    # Subplot for Q comparison
    plt.subplot(1, 2, 2)
    plt.plot(frequency, Q_pred, label='Predicted Q', color='blue')
    plt.plot(frequency, Q_actual, label='Actual Q', color='red', linestyle='--')
    plt.ylim(-50, 50)
    plt.xlabel('Frequency')
    plt.ylabel('Quality Factor (Q)')
    plt.title('Q Comparison: Predicted vs Actual')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("L_and_Q_Comparision_model_LQ.png")

    return Q_pred, L_pred


def debug_RI_model(dataId):
    id = dataId


    model_name = "Inductor_Coplanar_1N_to_5N_model_RI"
    model_path = "model_library/" + model_name
    pass


    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    new_feature_data = np.array(designParameters[id])
    actual_data = sParameters[id]


    denormalized_predictions = modelProcess.predict_from_model(model_name, model_path, new_feature_data, sParameters.shape)


    S11_real_pred = denormalized_predictions[0][0]
    S11_imag_pred =denormalized_predictions[0][1]
    S11_real_actual =actual_data[0]
    S11_imag_actual =actual_data[1]



    [Q_pred,L_pred] = inductor.s_real_imag_to_q_and_l(denormalized_predictions, frequency, Z0=100)
    [Q_actual,L_actual] = inductor.s_real_imag_to_q_and_l(sParameters[id], frequency, Z0=100)

    L_pred = L_pred.reshape(2000)
    Q_pred = Q_pred.reshape(2000)

    

    import pandas as pd
    # Create a numpy array by stacking all your arrays column-wise
    data_to_save = np.column_stack((S11_real_actual, S11_imag_actual, S11_real_pred, S11_imag_pred, Q_pred, Q_actual, L_pred, L_actual))

    # Convert the numpy array to a pandas DataFrame for easier CSV writing
    df = pd.DataFrame(data_to_save, columns=['S11_real_actual', 'S11_imag_actual', 'S11_real_pred', 'S11_imag_pred', 'Q_pred', 'Q_actual','L_pred', 'L_actual'])

    # Save to CSV
    df.to_csv('output_data.csv', index=False)




import os
def plot_model_learning_curves(model_path):


    
    


    with open(model_path + '/history.json', 'r') as f:
        history = json.load(f)



    # Extract loss (and accuracy if available) from history
    #RI_train_loss = history['loss']
    #RI_val_loss = history.get('val_loss', [])  # It will be empty if validation loss is not available
    RIQ_mae = history.get('mae', [])  # It will be empty if validation loss is not available
    RIQ_val_mae = history.get('val_mae', [])  # It will be empty if validation loss is not available




    plot_path = model_path + "/plot/"
    if not os.path.exists(plot_path):
    # If not, create the path
        os.makedirs(plot_path)


    plt.figure(figsize=(6, 3))

    # Using different line styles and markers to distinguish curves
    plt.plot(RIQ_mae, 'b-', marker='o', markevery=10)          # Blue solid line with circle markers
    plt.plot(RIQ_val_mae, 'g--', marker='s', markevery=10)     # Green dashed line with square markers


    plt.title('Model Loss')
    plt.ylabel('Loss (MAE)')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Validation'], loc='upper right')
    plt.tight_layout()
    plt.savefig(plot_path + "/learning_curve.png", dpi=300)

    return RIQ_mae, RIQ_val_mae



def model_comparision(dataId):
    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')
    print(designParameters[dataId])
    
    #generate_RI_model()
    #generate_QL_model()
    #generate_Q_model()
    #generate_RIQ_model()

    
    [Q_RI, L_RI] = compare_RI_model(dataId)
    [Q_QL, L_QL] = compare_QL_model(dataId)

    [Q_RIQ, L_RIQ] = compare_RIQ_model(dataId)


    plot_model_learning_curves()


  # Plotting L and Q comparison
    plt.figure(figsize=(6, 6))
    
    # Subplot for L comparison (top subplot)
    plt.subplot(2, 1, 1)  # 2 rows, 1 column, 1st subplot
    plt.plot(frequency, L_RI, label='RI', linestyle='-')
    plt.plot(frequency, L_QL, label='QL', linestyle='--')
    plt.plot(frequency, L_RIQ, label='RIQ', linestyle='-.')
    plt.xlabel('Frequency')
    plt.ylabel('Inductance (L)')
    plt.title("L predicted from RI, LQ and RIQ models")
    plt.legend()
    
    # Subplot for Q comparison (bottom subplot)
    plt.subplot(2, 1, 2)  # 2 rows, 1 column, 2nd subplot
    plt.plot(frequency, Q_RI, label='RI', linestyle='-')
    plt.plot(frequency, Q_QL, label='QL', linestyle='--')
    plt.plot(frequency, Q_RIQ, label='RIQ', linestyle='-.')
    plt.xlabel('Frequency')
    plt.ylabel('Quality Factor (Q)')
    plt.title("Q predicted from RI, LQ and RIQ models")
    plt.legend()
    
    plt.tight_layout()
    plt.savefig("model_comparision.png", dpi=300)



        # Plotting L comparison
    plt.figure(figsize=(6, 3))
    plt.plot(frequency, L_RI, label='RI', linestyle='-')
    plt.plot(frequency, L_QL, label='QL', linestyle='--')
    plt.plot(frequency, L_RIQ, label='RIQ', linestyle='-.')
    plt.xlabel('Frequency')
    plt.ylabel('Inductance (H)')
    plt.title("L predicted from RI, LQ and RIQ models")
    plt.legend()
    plt.tight_layout()
    plt.savefig("model_comparision_L.png", dpi=300)
    
    # Plotting Q comparison
    plt.figure(figsize=(6, 3))
    plt.plot(frequency, Q_RI, label='RI', linestyle='-')
    plt.plot(frequency, Q_QL, label='QL', linestyle='--')
    plt.plot(frequency, Q_RIQ, label='RIQ', linestyle='-.')
    plt.ylim(-15, 30)
    plt.xlabel('Frequency')
    plt.ylabel('Quality Factor')
    plt.title("Q predicted from RI, LQ and RIQ models")
    plt.legend()
    plt.tight_layout()
    plt.savefig("model_comparision_Q.png", dpi=300)









def main():
    

    generate_RIQ_model_with_kfold(5)
    return
    generate_RIQ_model(tune=0)



    compare_RIQ_model(2000)

    return
    

    model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ"
    model_path = "model_library/" + model_name
    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    plot_model_learning_curves(model_path)

    return


    # Load the .s1p file
    network = rf.Network('iscas/iscas.s1p')

    # Extract S11 data
    s11 = network.s[:, 0, 0]
    frequency = network.f

    # Initialize the reshaped array with zeros
    s11reshaped = np.zeros((1, 2, len(s11)))
    print(np.shape(s11reshaped))
    # Fill in the real and imaginary parts
    s11reshaped[0, 0, :] = s11.real
    s11reshaped[0, 1, :] = s11.imag

    print("s11reshaped shape:", s11reshaped.shape)  # Expected: (2, 2, number_of_frequency_points)

    print(s11reshaped)


    


    [Q,L] = inductor.s_real_imag_to_q_and_l(s11reshaped, frequency, Z0=100)
    Q = Q.reshape(2000)
    L = L.reshape(2000)


    plt.figure(figsize=(12, 6))
    
    model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ"
    model_path = "model_library/" + model_name
    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')

    
    #new_feature_data = np.array([67.190,8.73, 3.135, 2])
    new_feature_data = np.array([77.190,19.260, 3.270, 2])
    denormalized_predictions = modelProcess.predict_from_model(model_name, model_path, new_feature_data, (sParameters.shape[0], 3, sParameters.shape[2]))

    S11_real_pred = denormalized_predictions[0][0]
    S11_imag_pred =denormalized_predictions[0][1]
    Q_pred =denormalized_predictions[0][2]

    [_,L_pred] = inductor.s_real_imag_to_q_and_l(denormalized_predictions, frequency, Z0=100)
    L_pred = L_pred.reshape(2000)




     # Subplot for L comparison
    plt.subplot(1, 2, 1)
    plt.plot(frequency, Q, label=' Q', color='blue')
    plt.plot(frequency, Q_pred, label=' Q', color='red')
    plt.xlabel('Frequency')
    plt.ylabel('Q')
    plt.title('Q from RIQ')
    plt.legend()
    
    # Subplot for Q comparison
    plt.subplot(1, 2, 2)
    plt.plot(frequency, L, label='Predicted Q', color='blue')
    plt.plot(frequency, L_pred, label='Predicted L', color='red')
    plt.xlabel('Frequency')
    plt.ylabel('L')
    plt.title('L from RIQ')
    plt.legend()

    plt.tight_layout()
    plt.savefig("iscas_riq.png")


    s11_real_emx = s11.real
    s11_imag_emx = s11.imag
    Q_emx = Q 
    L_emx = L


    


    print(np.shape( s11_real_emx))
    print(np.shape( s11_imag_emx))
    print(np.shape( Q_emx))
    print(np.shape( L_emx))
    print(np.shape( S11_real_pred))
    print(np.shape( S11_imag_pred))
    print(np.shape( Q_pred))
    print(np.shape( L_pred))

    # Stack arrays vertically
    data = np.vstack((s11_real_emx, s11_imag_emx, Q_emx, L_emx, S11_real_pred, S11_imag_pred, Q_pred, L_pred)).T

    # Save to CSV
    np.savetxt("iscas_data0.csv", data, delimiter=",", header="s11_real_emx,s11_imag_emx,Q_emx,L_emx,S11_real_pred,S11_imag_pred,Q_pred,L_pred", comments='')


    [RIQ_mae, RIQ_val_mae] = plot_model_learning_curves()
    print(RIQ_mae)
    print(RIQ_val_mae)





     # Subplot for L comparison
    plt.figure
    plt.plot(RIQ_mae, label=' MAE', color='red')
    plt.plot(RIQ_val_mae, label=' VAL MAE', color='blue')
    plt.xlabel('Frequency')
    plt.ylabel('Q')
    plt.title('Q from RIQ')
    plt.legend()
    plt.savefig("iscas_learningCurve.png")


    # Stack arrays vertically and transpose
    data = np.vstack((RIQ_mae, RIQ_val_mae)).T

    # Save to CSV
    np.savetxt("iscas_learningCurve.csv", data, delimiter=",", header="RIQ_mae,RIQ_val_mae", comments='')

    return







    dataId = 2000
    model_comparision(dataId)


    designParameters, sParameters, frequency = modelProcess.load_data('data/Inductor_Coplanar_1N_to_5N.npz')


    
    #generate_RI_model()
    #generate_QL_model()
    #generate_Q_model()
    #generate_RIQ_model()

    
    [Q_RI, L_RI] = compare_RI_model(dataId)
    [Q_QL, L_QL] = compare_QL_model(dataId)

    [Q_RIQ, L_RIQ] = compare_RIQ_model(dataId)

    model_name = "Inductor_Coplanar_1N_to_5N_model_RIQ"
    model_path = "model_library/" + model_name
    plot_model_learning_curves(model_path)



    #

    return 


    model_name = "Inductor_Coplanar_1N_to_5N_model_RI"
    model_path = "model_library/" + model_name
    plot_path = "plot/" + model_name
    modelProcess.plot_model_learning_curves(model_path, plot_path)

    model_name = "Inductor_Coplanar_1N_to_5N_model_LQ"
    model_path = "model_library/" + model_name
    plot_path = "plot/" + model_name
    modelProcess.plot_model_learning_curves(model_path, plot_path)

    return
    #generate_RI_model()
    #generate_QL_model()

    id = 0
    #debug_RI_model(id)

    compare_RI_model(id)
    #compare_QL_model(id)
   

    # sParam_RI = rfProcess.extract_s_parameters_real_imaginary(sParameters)
    # sParam_complex= rfProcess.extract_s_parameters_complex(sParameters)
    # sParam_mag_ang=rfProcess.extract_s_parameters_magnitude_angle(sParameters)
    # sParam_db_ang = rfProcess.extract_s_parameters_db_angle(sParameters)


    # print(np.shape(sParam_RI))
    # print(np.shape(sParam_complex))
    # print(np.shape(sParam_mag_ang))
    # print(np.shape(sParam_db_ang))





# Press Fn+F5 to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
