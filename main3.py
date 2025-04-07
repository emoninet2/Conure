import model.model2 as modelProcess
import numpy as np
import os
import random
import joblib
import json





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

    feature_train, feature_test, target_train, target_test = modelProcess.split_data(features, targets,  0.95 , 0.05,  random.randint(0, 1000))

    print(np.shape(feature_train))
    print(np.shape(feature_test))
    print(np.shape(target_train))
    print(np.shape(target_test))



    feature_train_norm, feature_test_norm, target_train_norm, target_test_norm, feature_scaler, target_scaler = modelProcess.normalize_data_sets(
        feature_train, feature_test, target_train, target_test, feature_method="minmax", target_method="minmax"
    )




    print(np.shape(feature_train_norm))
    print(np.shape(feature_test_norm))
    print(np.shape(target_train_norm))
    print(np.shape(target_test_norm))



    # Reshape target data for dense network
    target_train_norm_reshaped = target_train_norm.reshape(target_train.shape[0], -1)
    target_test_norm_reshaped = target_test_norm.reshape(target_test.shape[0], -1)



    # Define architecture
    architecture = [
        {"type": "Dense", "units": 2000, "activation": "relu", "input_shape": (feature_train.shape[1],)},
        {"type": "Dense", "units": 4000, "activation": "relu"},
        {"type": "Dense", "units": 8000, "activation": "relu"},
        {"type": "Dense", "units": target_train.shape[1], "activation": "linear"}
    ]

    # # Define architecture
    # architecture = [
    #     {"type": "Dense", "units": 1000, "activation": "relu", "input_shape": (feature_train.shape[1],)},
    #     {"type": "Dense", "units": 100, "activation": "relu"},
    #     {"type": "Dense", "units": 4000, "activation": "relu"},
    #     {"type": "Dense", "units": 100, "activation": "relu"},
    #     {"type": "Dense", "units": target_train.shape[1], "activation": "linear"}
    # ]

    # Define early stopping parameters
    early_stopping_config = {
        "monitor": "val_loss",  # Monitor validation loss
        "patience": 20,         # Stop if no improvement for 20 epochs
        "restore_best_weights": True
    }

    # Train model
    model, history = modelProcess.generate_model(
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
    metrics_dict = modelProcess.get_model_metrics(model_name, model_path, feature_test, target_test)
    #metrics_dict = modelProcess.get_model_metrics(model_name, model_path, feature_train, target_train)
    # Round to 4 decimal places

    return metrics_dict





def generate_RI_inverse_model(npz_file_path,model_name, train_portion= 0.8):
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
    
    features = s_parameters.reshape(s_parameters.shape[0], -1)
    targets =  geometric_parameters[:,:-1]
    
    # targets = s_parameters.reshape(s_parameters.shape[0], -1)
    # features = geometric_parameters[:,:-1] #this is to remove the fourth member "N" which is the number of rings and is redundant for now


    print(np.shape(features))
    print(np.shape(targets))
    #print(np.shape(targets_flattened))
    #print(features)

    
    #model_name = "transformer32"
    model_path = "model_library/" + model_name

    # Create the directory if it does not exist
    if not os.path.exists(model_path):
        os.makedirs(model_path)

    feature_train, feature_test, target_train, target_test = modelProcess.split_data(features, targets,  0.95 , 0.05,  random.randint(0, 1000))

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



    # Define architecture
    architecture = [
        {"type": "Dense", "units": 288, "activation": "relu", "input_shape": (feature_train.shape[1],)},
        {"type": "Dense", "units": 3584, "activation": "relu"},
        {"type": "Dense", "units": 3584, "activation": "relu"},
        {"type": "Dense", "units": target_train.shape[1], "activation": "linear"}
    ]

    # # Define architecture
    # architecture = [
    #     {"type": "Dense", "units": 1000, "activation": "relu", "input_shape": (feature_train.shape[1],)},
    #     {"type": "Dense", "units": 100, "activation": "relu"},
    #     {"type": "Dense", "units": 4000, "activation": "relu"},
    #     {"type": "Dense", "units": 100, "activation": "relu"},
    #     {"type": "Dense", "units": target_train.shape[1], "activation": "linear"}
    # ]

    # Define early stopping parameters
    early_stopping_config = {
        "monitor": "val_loss",  # Monitor validation loss
        "patience": 20,         # Stop if no improvement for 20 epochs
        "restore_best_weights": True
    }

    # Train model
    model, history = modelProcess.generate_model(
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
    metrics_dict = modelProcess.get_model_metrics(model_name, model_path, feature_test, target_test)
    #metrics_dict = modelProcess.get_model_metrics(model_name, model_path, feature_train, target_train)
    # Round to 4 decimal places

    return metrics_dict


metrics_dict = generate_RI_model('/mnt/storage/conure_data/tsmc65/transformers/transformer_3_3/s_parameters_data.npz',"Fmodel", train_portion= 0.8)
print(metrics_dict)

# metrics_dict = generate_RI_inverse_model('/mnt/storage/conure_data/tsmc65/transformers/transformer_3_3/s_parameters_data.npz',"Imodel", train_portion= 0.8)
# print(metrics_dict)