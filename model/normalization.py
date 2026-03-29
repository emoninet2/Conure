"""
Shared feature/target scaling for model trainers (ANN, tree models, GPR, PCE, etc.).

Supports:
- Legacy single ``feature_method`` / ``target_method`` for all columns.
- Per-name maps: ``feature_methods`` / ``target_methods`` (``dict`` name -> method), aligned with
  ``feature_column_names`` / ``target_column_names`` (one logical name per *flat* column), set by
  ``train.py`` from translation selection.

Persists the same on-disk artifacts: ``feature_scaler.pkl`` / ``target_scaler.pkl`` (joblib).
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.preprocessing import (
    MaxAbsScaler,
    MinMaxScaler,
    RobustScaler,
    StandardScaler,
)

SCALER_CLASSES = {
    "standard": StandardScaler,
    "minmax": MinMaxScaler,
    "robust": RobustScaler,
    "maxabs": MaxAbsScaler,
    "none": None,
}


def expand_column_names_from_rle(rle: Optional[Sequence[Sequence[Any]]]) -> List[str]:
    """
    Rebuild a flat per-column name list from run-length pairs ``[[name, count], ...]``.

    Used when reading ``report.json`` artifact metadata where expanded
    ``feature_column_names`` / ``target_column_names`` are stored compactly as
    ``feature_column_names_rle`` / ``target_column_names_rle``.
    """
    if not rle:
        return []
    out: List[str] = []
    for pair in rle:
        if not pair or len(pair) < 2:
            continue
        name, count = str(pair[0]), int(pair[1])
        if count <= 0:
            continue
        out.extend([name] * count)
    return out


class PerColumnScaler:
    """
    Independent scaler per column (for mixed normalization types on one matrix).
    sklearn-like ``transform`` / ``inverse_transform``; ``n_features_in_`` for validation.
    """

    def __init__(self, methods: Sequence[str]):
        self.methods = [str(m).strip().lower() for m in methods]
        self.scalers_: List[Optional[Any]] = [None] * len(self.methods)
        self.n_features_in_: int = len(self.methods)

    def fit(self, X: np.ndarray) -> "PerColumnScaler":
        X = np.asarray(X)
        if X.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {X.shape}")
        n = X.shape[1]
        if n != len(self.methods):
            raise ValueError(
                f"PerColumnScaler: n_features_in ({n}) != len(methods) ({len(self.methods)})"
            )
        self.scalers_ = []
        for j, m in enumerate(self.methods):
            if m == "none" or SCALER_CLASSES.get(m) is None:
                self.scalers_.append(None)
            else:
                cls = SCALER_CLASSES[m]
                s = cls()
                s.fit(X[:, j : j + 1])
                self.scalers_.append(s)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X)
        cols = []
        for j, s in enumerate(self.scalers_):
            col = X[:, j : j + 1]
            if s is None:
                cols.append(col)
            else:
                cols.append(s.transform(col))
        return np.hstack(cols)

    def inverse_transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X)
        cols = []
        for j, s in enumerate(self.scalers_):
            col = X[:, j : j + 1]
            if s is None:
                cols.append(col)
            else:
                cols.append(s.inverse_transform(col))
        return np.hstack(cols)

    def propagate_std_from_norm(self, y_std_norm: np.ndarray) -> np.ndarray:
        """
        Map prediction std (in normalized target space) to original target space.
        Used by GPR when ``return_std=True``. Linear for standard/robust; delta trick otherwise.

        With *mixed* target scalers this is approximate (not a full uncertainty transform for
        arbitrary monotonic inverse maps).
        """
        y_std_norm = np.asarray(y_std_norm)
        if y_std_norm.ndim == 1:
            y_std_norm = y_std_norm.reshape(-1, 1)
        n_samples, n = y_std_norm.shape
        if n != len(self.scalers_):
            raise ValueError("propagate_std_from_norm: width mismatch")
        out = np.zeros_like(y_std_norm, dtype=np.float64)
        for j, s in enumerate(self.scalers_):
            sn = y_std_norm[:, j : j + 1]
            if s is None:
                out[:, j] = sn.ravel()
            elif hasattr(s, "scale_") and getattr(s, "scale_", None) is not None:
                out[:, j] = (sn * float(s.scale_[0])).ravel()
            else:
                z = np.zeros((n_samples, 1))
                out[:, j] = (s.inverse_transform(z + sn) - s.inverse_transform(z)).ravel()
        return out


def get_normalization_config(
    config: Dict[str, Any],
    *,
    feature_default: str = "standard",
    target_default: str = "standard",
) -> Tuple[str, str]:
    """
    Read ``config['normalization']`` with per-model defaults when keys are omitted.

    Tree ensembles (CAT, RF, XGB, LGBM) typically pass ``feature_default=target_default='none'``.
    """
    normalization_cfg = config.get("normalization") or {}
    if not isinstance(normalization_cfg, dict):
        normalization_cfg = {}
    feature_method = normalization_cfg.get("feature_method", feature_default)
    target_method = normalization_cfg.get("target_method", target_default)
    return str(feature_method).strip(), str(target_method).strip()


def _as_methods_map(raw: Any) -> Dict[str, str]:
    if not raw or not isinstance(raw, dict):
        return {}
    return {str(k): str(v).strip().lower() for k, v in raw.items()}


def _resolve_axis_methods(
    column_names: Optional[Sequence[str]],
    n_cols: int,
    methods_map: Dict[str, str],
    legacy_method: str,
) -> List[str]:
    lm = str(legacy_method).strip().lower()
    if column_names is not None and len(column_names) == n_cols:
        return [str(methods_map.get(str(name), lm)).strip().lower() for name in column_names]
    return [lm] * n_cols


def normalization_usage_flags(
    config: Dict[str, Any],
    *,
    n_features: int,
    n_targets: int,
    feature_default: str = "standard",
    target_default: str = "standard",
) -> Tuple[bool, bool]:
    """Whether feature / target axes use any non-``none`` scaling (including per-name maps)."""
    norm = config.get("normalization") or {}
    if not isinstance(norm, dict):
        norm = {}
    fm, tm = get_normalization_config(
        config, feature_default=feature_default, target_default=target_default
    )
    f_map = _as_methods_map(norm.get("feature_methods"))
    t_map = _as_methods_map(norm.get("target_methods"))
    f_cols = norm.get("feature_column_names")
    t_cols = norm.get("target_column_names")

    def axis_any(
        names: Optional[Sequence[str]],
        n: int,
        default_m: str,
        mmap: Dict[str, str],
    ) -> bool:
        methods = _resolve_axis_methods(names, n, mmap, default_m)
        return any(m != "none" for m in methods)

    return (
        axis_any(f_cols if isinstance(f_cols, list) else None, n_features, fm, f_map),
        axis_any(t_cols if isinstance(t_cols, list) else None, n_targets, tm, t_map),
    )


def _maybe_cast(arr: np.ndarray, scaled_dtype: Optional[Any]) -> np.ndarray:
    if scaled_dtype is None:
        return arr
    return np.asarray(arr, dtype=scaled_dtype)


def _scale_axis_single_method(
    train: np.ndarray,
    test: np.ndarray,
    method: str,
    none_dtype: Any,
    scaled_dtype: Optional[Any],
) -> Tuple[np.ndarray, np.ndarray, Optional[Any]]:
    method = str(method).strip().lower()
    if method not in SCALER_CLASSES:
        raise ValueError(f"Unsupported normalization method: {method}")
    if SCALER_CLASSES[method] is None:
        return (
            np.asarray(train, dtype=none_dtype),
            np.asarray(test, dtype=none_dtype),
            None,
        )
    scaler = SCALER_CLASSES[method]()
    tr = _maybe_cast(scaler.fit_transform(train), scaled_dtype)
    te = _maybe_cast(scaler.transform(test), scaled_dtype)
    return tr, te, scaler


def _scale_axis_per_column(
    train: np.ndarray,
    test: np.ndarray,
    methods: List[str],
    none_dtype: Any,
    scaled_dtype: Optional[Any],
) -> Tuple[np.ndarray, np.ndarray, Optional[Any]]:
    if all(m == "none" for m in methods):
        return (
            np.asarray(train, dtype=none_dtype),
            np.asarray(test, dtype=none_dtype),
            None,
        )
    if len(set(methods)) == 1:
        return _scale_axis_single_method(train, test, methods[0], none_dtype, scaled_dtype)

    pc = PerColumnScaler(methods)
    pc.fit(train)
    tr = _maybe_cast(pc.transform(train), scaled_dtype)
    te = _maybe_cast(pc.transform(test), scaled_dtype)
    return tr, te, pc


def normalize_train_test_split(
    config: Dict[str, Any],
    f_train,
    f_test,
    t_train,
    t_test,
    *,
    feature_default: str = "standard",
    target_default: str = "standard",
    none_dtype=np.float64,
    scaled_dtype=None,
):
    """
    Normalize train/test splits using ``config['normalization']`` (legacy + per-name maps).

    ``train.py`` should set ``feature_column_names`` / ``target_column_names`` on
    ``config['normalization']`` to lists aligned with flat matrix columns.
    """
    norm = config.get("normalization") or {}
    if not isinstance(norm, dict):
        norm = {}

    fm, tm = get_normalization_config(
        config, feature_default=feature_default, target_default=target_default
    )
    f_map = _as_methods_map(norm.get("feature_methods"))
    t_map = _as_methods_map(norm.get("target_methods"))
    f_cols = norm.get("feature_column_names")
    t_cols = norm.get("target_column_names")
    if f_cols is not None and not isinstance(f_cols, list):
        f_cols = None
    if t_cols is not None and not isinstance(t_cols, list):
        t_cols = None

    nf = int(np.asarray(f_train).shape[1])
    nt = int(np.asarray(t_train).shape[1])

    if f_map and (f_cols is None or len(f_cols) != nf):
        warnings.warn(
            "normalization.feature_methods is set but feature_column_names is missing or does not match "
            f"the number of feature columns ({nf}); using feature_method={fm!r} for every feature column. "
            "Unified training via train.py sets feature_column_names from Translation selection.",
            UserWarning,
            stacklevel=2,
        )
    if t_map and (t_cols is None or len(t_cols) != nt):
        warnings.warn(
            "normalization.target_methods is set but target_column_names is missing or does not match "
            f"the number of target columns ({nt}); using target_method={tm!r} for every target column. "
            "Unified training via train.py sets target_column_names from Translation selection.",
            UserWarning,
            stacklevel=2,
        )

    f_methods = _resolve_axis_methods(f_cols, nf, f_map, fm)
    t_methods = _resolve_axis_methods(t_cols, nt, t_map, tm)

    for m in f_methods:
        if m not in SCALER_CLASSES:
            raise ValueError(f"Unsupported feature normalization method: {m}")
    for m in t_methods:
        if m not in SCALER_CLASSES:
            raise ValueError(f"Unsupported target normalization method: {m}")

    f_train_n, f_test_n, f_scaler = _scale_axis_per_column(
        f_train, f_test, f_methods, none_dtype, scaled_dtype
    )
    t_train_n, t_test_n, t_scaler = _scale_axis_per_column(
        t_train, t_test, t_methods, none_dtype, scaled_dtype
    )

    return f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler


def normalize_data_sets(
    feature_train,
    feature_test,
    target_train,
    target_test,
    *,
    feature_method: str = "standard",
    target_method: str = "standard",
    none_dtype=np.float64,
    scaled_dtype=None,
):
    """
    Legacy API: single method for all feature columns and all target columns.

    Prefer :func:`normalize_train_test_split` with full ``config`` for per-name maps.
    """
    fake = {
        "normalization": {
            "feature_method": feature_method,
            "target_method": target_method,
        }
    }
    return normalize_train_test_split(
        fake,
        feature_train,
        feature_test,
        target_train,
        target_test,
        feature_default="standard",
        target_default="standard",
        none_dtype=none_dtype,
        scaled_dtype=scaled_dtype,
    )
