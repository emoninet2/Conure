import numpy as np
#import rf.rf as rfProcess



from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import r2_score,mean_absolute_error, mean_squared_error
from keras.models import Sequential, load_model
from keras.layers import Dense, Flatten
from keras.optimizers import Adam
from tensorflow import keras
from kerastuner import tuners as kt
from keras.callbacks import EarlyStopping

import os
import joblib
import json
import matplotlib.pyplot as plt



def preProcess_data(npz_file_path):
    pass
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
    targets_flattened = targets.reshape(nSamples,-1)

    print(np.shape(targets_flattened))
    print(features)




preProcess_data('/projects/bitstream/emon/conure_workspace/sessions/88c8c56c-34cf-4450-915d-bea55499964e/sweep/1727866838645/s_parameters_data.npz')
