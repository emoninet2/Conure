import numpy as np
import os


# ---------------------- FFI  -------------------------
def prepare_ffi_data(npz_file_path):
    """
    Load data from an NPZ file and prepare it for training a forward frequency-independent model (FFI).
    
    Parameters:
    -----------
    npz_file_path : str
        Path to the .npz file containing 'features' and 'targets'.
        
    Returns:
    --------
    X : np.ndarray
        Feature array of shape (num_samples, num_features)
    y : np.ndarray
        Flattened target array of shape (num_samples, num_targets_flat)
    feature_names : list of str
        Names of features
    target_names : list of str
        Names of targets (repeated for each frequency if needed)
    """
    
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        # Extract features and targets
        X = data['features'].astype(np.float32)  # (260, 3)
        y = data['targets']  # (260, 8, 2000)
        
        # Flatten the 8x2000 targets to 1D per sample
        y = y.reshape(y.shape[0], -1).astype(np.float32)  # (260, 16000)
        
        # Optional: extract feature and target names
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
        
    return X, y, feature_names, target_names



# ---------------------- FFD  -------------------------
def prepare_ffd_data(npz_file_path):
    """
    Prepare data for a forward frequency-dependent (FFD) model.
    
    Parameters:
    -----------
    npz_file_path : str
        Path to the .npz file containing 'features', 'targets', and 'frequency_points'.
        
    Returns:
    --------
    X : np.ndarray
        Feature array including frequency, shape (num_samples*num_freq_points, 4)
    y : np.ndarray
        Target array at each frequency, shape (num_samples*num_freq_points, 8)
    feature_names : list of str
        Names of features + 'frequency'
    target_names : list of str
        Names of the 8 targets
    """
    
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)       # (260, 3)
        targets = data['targets'].astype(np.float32)        # (260, 8, 2000)
        freqs = data['frequency_points'].astype(np.float32) # (2000,)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    num_samples, num_features = features.shape
    num_targets, num_freqs = targets.shape[1], targets.shape[2]
    
    # Repeat features for each frequency point
    X_features = np.repeat(features, num_freqs, axis=0)  # (260*2000, 3)
    
    # Repeat frequency points for each sample
    X_freqs = np.tile(freqs, num_samples).reshape(-1, 1) # (260*2000, 1)
    
    # Concatenate features + frequency
    X = np.hstack([X_features, X_freqs])                 # (260*2000, 4)
    
    # Flatten targets along frequency dimension
    y = targets.transpose(0, 2, 1).reshape(-1, num_targets) # (260*2000, 8)
    
    # Add 'frequency' to feature names
    feature_names_with_freq = feature_names + ['frequency']
    
    return X, y, feature_names_with_freq, target_names



# ---------------------- IFI  -------------------------
def prepare_ifi_data(npz_file_path):
    """
    Prepare data for an inverse frequency-independent (IFI) model.
    
    Parameters:
    -----------
    npz_file_path : str
        Path to the .npz file containing 'features' and 'targets'.
        
    Returns:
    --------
    X : np.ndarray
        Flattened targets as inputs, shape (num_samples, 8*2000)
    y : np.ndarray
        Features as outputs, shape (num_samples, 3)
    feature_names : list of str
        Names of features
    target_names : list of str
        Names of the 8 targets repeated for all frequencies
    """
    
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)      # (260, 3)
        targets = data['targets'].astype(np.float32)        # (260, 8, 2000)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    # Flatten targets
    X = targets.reshape(targets.shape[0], -1)             # (260, 16000)
    y = features                                         # (260, 3)
    
    return X, y, feature_names, target_names




# ---------------------- FFD  -------------------------
def prepare_ifd_data(npz_file_path):
    """
    Prepare data for an inverse frequency-dependent (IFD) model.
    
    Parameters:
    -----------
    npz_file_path : str
        Path to the .npz file containing 'features' and 'targets'.
        
    Returns:
    --------
    X : np.ndarray
        Target values at each frequency, shape (num_samples*num_freq_points, 8)
    y : np.ndarray
        Features as outputs, repeated for each frequency, shape (num_samples*num_freq_points, 3)
    feature_names : list of str
        Names of the features
    target_names : list of str
        Names of the 8 targets
    """
    
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)  # (260, 3)
        targets = data['targets'].astype(np.float32)    # (260, 8, 2000)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    num_samples, num_targets, num_freqs = targets.shape
    
    # Flatten along frequency dimension
    X = targets.transpose(0, 2, 1).reshape(-1, num_targets)  # (260*2000, 8)
    
    # Repeat features for each frequency
    y = np.repeat(features, num_freqs, axis=0)               # (260*2000, 3)
    
    return X, y, feature_names, target_names


def add_noise(data, noise_std=0.0, clip=False, min_val=None, max_val=None):
    """
    Add Gaussian noise to data.
    """
    if noise_std <= 0.0:
        return data.copy()
    
    rng = np.random.default_rng()
    scale = noise_std * (np.max(data, axis=0) - np.min(data, axis=0))
    noisy_data = data + rng.normal(0, scale, size=data.shape)
    
    if clip and min_val is not None and max_val is not None:
        noisy_data = np.clip(noisy_data, min_val, max_val)
    
    return noisy_data

# ---------------------- FFI Augmented ----------------------
def prepare_ffi_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0,2)), np.max(targets, axis=(0,2))
    
    X_list, y_list = [], []
    for _ in range(n_augment):
        X_noisy = add_noise(features, feature_noise_std, clip, f_min, f_max)
        y_noisy = add_noise(targets.reshape(targets.shape[0], -1), target_noise_std, clip, t_min.min(), t_max.max())
        X_list.append(X_noisy)
        y_list.append(y_noisy)
    
    X = np.vstack(X_list)
    y = np.vstack(y_list)
    return X, y, feature_names, target_names

# ---------------------- FFD Augmented ----------------------
def prepare_ffd_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        freqs = data['frequency_points'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    num_samples, num_targets, num_freqs = targets.shape
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0,2)), np.max(targets, axis=(0,2))
    
    X_list, y_list = [], []
    for _ in range(n_augment):
        X_features = add_noise(np.repeat(features, num_freqs, axis=0), feature_noise_std, clip, f_min, f_max)
        X_freqs = np.tile(freqs, num_samples).reshape(-1,1)
        X = np.hstack([X_features, X_freqs])
        y = add_noise(targets.transpose(0,2,1).reshape(-1, num_targets), target_noise_std, clip, t_min.min(), t_max.max())
        X_list.append(X)
        y_list.append(y)
    
    X = np.vstack(X_list)
    y = np.vstack(y_list)
    return X, y, feature_names + ['frequency'], target_names

# ---------------------- IFI Augmented ----------------------
def prepare_ifi_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0,2)), np.max(targets, axis=(0,2))
    
    X_list, y_list = [], []
    for _ in range(n_augment):
        X_noisy = add_noise(targets.reshape(targets.shape[0], -1), target_noise_std, clip, t_min.min(), t_max.max())
        y_noisy = add_noise(features, feature_noise_std, clip, f_min, f_max)
        X_list.append(X_noisy)
        y_list.append(y_noisy)
    
    X = np.vstack(X_list)
    y = np.vstack(y_list)
    return X, y, feature_names, target_names

# ---------------------- IFD Augmented ----------------------
def prepare_ifd_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
    
    num_samples, num_targets, num_freqs = targets.shape
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0,2)), np.max(targets, axis=(0,2))
    
    X_list, y_list = [], []
    for _ in range(n_augment):
        X_noisy = add_noise(targets.transpose(0,2,1).reshape(-1, num_targets), target_noise_std, clip, t_min.min(), t_max.max())
        y_noisy = add_noise(np.repeat(features, num_freqs, axis=0), feature_noise_std, clip, f_min, f_max)
        X_list.append(X_noisy)
        y_list.append(y_noisy)
    
    X = np.vstack(X_list)
    y = np.vstack(y_list)
    return X, y, feature_names, target_names





# ---------------------- Example Usage ----------------------
file_path = '/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz'

# Generate 3 noisy variants for FFD
X_ffd, y_ffd, feat_names, targ_names = prepare_ffd_augmented(
    file_path, feature_noise_std=0.01, target_noise_std=0.005, n_augment=3
)
print("FFD Augmented X shape:", X_ffd.shape)
print("FFD Augmented y shape:", y_ffd.shape)