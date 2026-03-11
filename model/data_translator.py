import json
import os
import numpy as np


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


# -------------------------------------------------------------
# Metadata helpers
# -------------------------------------------------------------
def _to_serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, tuple):
        return list(value)
    return value



def _normalize_names(names):
    if names is None:
        return []
    if isinstance(names, np.ndarray):
        return names.tolist()
    return list(names)



def _build_metadata(
    *,
    translation_type,
    features,
    targets,
    feature_names,
    target_names,
    freqs,
    X,
    y,
    original_input_shape_per_sample,
    original_output_shape_per_sample,
    grouped_input_shape_per_original_sample=None,
    grouped_output_shape_per_original_sample=None,
    input_semantics="features",
    output_semantics="targets",
    notes=None,
):
    metadata = {
        "translation_type": translation_type,
        "feature_names": _normalize_names(feature_names),
        "target_names": _normalize_names(target_names),
        "frequency_points": _to_serializable(freqs),
        "frequency_count": int(len(freqs)) if freqs is not None else None,
        "original_features_shape": list(features.shape),
        "original_targets_shape": list(targets.shape),
        "model_input_shape": list(X.shape),
        "model_output_shape": list(y.shape),
        "model_input_shape_per_sample": list(X.shape[1:]),
        "model_output_shape_per_sample": list(y.shape[1:]),
        "original_input_shape_per_sample": list(original_input_shape_per_sample),
        "original_output_shape_per_sample": list(original_output_shape_per_sample),
        "grouped_input_shape_per_original_sample": (
            list(grouped_input_shape_per_original_sample)
            if grouped_input_shape_per_original_sample is not None
            else None
        ),
        "grouped_output_shape_per_original_sample": (
            list(grouped_output_shape_per_original_sample)
            if grouped_output_shape_per_original_sample is not None
            else None
        ),
        "input_semantics": input_semantics,
        "output_semantics": output_semantics,
        "flatten_order": "C",
        "notes": notes or "",
    }
    return metadata



def save_metadata_json(metadata, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


# =============================================================
# ---------------- Forward Frequency-Independent -------------
# =============================================================
def prepare_ffi_data(npz_file_path, return_metadata=False):
    """
    Prepare data for a Forward Frequency-Independent (FFI) model.
    Features: geometry parameters
    Targets: flattened target tensor per sample
    Returns also raw frequency_points for reference.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")

    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        X = features
        y = targets.reshape(targets.shape[0], -1).astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        freqs = data["frequency_points"].astype(np.float32)

    if not return_metadata:
        return X, y, feature_names, target_names, freqs

    metadata = _build_metadata(
        translation_type="ffi",
        features=features,
        targets=targets,
        feature_names=feature_names,
        target_names=target_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=features.shape[1:],
        original_output_shape_per_sample=targets.shape[1:],
        grouped_input_shape_per_original_sample=features.shape[1:],
        grouped_output_shape_per_original_sample=targets.shape[1:],
        input_semantics="geometry_parameters",
        output_semantics="frequency_response_tensor",
        notes="Model input is already structured feature vector. Model output is flattened from the original target tensor.",
    )
    return X, y, feature_names, target_names, freqs, metadata


# ---------------------- Augmented ----------------------------
def prepare_ffi_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    """
    Prepare FFI data with data augmentation by adding noise.
    n_augment: how many noisy copies to generate.
    """
    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        freqs = data["frequency_points"].astype(np.float32)

    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list = [], []
    for _ in range(n_augment):
        X_noisy = add_noise(features, feature_noise_std, clip, f_min, f_max)
        y_noisy = add_noise(
            targets.reshape(targets.shape[0], -1),
            target_noise_std,
            clip,
            t_min.min(),
            t_max.max(),
        )
        X_list.append(X_noisy)
        y_list.append(y_noisy)

    X = np.vstack(X_list).astype(np.float32)
    y = np.vstack(y_list).astype(np.float32)

    if not return_metadata:
        return X, y, feature_names, target_names, freqs

    metadata = _build_metadata(
        translation_type="ffi_augmented",
        features=features,
        targets=targets,
        feature_names=feature_names,
        target_names=target_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=features.shape[1:],
        original_output_shape_per_sample=targets.shape[1:],
        grouped_input_shape_per_original_sample=features.shape[1:],
        grouped_output_shape_per_original_sample=targets.shape[1:],
        input_semantics="geometry_parameters",
        output_semantics="frequency_response_tensor",
        notes="Augmented FFI dataset. Model output is flattened from the original target tensor.",
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    return X, y, feature_names, target_names, freqs, metadata


# =============================================================
# ---------------- Forward Frequency-Dependent ----------------
# =============================================================
def prepare_ffd_data(npz_file_path, return_metadata=False):
    """
    Prepare data for a Forward Frequency-Dependent (FFD) model.
    Features: geometry parameters + frequency
    Targets: one target vector per frequency row
    Returns repeated frequency points.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")

    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        freqs = data["frequency_points"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()

    num_samples, _ = features.shape
    num_targets, num_freqs = targets.shape[1], targets.shape[2]

    X_features = np.repeat(features, num_freqs, axis=0)
    X_freqs = np.tile(freqs, num_samples).reshape(-1, 1)
    X = np.hstack([X_features, X_freqs]).astype(np.float32)
    y = targets.transpose(0, 2, 1).reshape(-1, num_targets).astype(np.float32)

    feature_names_with_freq = feature_names + ["frequency"]
    freqs_repeated = np.tile(freqs, num_samples)

    if not return_metadata:
        return X, y, feature_names_with_freq, target_names, freqs_repeated

    metadata = _build_metadata(
        translation_type="ffd",
        features=features,
        targets=targets,
        feature_names=feature_names_with_freq,
        target_names=target_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=(features.shape[1] + 1,),
        original_output_shape_per_sample=(targets.shape[1],),
        grouped_input_shape_per_original_sample=(num_freqs, features.shape[1] + 1),
        grouped_output_shape_per_original_sample=(num_freqs, targets.shape[1]),
        input_semantics="geometry_parameters_plus_frequency",
        output_semantics="frequency_row_targets",
        notes="Each original sample is expanded into one training row per frequency point.",
    )
    return X, y, feature_names_with_freq, target_names, freqs_repeated, metadata


# ---------------------- Augmented ----------------------------
def prepare_ffd_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    """
    Prepare FFD data with augmentation.
    Returns repeated frequency points.
    """
    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        freqs = data["frequency_points"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()

    num_samples, num_targets, num_freqs = targets.shape
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list, freq_list = [], [], []
    for _ in range(n_augment):
        X_features = add_noise(
            np.repeat(features, num_freqs, axis=0),
            feature_noise_std,
            clip,
            f_min,
            f_max,
        )
        X_freqs = np.tile(freqs, num_samples).reshape(-1, 1)
        X = np.hstack([X_features, X_freqs])
        y = add_noise(
            targets.transpose(0, 2, 1).reshape(-1, num_targets),
            target_noise_std,
            clip,
            t_min.min(),
            t_max.max(),
        )
        X_list.append(X)
        y_list.append(y)
        freq_list.append(np.tile(freqs, num_samples))

    X = np.vstack(X_list).astype(np.float32)
    y = np.vstack(y_list).astype(np.float32)
    freqs_augmented = np.concatenate(freq_list)

    feature_names_with_freq = feature_names + ["frequency"]

    if not return_metadata:
        return X, y, feature_names_with_freq, target_names, freqs_augmented

    metadata = _build_metadata(
        translation_type="ffd_augmented",
        features=features,
        targets=targets,
        feature_names=feature_names_with_freq,
        target_names=target_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=(features.shape[1] + 1,),
        original_output_shape_per_sample=(targets.shape[1],),
        grouped_input_shape_per_original_sample=(num_freqs, features.shape[1] + 1),
        grouped_output_shape_per_original_sample=(num_freqs, targets.shape[1]),
        input_semantics="geometry_parameters_plus_frequency",
        output_semantics="frequency_row_targets",
        notes="Augmented FFD dataset. Each original sample is expanded into one training row per frequency point.",
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    return X, y, feature_names_with_freq, target_names, freqs_augmented, metadata


# =============================================================
# ---------------- Inverse Frequency-Independent -------------
# =============================================================
def prepare_ifi_data(npz_file_path, return_metadata=False):
    """
    Prepare data for Inverse Frequency-Independent (IFI) model.
    Features: flattened targets
    Targets: geometry parameters
    Returns raw frequency points.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")

    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        freqs = data["frequency_points"].astype(np.float32)

    X = targets.reshape(targets.shape[0], -1).astype(np.float32)
    y = features.astype(np.float32)

    if not return_metadata:
        return X, y, feature_names, target_names, freqs

    metadata = _build_metadata(
        translation_type="ifi",
        features=features,
        targets=targets,
        feature_names=target_names,
        target_names=feature_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=targets.shape[1:],
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=targets.shape[1:],
        grouped_output_shape_per_original_sample=features.shape[1:],
        input_semantics="frequency_response_tensor",
        output_semantics="geometry_parameters",
        notes="Inverse model. Model input is flattened from the original target tensor.",
    )
    return X, y, target_names, feature_names, freqs, metadata


# ---------------------- Augmented ----------------------------
def prepare_ifi_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    """
    Prepare IFI data with augmentation.
    """
    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        freqs = data["frequency_points"].astype(np.float32)

    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list = [], []
    for _ in range(n_augment):
        X_noisy = add_noise(
            targets.reshape(targets.shape[0], -1),
            target_noise_std,
            clip,
            t_min.min(),
            t_max.max(),
        )
        y_noisy = add_noise(features, feature_noise_std, clip, f_min, f_max)
        X_list.append(X_noisy)
        y_list.append(y_noisy)

    X = np.vstack(X_list).astype(np.float32)
    y = np.vstack(y_list).astype(np.float32)

    if not return_metadata:
        return X, y, feature_names, target_names, freqs

    metadata = _build_metadata(
        translation_type="ifi_augmented",
        features=features,
        targets=targets,
        feature_names=target_names,
        target_names=feature_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=targets.shape[1:],
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=targets.shape[1:],
        grouped_output_shape_per_original_sample=features.shape[1:],
        input_semantics="frequency_response_tensor",
        output_semantics="geometry_parameters",
        notes="Augmented inverse model. Model input is flattened from the original target tensor.",
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    return X, y, target_names, feature_names, freqs, metadata


# =============================================================
# ---------------- Inverse Frequency-Dependent ---------------
# =============================================================
def prepare_ifd_data(npz_file_path, return_metadata=False):
    """
    Prepare data for Inverse Frequency-Dependent (IFD) model.
    Features: targets at each frequency + frequency
    Targets: geometry parameters repeated per frequency
    Returns repeated frequency points.
    """
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")

    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        freqs = data["frequency_points"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()

    num_samples, num_targets, num_freqs = targets.shape

    X_signal = targets.transpose(0, 2, 1).reshape(-1, num_targets)
    X_freq = np.tile(freqs, num_samples).reshape(-1, 1)
    X = np.hstack([X_signal, X_freq]).astype(np.float32)

    y = np.repeat(features, num_freqs, axis=0).astype(np.float32)
    freqs_repeated = np.tile(freqs, num_samples)

    input_feature_names = target_names + ["frequency"]

    if not return_metadata:
        return X, y, input_feature_names, feature_names, freqs_repeated

    metadata = _build_metadata(
        translation_type="ifd",
        features=features,
        targets=targets,
        feature_names=input_feature_names,
        target_names=feature_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=(targets.shape[1] + 1,),
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=(num_freqs, targets.shape[1] + 1),
        grouped_output_shape_per_original_sample=(num_freqs, features.shape[1]),
        input_semantics="frequency_row_targets_plus_frequency",
        output_semantics="geometry_parameters",
        notes="Inverse frequency-dependent model. Each original sample is expanded into one row per frequency point.",
    )
    return X, y, input_feature_names, feature_names, freqs_repeated, metadata


# ---------------------- Augmented ----------------------------
def prepare_ifd_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    """
    Prepare IFD data with augmentation.
    Features: targets at each frequency + frequency
    Targets: geometry parameters repeated per frequency
    """
    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        freqs = data["frequency_points"].astype(np.float32)

    num_samples, num_targets, num_freqs = targets.shape
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list, freq_list = [], [], []

    for _ in range(n_augment):
        X_signal_noisy = add_noise(
            targets.transpose(0, 2, 1).reshape(-1, num_targets),
            target_noise_std,
            clip,
            t_min.min(),
            t_max.max(),
        )

        X_freq = np.tile(freqs, num_samples).reshape(-1, 1)
        X = np.hstack([X_signal_noisy, X_freq])

        y_noisy = add_noise(
            np.repeat(features, num_freqs, axis=0),
            feature_noise_std,
            clip,
            f_min,
            f_max,
        )

        X_list.append(X)
        y_list.append(y_noisy)
        freq_list.append(np.tile(freqs, num_samples))

    X = np.vstack(X_list).astype(np.float32)
    y = np.vstack(y_list).astype(np.float32)
    freqs_augmented = np.concatenate(freq_list)

    input_feature_names = target_names + ["frequency"]

    if not return_metadata:
        return X, y, input_feature_names, feature_names, freqs_augmented

    metadata = _build_metadata(
        translation_type="ifd_augmented",
        features=features,
        targets=targets,
        feature_names=input_feature_names,
        target_names=feature_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=(targets.shape[1] + 1,),
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=(num_freqs, targets.shape[1] + 1),
        grouped_output_shape_per_original_sample=(num_freqs, features.shape[1]),
        input_semantics="frequency_row_targets_plus_frequency",
        output_semantics="geometry_parameters",
        notes="Augmented IFD dataset. Each original sample is expanded into one row per frequency point.",
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    return X, y, input_feature_names, feature_names, freqs_augmented, metadata


# =============================================================
# ---------------- Example Usage -----------------------------
# =============================================================
if __name__ == "__main__":
    file_path = "/mnt/storage/shared/jobs/01-sweep/output/TXCo11/simulation_data_fixed.npz"

    X_ffd, y_ffd, feat_names, targ_names, freqs_ffd, meta = prepare_ffd_augmented(
        file_path,
        feature_noise_std=0.01,
        target_noise_std=0.005,
        n_augment=3,
        return_metadata=True,
    )
    print("FFD Augmented X shape:", X_ffd.shape)
    print("FFD Augmented y shape:", y_ffd.shape)
    print("FFD Augmented frequency shape:", freqs_ffd.shape)
    print("Metadata keys:", sorted(meta.keys()))
