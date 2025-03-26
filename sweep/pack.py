import os
import json
import numpy as np
import skrf as rf
import glob


def pack(sweep_dir):

    data_dir = sweep_dir
    print(f"Data directory: {data_dir}")
    geometric_paremeters = []
    s_paremeters = []
    geometric_paremeters_names = None  # Initialize to store feature names
    s_parameter_names = None   # Initialize to store target (S-parameter) names
    frequency_points = None  # Initialize to store frequency points

    # Loop through each run folder
    for run_folder in os.listdir(data_dir):
        if run_folder.startswith('RunID'):
            run_id = run_folder
            
            # Load the parameters from parameters.json
            with open(os.path.join(data_dir, run_folder, 'parameters.json'), 'r') as param_file:
                params = json.load(param_file)
                params_values = list(params['parameters'].values())
                
                # Save feature names only once
                if geometric_paremeters_names is None:
                    geometric_paremeters_names = list(params['parameters'].keys())
                
                geometric_paremeters.append(params_values)
            
            # Find any touchstone file (e.g., .s2p, .s4p, .sNp) in the folder
            touchstone_files = glob.glob(os.path.join(data_dir, run_folder, f"*.s*p"))

            if touchstone_files:  # Check if there's at least one file found
                touchstone_path = touchstone_files[0]  # Take the first matching file
                print(f"Touchstone file found: {touchstone_path}")  # Print the path of the touchstone file
                network = rf.Network(touchstone_path)
                
                # Get the number of frequency points
                num_freqs = network.frequency.npoints
                num_ports = network.s.shape[1]  # Number of ports (shape: [freqs, ports, ports])
                
                # Save the frequency points only once
                if frequency_points is None:
                    frequency_points = network.f  # Frequency points in Hz
                
                # Save target names (S-parameter keys) only once
                if s_parameter_names is None:
                    s_parameter_names = []
                    for i in range(num_ports):
                        for j in range(num_ports):
                            s_parameter_names.append(f"S{i+1}{j+1}_real")
                            s_parameter_names.append(f"S{i+1}{j+1}_imag")

                # Prepare real and imaginary parts for all S-parameters at each frequency
                s_real_imag = []
                for i in range(num_ports):
                    for j in range(num_ports):
                        s_real_imag.append(network.s[:, i, j].real)  # Append real part
                        s_real_imag.append(network.s[:, i, j].imag)  # Append imaginary part

                # Stack the real and imaginary parts in alternating order
                s_real_imag = np.stack(s_real_imag, axis=0)  # Shape: [2*num_ports^2, num_freqs]

                # Append this run's target data, keeping the shape [2*num_ports^2, num_freqs]
                s_paremeters.append(s_real_imag)
            else:
                print(f"TOUCHSTONE FILE NOT FOUND for {run_id}")

    # Convert lists to arrays
    geometric_parameter_array = np.array(geometric_paremeters)
    s_parameter_array = np.array(s_paremeters)  # Shape: [num_runs, 2*num_ports^2, num_freqs]

    # Save the data in npz format, including feature names, target names, and frequency points
    np.savez(os.path.join(data_dir, 's_parameters_data.npz'), 
             geometric_parameters=geometric_parameter_array, 
             s_parameters=s_parameter_array, 
             geometric_paremeters_names=geometric_paremeters_names, 
             s_parameter_names=s_parameter_names,
             frequency_points=frequency_points)  # Store frequency points



def unpack_and_print(npz_file_path):
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


    targets_flattened = targets.reshape(nSamples,-1)

    print(np.shape(targets_flattened))

    print(feature_names)
    print(target_names)

    return
    
    # Print the first frequency point
    print(f"Frequency point: {frequency_points[4]:.6e} Hz")
    
    # Print the feature 
    print(f"Target : {feature_names} ")

    # Print the feature 
    print(f"Features : {features[:,:-1]} ")

    # Print the Target 
    print(f"Targets shape : {np.shape(targets)} ")


    print(f"Targets : {(targets[0])} ")

    # Loop through the target names and print corresponding values for the first run and first frequency point
    print("S-parameter values for the first frequency point:")
    for i, target_name in enumerate(target_names):
        print(f"{target_name}: {targets[0][i][4]}")


# Example usage:
#pack('/projects/bitstream/emon/conure_workspace/sessions/c8b07d3d-21c5-478e-b5e9-7df39b02041c/sweep/1727798547633')



#transformer_1_1  transformer_2_1  transformer_2_2  transformer_3_2  transformer_3_3  transformer_4_3  Transformer_Coplanar_1_1
# Example usage
filename = '/projects/bitstream/emon/conure_workspace/Transformers/transformer_4_3/'
pack(filename)
#unpack_and_print('/projects/bitstream/emon/conure_workspace/Transformers/transformer_1_1/s_parameters_data.npz')