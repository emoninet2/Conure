import numpy as np
import os

# -------------------------------------------------------------
# Utility function to add Gaussian noise to data
# -------------------------------------------------------------
def add_noise(data, noise_std=0.0, clip=False, min_val=None, max_val=None):
    """
    Add Gaussian noise to data.

    Parameters:
    -----------
    data : np.ndarray
        Input array to which noise will be added.
    noise_std : float
        Standard deviation of noise relative to the data range.
    clip : bool
        Whether to clip noisy data to [min_val, max_val].
    min_val : float or np.ndarray
        Minimum value(s) for clipping.
    max_val : float or np.ndarray
        Maximum value(s) for clipping.

    Returns:
    --------
    np.ndarray
        Noisy data array.
    """
    if noise_std <= 0.0:
        return data.copy()
    
    rng = np.random.default_rng()
    scale = noise_std * (np.max(data, axis=0) - np.min(data, axis=0))
    noisy_data = data + rng.normal(0, scale, size=data.shape)
    
    if clip and min_val is not None and max_val is not None:
        noisy_data = np.clip(noisy_data, min_val, max_val)
    
    return noisy_data

# =============================================================
# ---------------- Forward Frequency-Independent -------------
# =============================================================
def prepare_ffi_data(npz_file_path):
    """
    Prepare data for a Forward Frequency-Independent (FFI) model.
    Features: 3 geometry params
    Targets: flattened 8x2000 array
    Returns also raw frequency_points for reference.

    Returns:
    --------
    X : np.ndarray (num_samples, 3)
    y : np.ndarray (num_samples, 16000)
    feature_names : list of str
    target_names : list of str
    freqs : np.ndarray (2000,)
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        X = data['features'].astype(np.float32)
        y = data['targets'].reshape(data['targets'].shape[0], -1).astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
        freqs = data['frequency_points'].astype(np.float32)
    
    return X, y, feature_names, target_names, freqs

# ---------------------- Augmented ----------------------------
def prepare_ffi_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    """
    Prepare FFI data with data augmentation by adding noise.
    n_augment: how many noisy copies to generate.
    """
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
        freqs = data['frequency_points'].astype(np.float32)
    
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
    return X, y, feature_names, target_names, freqs

# =============================================================
# ---------------- Forward Frequency-Dependent ----------------
# =============================================================
def prepare_ffd_data(npz_file_path):
    """
    Prepare data for a Forward Frequency-Dependent (FFD) model.
    Features: 3 geometry params + frequency
    Targets: 8 per frequency
    Returns repeated frequency points.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        freqs = data['frequency_points'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()

    num_samples, num_features = features.shape
    num_targets, num_freqs = targets.shape[1], targets.shape[2]

    X_features = np.repeat(features, num_freqs, axis=0)
    X_freqs = np.tile(freqs, num_samples).reshape(-1, 1)
    X = np.hstack([X_features, X_freqs])
    y = targets.transpose(0, 2, 1).reshape(-1, num_targets)

    feature_names_with_freq = feature_names + ['frequency']
    freqs_repeated = np.tile(freqs, num_samples)

    return X, y, feature_names_with_freq, target_names, freqs_repeated

# ---------------------- Augmented ----------------------------
def prepare_ffd_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    """
    Prepare FFD data with augmentation.
    Returns repeated frequency points.
    """
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        freqs = data['frequency_points'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()

    num_samples, num_targets, num_freqs = targets.shape
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0,2)), np.max(targets, axis=(0,2))

    X_list, y_list, freq_list = [], [], []
    for _ in range(n_augment):
        X_features = add_noise(np.repeat(features, num_freqs, axis=0), feature_noise_std, clip, f_min, f_max)
        X_freqs = np.tile(freqs, num_samples).reshape(-1,1)
        X = np.hstack([X_features, X_freqs])
        y = add_noise(targets.transpose(0,2,1).reshape(-1, num_targets), target_noise_std, clip, t_min.min(), t_max.max())
        X_list.append(X)
        y_list.append(y)
        freq_list.append(np.tile(freqs, num_samples))

    X = np.vstack(X_list)
    y = np.vstack(y_list)
    freqs_augmented = np.concatenate(freq_list)

    return X, y, feature_names + ['frequency'], target_names, freqs_augmented

# =============================================================
# ---------------- Inverse Frequency-Independent -------------
# =============================================================
def prepare_ifi_data(npz_file_path):
    """
    Prepare data for Inverse Frequency-Independent (IFI) model.
    Features: flattened targets
    Targets: geometry parameters
    Returns raw frequency points.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")
    
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
        freqs = data['frequency_points'].astype(np.float32)

    X = targets.reshape(targets.shape[0], -1)
    y = features
    return X, y, feature_names, target_names, freqs

# ---------------------- Augmented ----------------------------
def prepare_ifi_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    """
    Prepare IFI data with augmentation.
    """
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
        freqs = data['frequency_points'].astype(np.float32)

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
    return X, y, feature_names, target_names, freqs

# =============================================================
# ---------------- Inverse Frequency-Dependent ---------------
# =============================================================
def prepare_ifd_data(npz_file_path):
    """
    Prepare data for Inverse Frequency-Dependent (IFD) model.
    Features: targets at each frequency
    Targets: geometry parameters repeated per frequency
    Returns repeated frequency points.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")

    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        freqs = data['frequency_points'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()

    num_samples, num_targets, num_freqs = targets.shape
    X = targets.transpose(0, 2, 1).reshape(-1, num_targets)
    y = np.repeat(features, num_freqs, axis=0)
    freqs_repeated = np.tile(freqs, num_samples)

    return X, y, feature_names, target_names, freqs_repeated

# ---------------------- Augmented ----------------------------
def prepare_ifd_augmented(npz_file_path, feature_noise_std=0.0, target_noise_std=0.0, n_augment=1, clip=True):
    """
    Prepare IFD data with augmentation.
    """
    with np.load(npz_file_path) as data:
        features = data['features'].astype(np.float32)
        targets = data['targets'].astype(np.float32)
        feature_names = data['feature_names'].tolist()
        target_names = data['target_names'].tolist()
        freqs = data['frequency_points'].astype(np.float32)

    num_samples, num_targets, num_freqs = targets.shape
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0,2)), np.max(targets, axis=(0,2))

    X_list, y_list, freq_list = [], [], []
    for _ in range(n_augment):
        X_noisy = add_noise(targets.transpose(0,2,1).reshape(-1, num_targets), target_noise_std, clip, t_min.min(), t_max.max())
        y_noisy = add_noise(np.repeat(features, num_freqs, axis=0), feature_noise_std, clip, f_min, f_max)
        X_list.append(X_noisy)
        y_list.append(y_noisy)
        freq_list.append(np.tile(freqs, num_samples))

    X = np.vstack(X_list)
    y = np.vstack(y_list)
    freqs_augmented = np.concatenate(freq_list)

    return X, y, feature_names, target_names, freqs_augmented

# =============================================================
# ---------------- Example Usage -----------------------------
# =============================================================
if __name__ == "__main__":
    file_path = '/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz'

    # Generate 3 noisy variants for FFD
    X_ffd, y_ffd, feat_names, targ_names, freqs_ffd = prepare_ffd_augmented(
        file_path, feature_noise_std=0.01, target_noise_std=0.005, n_augment=3
    )
    print("FFD Augmented X shape:", X_ffd.shape)
    print("FFD Augmented y shape:", y_ffd.shape)
    print("FFD Augmented frequency shape:", freqs_ffd.shape)