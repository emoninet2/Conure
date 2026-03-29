import os
import json

# Define the base directory where your folders are located
# Use '.' if the script is in the same directory as the RunID folders
base_path = 'data/workspace/IND1/sweep/Inductor_Coplanar_1'

# Loop through all items in the directory
for folder_name in os.listdir(base_path):
    # Check if the folder follows the RunID_xxxx naming convention
    if folder_name.startswith("RunID_") and os.path.isdir(os.path.join(base_path, folder_name)):
        
        # Extract the ID from the folder name (e.g., '0000')
        run_id_val = folder_name.split('_')[1]
        file_path = os.path.join(base_path, folder_name, 'parameters.json')
        
        # Only proceed if the file actually exists
        if os.path.exists(file_path):
            # 1. Read the existing data
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # 2. Update the runID
            data['runID'] = run_id_val
            
            # 3. Remove 'rings' from the parameters sub-dictionary
            if 'rings' in data.get('parameters', {}):
                del data['parameters']['rings']
            
            # 4. Write the updated data back to the file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)

print(f"Successfully processed iterations.")




# from model import predict

# model_type = "ann"
# model_dir = "data/workspace/IND2/model/ANN_FFI"

# X_new = [[100, 8, 2]]


# Y_new = predict.predict_model(model_type, model_dir, X_new)

# print(Y_new)