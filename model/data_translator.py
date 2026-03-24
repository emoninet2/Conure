import json
import os
import re
import numpy as np


# -------------------------------------------------------------
# Utility function to add Gaussian noise to data
# -------------------------------------------------------------
def add_noise(data, noise_std=0.0, clip=False, min_val=None, max_val=None):
    """
    Add Gaussian noise to data.

    Parameters
    ----------
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

    Returns
    -------
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


# -------------------------------------------------------------
# NPZ loader
# -------------------------------------------------------------
def _load_npz_core(npz_file_path):
    if not os.path.exists(npz_file_path):
        raise FileNotFoundError(f"{npz_file_path} not found.")

    with np.load(npz_file_path) as data:
        features = data["features"].astype(np.float32)
        targets = data["targets"].astype(np.float32)
        feature_names = data["feature_names"].tolist()
        target_names = data["target_names"].tolist()
        freqs = data["frequency_points"].astype(np.float32)

    return features, targets, feature_names, target_names, freqs


# =============================================================
# ---------------- Base translators (raw targets) ------------
# =============================================================
def _prepare_forward_frequency_independent(
    features,
    targets,
    feature_names,
    target_names,
    freqs,
    *,
    translation_type,
    return_metadata=False,
    notes="",
    extra_metadata=None,
):
    X = features
    y = targets.reshape(targets.shape[0], -1).astype(np.float32)

    if not return_metadata:
        return X, y, feature_names, target_names, freqs

    metadata = _build_metadata(
        translation_type=translation_type,
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
        notes=notes,
    )
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, feature_names, target_names, freqs, metadata


def _prepare_forward_frequency_independent_augmented(
    features,
    targets,
    feature_names,
    target_names,
    freqs,
    *,
    translation_type,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
    notes="",
    extra_metadata=None,
):
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list = [], []
    flat_targets = targets.reshape(targets.shape[0], -1)

    for _ in range(n_augment):
        X_noisy = add_noise(features, feature_noise_std, clip, f_min, f_max)
        y_noisy = add_noise(
            flat_targets,
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
        translation_type=translation_type,
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
        notes=notes,
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, feature_names, target_names, freqs, metadata


def _prepare_forward_frequency_dependent(
    features,
    targets,
    feature_names,
    target_names,
    freqs,
    *,
    translation_type,
    return_metadata=False,
    notes="",
    output_semantics="frequency_row_targets",
    extra_metadata=None,
):
    num_samples = features.shape[0]
    num_targets = targets.shape[1]
    num_freqs = targets.shape[2]

    X_features = np.repeat(features, num_freqs, axis=0)
    X_freqs = np.tile(freqs, num_samples).reshape(-1, 1)
    X = np.hstack([X_features, X_freqs]).astype(np.float32)
    y = targets.transpose(0, 2, 1).reshape(-1, num_targets).astype(np.float32)

    feature_names_with_freq = feature_names + ["frequency"]
    freqs_repeated = np.tile(freqs, num_samples)

    if not return_metadata:
        return X, y, feature_names_with_freq, target_names, freqs_repeated

    metadata = _build_metadata(
        translation_type=translation_type,
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
        output_semantics=output_semantics,
        notes=notes,
    )
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, feature_names_with_freq, target_names, freqs_repeated, metadata


def _prepare_forward_frequency_dependent_augmented(
    features,
    targets,
    feature_names,
    target_names,
    freqs,
    *,
    translation_type,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
    notes="",
    output_semantics="frequency_row_targets",
    extra_metadata=None,
):
    num_samples = features.shape[0]
    num_targets = targets.shape[1]
    num_freqs = targets.shape[2]

    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list, freq_list = [], [], []

    row_targets = targets.transpose(0, 2, 1).reshape(-1, num_targets)

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
            row_targets,
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
        translation_type=translation_type,
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
        output_semantics=output_semantics,
        notes=notes,
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, feature_names_with_freq, target_names, freqs_augmented, metadata


def _prepare_inverse_frequency_independent(
    features,
    targets,
    input_names,
    output_names,
    freqs,
    *,
    translation_type,
    return_metadata=False,
    notes="",
    input_semantics="frequency_response_tensor",
    output_semantics="geometry_parameters",
    extra_metadata=None,
):
    X = targets.reshape(targets.shape[0], -1).astype(np.float32)
    y = features.astype(np.float32)

    if not return_metadata:
        return X, y, input_names, output_names, freqs

    metadata = _build_metadata(
        translation_type=translation_type,
        features=features,
        targets=targets,
        feature_names=input_names,
        target_names=output_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=targets.shape[1:],
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=targets.shape[1:],
        grouped_output_shape_per_original_sample=features.shape[1:],
        input_semantics=input_semantics,
        output_semantics=output_semantics,
        notes=notes,
    )
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, input_names, output_names, freqs, metadata


def _prepare_inverse_frequency_independent_augmented(
    features,
    targets,
    input_names,
    output_names,
    freqs,
    *,
    translation_type,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
    notes="",
    input_semantics="frequency_response_tensor",
    output_semantics="geometry_parameters",
    extra_metadata=None,
):
    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list = [], []
    flat_targets = targets.reshape(targets.shape[0], -1)

    for _ in range(n_augment):
        X_noisy = add_noise(
            flat_targets,
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
        return X, y, input_names, output_names, freqs

    metadata = _build_metadata(
        translation_type=translation_type,
        features=features,
        targets=targets,
        feature_names=input_names,
        target_names=output_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=targets.shape[1:],
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=targets.shape[1:],
        grouped_output_shape_per_original_sample=features.shape[1:],
        input_semantics=input_semantics,
        output_semantics=output_semantics,
        notes=notes,
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, input_names, output_names, freqs, metadata


def _prepare_inverse_frequency_dependent(
    features,
    targets,
    input_names,
    output_names,
    freqs,
    *,
    translation_type,
    return_metadata=False,
    notes="",
    input_semantics="frequency_row_targets_plus_frequency",
    output_semantics="geometry_parameters",
    extra_metadata=None,
):
    num_samples = features.shape[0]
    num_targets = targets.shape[1]
    num_freqs = targets.shape[2]

    X_signal = targets.transpose(0, 2, 1).reshape(-1, num_targets)
    X_freq = np.tile(freqs, num_samples).reshape(-1, 1)
    X = np.hstack([X_signal, X_freq]).astype(np.float32)

    y = np.repeat(features, num_freqs, axis=0).astype(np.float32)
    freqs_repeated = np.tile(freqs, num_samples)

    input_feature_names = input_names + ["frequency"]

    if not return_metadata:
        return X, y, input_feature_names, output_names, freqs_repeated

    metadata = _build_metadata(
        translation_type=translation_type,
        features=features,
        targets=targets,
        feature_names=input_feature_names,
        target_names=output_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=(targets.shape[1] + 1,),
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=(num_freqs, targets.shape[1] + 1),
        grouped_output_shape_per_original_sample=(num_freqs, features.shape[1]),
        input_semantics=input_semantics,
        output_semantics=output_semantics,
        notes=notes,
    )
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, input_feature_names, output_names, freqs_repeated, metadata


def _prepare_inverse_frequency_dependent_augmented(
    features,
    targets,
    input_names,
    output_names,
    freqs,
    *,
    translation_type,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
    notes="",
    input_semantics="frequency_row_targets_plus_frequency",
    output_semantics="geometry_parameters",
    extra_metadata=None,
):
    num_samples = features.shape[0]
    num_targets = targets.shape[1]
    num_freqs = targets.shape[2]

    f_min, f_max = np.min(features, axis=0), np.max(features, axis=0)
    t_min, t_max = np.min(targets, axis=(0, 2)), np.max(targets, axis=(0, 2))

    X_list, y_list, freq_list = [], [], []
    row_targets = targets.transpose(0, 2, 1).reshape(-1, num_targets)

    for _ in range(n_augment):
        X_signal_noisy = add_noise(
            row_targets,
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

    input_feature_names = input_names + ["frequency"]

    if not return_metadata:
        return X, y, input_feature_names, output_names, freqs_augmented

    metadata = _build_metadata(
        translation_type=translation_type,
        features=features,
        targets=targets,
        feature_names=input_feature_names,
        target_names=output_names,
        freqs=freqs,
        X=X,
        y=y,
        original_input_shape_per_sample=(targets.shape[1] + 1,),
        original_output_shape_per_sample=features.shape[1:],
        grouped_input_shape_per_original_sample=(num_freqs, targets.shape[1] + 1),
        grouped_output_shape_per_original_sample=(num_freqs, features.shape[1]),
        input_semantics=input_semantics,
        output_semantics=output_semantics,
        notes=notes,
    )
    metadata["augmentation"] = {
        "feature_noise_std": feature_noise_std,
        "target_noise_std": target_noise_std,
        "n_augment": n_augment,
        "clip": bool(clip),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return X, y, input_feature_names, output_names, freqs_augmented, metadata


# =============================================================
# ---------------- Standard translators ----------------------
# =============================================================
def prepare_ffi_data(npz_file_path, return_metadata=False):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_forward_frequency_independent(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffi",
        return_metadata=return_metadata,
        notes="Model input is already structured feature vector. Model output is flattened from the original target tensor.",
    )


def prepare_ffi_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_forward_frequency_independent_augmented(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffi_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented FFI dataset. Model output is flattened from the original target tensor.",
    )


def prepare_ffd_data(npz_file_path, return_metadata=False):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_forward_frequency_dependent(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffd",
        return_metadata=return_metadata,
        notes="Each original sample is expanded into one training row per frequency point.",
    )


def prepare_ffd_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_forward_frequency_dependent_augmented(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffd_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented FFD dataset. Each original sample is expanded into one training row per frequency point.",
    )


def prepare_ifi_data(npz_file_path, return_metadata=False):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_inverse_frequency_independent(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifi",
        return_metadata=return_metadata,
        notes="Inverse model. Model input is flattened from the original target tensor.",
    )


def prepare_ifi_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_inverse_frequency_independent_augmented(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifi_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented inverse model. Model input is flattened from the original target tensor.",
    )


def prepare_ifd_data(npz_file_path, return_metadata=False):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_inverse_frequency_dependent(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifd",
        return_metadata=return_metadata,
        notes="Inverse frequency-dependent model. Each original sample is expanded into one row per frequency point.",
    )


def prepare_ifd_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs = _load_npz_core(npz_file_path)
    return _prepare_inverse_frequency_dependent_augmented(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifd_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented IFD dataset. Each original sample is expanded into one row per frequency point.",
    )


# =============================================================
# ---------------- S-parameter -> L/Q helpers ----------------
# =============================================================
_REAL_PATTERNS = [
    r"^(?P<base>.+)_real$",
    r"^(?P<base>.+)_re$",
    r"^(?P<base>.+)_r$",
    r"^real\((?P<base>.+)\)$",
]

_IMAG_PATTERNS = [
    r"^(?P<base>.+)_imag$",
    r"^(?P<base>.+)_im$",
    r"^(?P<base>.+)_i$",
    r"^imag\((?P<base>.+)\)$",
]


def _detect_complex_target_pairs(target_names):
    """
    Detect pairs like:
      S11_real / S11_imag
      S11_re   / S11_im
      real(S11) / imag(S11)
      S11_r / S11_i
    """
    target_names = list(target_names)
    real_map = {}
    imag_map = {}

    for idx, name in enumerate(target_names):
        s = str(name).strip()

        for pat in _REAL_PATTERNS:
            m = re.match(pat, s, flags=re.IGNORECASE)
            if m:
                real_map[m.group("base")] = idx
                break

        for pat in _IMAG_PATTERNS:
            m = re.match(pat, s, flags=re.IGNORECASE)
            if m:
                imag_map[m.group("base")] = idx
                break

    pairs = [(base, real_map[base], imag_map[base]) for base in sorted(set(real_map) & set(imag_map))]

    if not pairs:
        raise ValueError(
            "Could not detect any real/imag pairs in target_names. "
            "Expected names like S11_real/S11_imag, S11_re/S11_im, real(S11)/imag(S11), etc."
        )

    return pairs


def _s_to_z(s_complex, z0=50.0):
    denom = 1.0 - s_complex
    eps = 1e-12
    denom = np.where(np.abs(denom) < eps, eps + 0j, denom)
    return z0 * (1.0 + s_complex) / denom


def _targets_sparams_to_lq(targets, target_names, freqs, z0=50.0):
    """
    targets shape = (N, C, F)
    output shape  = (N, 2*num_pairs, F)
    """
    targets = np.asarray(targets, dtype=np.float32)
    freqs = np.asarray(freqs, dtype=np.float32)

    if targets.ndim != 3:
        raise ValueError(f"targets must have shape (N, C, F). Got {targets.shape}")
    if freqs.ndim != 1:
        raise ValueError(f"freqs must be 1D. Got {freqs.shape}")
    if targets.shape[2] != len(freqs):
        raise ValueError(
            f"targets frequency dimension ({targets.shape[2]}) does not match len(freqs) ({len(freqs)})"
        )

    pairs = _detect_complex_target_pairs(target_names)
    omega = 2.0 * np.pi * freqs.reshape(1, -1)
    eps = 1e-12
    omega_safe = np.where(np.abs(omega) < eps, eps, omega)

    out_channels = []
    out_names = []
    pair_info = []

    for base, real_idx, imag_idx in pairs:
        s_real = targets[:, real_idx, :]
        s_imag = targets[:, imag_idx, :]
        s_complex = s_real.astype(np.float64) + 1j * s_imag.astype(np.float64)

        z_complex = _s_to_z(s_complex, z0=z0)
        z_real = np.real(z_complex)
        z_imag = np.imag(z_complex)

        L = (z_imag / omega_safe).astype(np.float32)
        z_real_safe = np.where(np.abs(z_real) < eps, eps, z_real)
        Q = (z_imag / z_real_safe).astype(np.float32)

        out_channels.append(L[:, np.newaxis, :])
        out_channels.append(Q[:, np.newaxis, :])

        out_names.append(f"L_{base}")
        out_names.append(f"Q_{base}")

        pair_info.append(
            {
                "source_base": base,
                "source_real_name": target_names[real_idx],
                "source_imag_name": target_names[imag_idx],
                "derived_names": [f"L_{base}", f"Q_{base}"],
            }
        )

    lq_targets = np.concatenate(out_channels, axis=1).astype(np.float32)
    return lq_targets, out_names, pair_info


def _load_inductor_npz(npz_file_path, z0=50.0):
    features, raw_targets, feature_names, raw_target_names, freqs = _load_npz_core(npz_file_path)

    lq_targets, lq_target_names, pair_info = _targets_sparams_to_lq(
        raw_targets, raw_target_names, freqs, z0=z0
    )

    extra_metadata = {
        "source_target_names": raw_target_names,
        "sparam_to_lq_pairs": pair_info,
        "z0": float(z0),
    }

    return features, lq_targets, feature_names, lq_target_names, freqs, extra_metadata


# =============================================================
# ---------------- Inductor translators ----------------------
# =============================================================
def prepare_ffi_inductor_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_independent(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffi_inductor",
        return_metadata=return_metadata,
        notes="Forward frequency-independent inductor model. Targets are derived from S-parameters via S->Z->(L,Q) and then flattened.",
        extra_metadata=extra,
    )


def prepare_ffi_inductor_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_independent_augmented(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffi_inductor_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented forward frequency-independent inductor model.",
        extra_metadata=extra,
    )


def prepare_ffd_inductor_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_dependent(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffd_inductor",
        return_metadata=return_metadata,
        notes="Forward frequency-dependent inductor model. S-parameters are converted to L/Q first, then expanded row-wise by frequency.",
        output_semantics="inductor_LQ_row",
        extra_metadata=extra,
    )


def prepare_ffd_inductor_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_dependent_augmented(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffd_inductor_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented forward frequency-dependent inductor model.",
        output_semantics="inductor_LQ_row",
        extra_metadata=extra,
    )


def prepare_ifi_inductor_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_independent(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifi_inductor",
        return_metadata=return_metadata,
        notes="Inverse frequency-independent inductor model. Input is flattened from the derived L/Q tensor.",
        input_semantics="inductor_LQ_tensor",
        extra_metadata=extra,
    )


def prepare_ifi_inductor_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_independent_augmented(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifi_inductor_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented inverse frequency-independent inductor model.",
        input_semantics="inductor_LQ_tensor",
        extra_metadata=extra,
    )


def prepare_ifd_inductor_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_dependent(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifd_inductor",
        return_metadata=return_metadata,
        notes="Inverse frequency-dependent inductor model. Derived L/Q is expanded row-wise by frequency.",
        input_semantics="inductor_LQ_row_plus_frequency",
        extra_metadata=extra,
    )


def prepare_ifd_inductor_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_inductor_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_dependent_augmented(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifd_inductor_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented inverse frequency-dependent inductor model.",
        input_semantics="inductor_LQ_row_plus_frequency",
        extra_metadata=extra,
    )


# =============================================================
# -------------- Transformer helpers: 2-port -> Lp/Ls/Qp/Qs/k
# =============================================================
_TWO_PORT_REAL_PATTERNS = [
    r"^(?P<base>[SZ]\d\d)_real$",
    r"^(?P<base>[SZ]\d\d)_re$",
    r"^(?P<base>[SZ]\d\d)_r$",
    r"^real\((?P<base>[SZ]\d\d)\)$",
]

_TWO_PORT_IMAG_PATTERNS = [
    r"^(?P<base>[SZ]\d\d)_imag$",
    r"^(?P<base>[SZ]\d\d)_im$",
    r"^(?P<base>[SZ]\d\d)_i$",
    r"^imag\((?P<base>[SZ]\d\d)\)$",
]


def _detect_complex_network_pairs(target_names):
    target_names = list(target_names)
    real_map = {}
    imag_map = {}

    for idx, name in enumerate(target_names):
        s = str(name).strip()

        for pat in _TWO_PORT_REAL_PATTERNS:
            m = re.match(pat, s, flags=re.IGNORECASE)
            if m:
                real_map[m.group("base").upper()] = idx
                break

        for pat in _TWO_PORT_IMAG_PATTERNS:
            m = re.match(pat, s, flags=re.IGNORECASE)
            if m:
                imag_map[m.group("base").upper()] = idx
                break

    return {
        base: (real_map[base], imag_map[base])
        for base in sorted(set(real_map) & set(imag_map))
    }


def _extract_complex_channel(targets, pair_map, base_name):
    real_idx, imag_idx = pair_map[base_name]
    real_part = targets[:, real_idx, :].astype(np.float64)
    imag_part = targets[:, imag_idx, :].astype(np.float64)
    return real_part + 1j * imag_part


def _twoport_s_to_z(s11, s12, s21, s22, z0=50.0):
    """
    Convert 2-port S-parameters to Z-parameters:
        Z = Z0 * (I + S) @ inv(I - S)
    """
    n_samples, n_freqs = s11.shape
    z11 = np.zeros((n_samples, n_freqs), dtype=np.complex128)
    z12 = np.zeros((n_samples, n_freqs), dtype=np.complex128)
    z21 = np.zeros((n_samples, n_freqs), dtype=np.complex128)
    z22 = np.zeros((n_samples, n_freqs), dtype=np.complex128)

    I = np.eye(2, dtype=np.complex128)
    eps = 1e-12

    for i in range(n_samples):
        for f in range(n_freqs):
            S = np.array(
                [
                    [s11[i, f], s12[i, f]],
                    [s21[i, f], s22[i, f]],
                ],
                dtype=np.complex128,
            )
            A = I - S
            if abs(np.linalg.det(A)) < eps:
                A = A + eps * I
            Z = z0 * (I + S) @ np.linalg.inv(A)

            z11[i, f] = Z[0, 0]
            z12[i, f] = Z[0, 1]
            z21[i, f] = Z[1, 0]
            z22[i, f] = Z[1, 1]

    return z11, z12, z21, z22


def _derive_transformer_metrics_from_z(z11, z12, z21, z22, freqs):
    """
    Outputs:
      Lp, Ls, Qp, Qs, k

    Definitions:
      Lp = imag(Z11) / (2*pi*f)
      Ls = imag(Z22) / (2*pi*f)
      Qp = imag(Z11) / real(Z11)
      Qs = imag(Z22) / real(Z22)
      k  = imag(Zm) / sqrt(imag(Z11) * imag(Z22))
      Zm = 0.5 * (Z12 + Z21)
    """
    freqs = np.asarray(freqs, dtype=np.float64)
    omega = 2.0 * np.pi * freqs.reshape(1, -1)

    eps = 1e-12
    omega_safe = np.where(np.abs(omega) < eps, eps, omega)

    z11_real = np.real(z11)
    z11_imag = np.imag(z11)

    z22_real = np.real(z22)
    z22_imag = np.imag(z22)

    zm = 0.5 * (z12 + z21)
    zm_imag = np.imag(zm)

    lp = z11_imag / omega_safe
    ls = z22_imag / omega_safe

    z11_real_safe = np.where(np.abs(z11_real) < eps, eps, z11_real)
    z22_real_safe = np.where(np.abs(z22_real) < eps, eps, z22_real)

    qp = z11_imag / z11_real_safe
    qs = z22_imag / z22_real_safe

    coupling_denom = np.sqrt(np.maximum(z11_imag * z22_imag, eps))
    k = zm_imag / coupling_denom

    transformer_targets = np.stack(
        [
            lp.astype(np.float32),
            ls.astype(np.float32),
            qp.astype(np.float32),
            qs.astype(np.float32),
            k.astype(np.float32),
        ],
        axis=1,
    )

    transformer_target_names = ["Lp", "Ls", "Qp", "Qs", "k"]
    return transformer_targets, transformer_target_names


def _targets_to_transformer_metrics(targets, target_names, freqs, z0=50.0):
    """
    Accept either:
      - Z11/Z12/Z21/Z22 channels directly
      - or S11/S12/S21/S22 channels, then convert S -> Z
    """
    targets = np.asarray(targets, dtype=np.float32)
    freqs = np.asarray(freqs, dtype=np.float32)

    if targets.ndim != 3:
        raise ValueError(f"targets must have shape (N, C, F). Got {targets.shape}")
    if freqs.ndim != 1:
        raise ValueError(f"freqs must be 1D. Got {freqs.shape}")
    if targets.shape[2] != len(freqs):
        raise ValueError(
            f"targets frequency dimension ({targets.shape[2]}) does not match len(freqs) ({len(freqs)})"
        )

    pair_map = _detect_complex_network_pairs(target_names)

    has_z = all(name in pair_map for name in ["Z11", "Z12", "Z21", "Z22"])
    has_s = all(name in pair_map for name in ["S11", "S12", "S21", "S22"])

    if has_z:
        z11 = _extract_complex_channel(targets, pair_map, "Z11")
        z12 = _extract_complex_channel(targets, pair_map, "Z12")
        z21 = _extract_complex_channel(targets, pair_map, "Z21")
        z22 = _extract_complex_channel(targets, pair_map, "Z22")

        transformer_targets, transformer_target_names = _derive_transformer_metrics_from_z(
            z11, z12, z21, z22, freqs
        )

        transform_info = {
            "source_type": "Z",
            "required_channels": {
                "Z11": [target_names[pair_map["Z11"][0]], target_names[pair_map["Z11"][1]]],
                "Z12": [target_names[pair_map["Z12"][0]], target_names[pair_map["Z12"][1]]],
                "Z21": [target_names[pair_map["Z21"][0]], target_names[pair_map["Z21"][1]]],
                "Z22": [target_names[pair_map["Z22"][0]], target_names[pair_map["Z22"][1]]],
            },
            "derived_names": transformer_target_names,
            "z0": float(z0),
        }
        return transformer_targets, transformer_target_names, transform_info

    if has_s:
        s11 = _extract_complex_channel(targets, pair_map, "S11")
        s12 = _extract_complex_channel(targets, pair_map, "S12")
        s21 = _extract_complex_channel(targets, pair_map, "S21")
        s22 = _extract_complex_channel(targets, pair_map, "S22")

        z11, z12, z21, z22 = _twoport_s_to_z(s11, s12, s21, s22, z0=z0)

        transformer_targets, transformer_target_names = _derive_transformer_metrics_from_z(
            z11, z12, z21, z22, freqs
        )

        transform_info = {
            "source_type": "S",
            "required_channels": {
                "S11": [target_names[pair_map["S11"][0]], target_names[pair_map["S11"][1]]],
                "S12": [target_names[pair_map["S12"][0]], target_names[pair_map["S12"][1]]],
                "S21": [target_names[pair_map["S21"][0]], target_names[pair_map["S21"][1]]],
                "S22": [target_names[pair_map["S22"][0]], target_names[pair_map["S22"][1]]],
            },
            "conversion": "2-port S->Z using Z = Z0 * (I + S) @ inv(I - S)",
            "derived_names": transformer_target_names,
            "z0": float(z0),
        }
        return transformer_targets, transformer_target_names, transform_info

    raise ValueError(
        "Transformer translation requires either:\n"
        "  Z11/Z12/Z21/Z22 real-imag channels\n"
        "or\n"
        "  S11/S12/S21/S22 real-imag channels.\n"
        "Examples: S11_real, S11_imag, ..., or Z11_real, Z11_imag, ..."
    )


def _load_transformer_npz(npz_file_path, z0=50.0):
    features, raw_targets, feature_names, raw_target_names, freqs = _load_npz_core(npz_file_path)

    transformer_targets, transformer_target_names, transform_info = _targets_to_transformer_metrics(
        raw_targets, raw_target_names, freqs, z0=z0
    )

    extra_metadata = {
        "source_target_names": raw_target_names,
        "transformer_derivation": transform_info,
    }

    return features, transformer_targets, feature_names, transformer_target_names, freqs, extra_metadata


# =============================================================
# ---------------- Transformer translators -------------------
# =============================================================
def prepare_ffi_transformer_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_independent(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffi_transformer",
        return_metadata=return_metadata,
        notes="Forward frequency-independent transformer model. Targets are derived as [Lp, Ls, Qp, Qs, k] and then flattened.",
        extra_metadata=extra,
    )


def prepare_ffi_transformer_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_independent_augmented(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffi_transformer_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented forward frequency-independent transformer model.",
        extra_metadata=extra,
    )


def prepare_ffd_transformer_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_dependent(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffd_transformer",
        return_metadata=return_metadata,
        notes="Forward frequency-dependent transformer model. Outputs one row per frequency point with [Lp, Ls, Qp, Qs, k].",
        output_semantics="transformer_metrics_row",
        extra_metadata=extra,
    )


def prepare_ffd_transformer_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_forward_frequency_dependent_augmented(
        features,
        targets,
        feature_names,
        target_names,
        freqs,
        translation_type="ffd_transformer_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented forward frequency-dependent transformer model.",
        output_semantics="transformer_metrics_row",
        extra_metadata=extra,
    )


def prepare_ifi_transformer_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_independent(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifi_transformer",
        return_metadata=return_metadata,
        notes="Inverse frequency-independent transformer model. Input is flattened from the [Lp, Ls, Qp, Qs, k] tensor.",
        input_semantics="transformer_metrics_tensor",
        extra_metadata=extra,
    )


def prepare_ifi_transformer_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_independent_augmented(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifi_transformer_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented inverse frequency-independent transformer model.",
        input_semantics="transformer_metrics_tensor",
        extra_metadata=extra,
    )


def prepare_ifd_transformer_data(npz_file_path, z0=50.0, return_metadata=False):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_dependent(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifd_transformer",
        return_metadata=return_metadata,
        notes="Inverse frequency-dependent transformer model. Derived [Lp, Ls, Qp, Qs, k] is expanded row-wise by frequency.",
        input_semantics="transformer_metrics_row_plus_frequency",
        extra_metadata=extra,
    )


def prepare_ifd_transformer_augmented(
    npz_file_path,
    feature_noise_std=0.0,
    target_noise_std=0.0,
    n_augment=1,
    clip=True,
    z0=50.0,
    return_metadata=False,
):
    features, targets, feature_names, target_names, freqs, extra = _load_transformer_npz(npz_file_path, z0=z0)
    return _prepare_inverse_frequency_dependent_augmented(
        features,
        targets,
        target_names,
        feature_names,
        freqs,
        translation_type="ifd_transformer_augmented",
        feature_noise_std=feature_noise_std,
        target_noise_std=target_noise_std,
        n_augment=n_augment,
        clip=clip,
        return_metadata=return_metadata,
        notes="Augmented inverse frequency-dependent transformer model.",
        input_semantics="transformer_metrics_row_plus_frequency",
        extra_metadata=extra,
    )


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

    # Example for inductor translators:
    # X_i, y_i, feat_i, targ_i, freqs_i, meta_i = prepare_ffd_inductor_data(
    #     file_path,
    #     z0=50.0,
    #     return_metadata=True,
    # )
    # print("FFD_Inductor X shape:", X_i.shape)
    # print("FFD_Inductor y shape:", y_i.shape)
    # print("FFD_Inductor freq shape:", freqs_i.shape)
    # print("Inductor target names:", targ_i)

    # Example for transformer translators:
    # X_t, y_t, feat_t, targ_t, freqs_t, meta_t = prepare_ffd_transformer_data(
    #     file_path,
    #     z0=50.0,
    #     return_metadata=True,
    # )
    # print("FFD_Transformer X shape:", X_t.shape)
    # print("FFD_Transformer y shape:", y_t.shape)
    # print("FFD_Transformer freq shape:", freqs_t.shape)
    # print("Transformer target names:", targ_t)