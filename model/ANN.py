# ANN.py
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import psutil
import tensorflow as tf
from sklearn.model_selection import train_test_split

import normalization
import report


# ---------------- LOGGER ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ---------------- KERAS CUSTOM LAYERS ----------------
@tf.keras.utils.register_keras_serializable(package="ConureANN")
class SliceLayer(tf.keras.layers.Layer):
    """
    Serializable replacement for Lambda-based slicing.

    Supports selecting columns from a 2D feature matrix:
      input shape:  (batch, n_features)
      output shape: (batch, len(indices))
    """

    def __init__(self, indices: Sequence[int], **kwargs):
        super().__init__(**kwargs)
        if not isinstance(indices, (list, tuple)) or not indices:
            raise ValueError("SliceLayer 'indices' must be a non-empty list/tuple of integers.")
        self.indices = [int(i) for i in indices]

    def call(self, inputs):
        return tf.gather(inputs, indices=self.indices, axis=-1)

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"indices": self.indices})
        return cfg


# ---------------- CONFIG HELPERS ----------------
def _deepcopy_jsonish(obj: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(obj))


def _as_list(value: Any, field_name: str) -> List[Any]:
    if not isinstance(value, list):
        raise ValueError(f"'{field_name}' must be a list.")
    return value


def _require_dict(value: Any, field_name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"'{field_name}' must be an object.")
    return value


def _architecture_type(config: Dict[str, Any]) -> str:
    # backward compatible default
    return str(config.get("architecture_type", "sequential")).strip().lower()


def _is_auto_units(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() == "AUTO"


def _resolve_units(value: Any, y_dim: int) -> int:
    if _is_auto_units(value):
        return int(y_dim)
    return int(value)


def _build_regularizer(layer_cfg: Dict[str, Any]):
    regularizers = tf.keras.regularizers
    reg_cfg = layer_cfg.get("regularizer")
    if not reg_cfg:
        return None

    reg_cfg = _require_dict(reg_cfg, "regularizer")
    reg_type = str(reg_cfg.get("type", "")).strip().lower()

    if reg_type == "l1":
        return regularizers.l1(float(reg_cfg["value"]))
    if reg_type == "l2":
        return regularizers.l2(float(reg_cfg["value"]))
    if reg_type == "l1_l2":
        return regularizers.l1_l2(
            l1=float(reg_cfg.get("l1", 0.0)),
            l2=float(reg_cfg.get("l2", 0.0)),
        )

    raise ValueError(f"Unsupported regularizer type: {reg_type}")


def _build_optimizer(config: Dict[str, Any]):
    opt_conf = config.get(
        "training",
        {},
    ).get(
        "optimizer",
        {"type": "Adam", "learning_rate": 0.001},
    )

    opt_type = str(opt_conf.get("type", "Adam")).strip().lower()
    lr = float(opt_conf.get("learning_rate", 0.001))

    if opt_type == "adam":
        return tf.keras.optimizers.Adam(learning_rate=lr)
    if opt_type == "sgd":
        momentum = float(opt_conf.get("momentum", 0.0))
        return tf.keras.optimizers.SGD(learning_rate=lr, momentum=momentum)
    if opt_type == "rmsprop":
        return tf.keras.optimizers.RMSprop(learning_rate=lr)
    if opt_type == "adagrad":
        return tf.keras.optimizers.Adagrad(learning_rate=lr)

    raise ValueError(f"Unsupported optimizer type: {opt_type}")


# ================== FIXED NORMALIZATION FUNCTIONS ==================

def _normalize_loss_for_multi_output(loss_cfg: Any, output_names: Sequence[str]):
    if len(output_names) <= 1:
        return loss_cfg if loss_cfg is not None else "mse"

    if loss_cfg is None:
        return {name: "mse" for name in output_names}

    # If scalar (str or other), apply to all outputs
    if not isinstance(loss_cfg, dict):
        return {name: loss_cfg for name in output_names}

    # If dict, ensure every output has a loss (fallback to mse)
    return {name: loss_cfg.get(name, "mse") for name in output_names}


def _normalize_metrics_for_multi_output(metrics_cfg: Any, output_names: Sequence[str]):
    if len(output_names) <= 1:
        return metrics_cfg if metrics_cfg is not None else ["mae"]

    if metrics_cfg is None:
        return {name: ["mae"] for name in output_names}

    if isinstance(metrics_cfg, (str, list)):
        return {name: metrics_cfg if isinstance(metrics_cfg, list) else [metrics_cfg]
                for name in output_names}

    if isinstance(metrics_cfg, dict):
        return {name: metrics_cfg.get(name, ["mae"]) for name in output_names}

    return {name: ["mae"] for name in output_names}


def _keras_output_names(model: tf.keras.Model) -> List[str]:
    """
    Output identifiers used by Keras for compile(loss=...) and fit(y=...) dicts.
    These are layer names, not symbolic tensor names (which often look like keras_tensor_*).
    """
    names = getattr(model, "output_names", None)
    if names is not None:
        return list(names)
    layers = getattr(model, "output_layers", None)
    if layers is not None:
        return [layer.name for layer in layers]
    return [tensor.name.split(":")[0].split("/")[-1] for tensor in model.outputs]


def _split_targets_for_model(
    y: np.ndarray,
    model: tf.keras.Model,
) -> Union[np.ndarray, Dict[str, np.ndarray]]:
    """
    Convert a flat y matrix into:
      - a single ndarray for single-output models
      - a dict(name -> ndarray slice) for multi-output models
    """
    output_names = _keras_output_names(model)

    if len(output_names) == 1:
        return y

    offset = 0
    out: Dict[str, np.ndarray] = {}
    for name, tensor in zip(output_names, model.outputs):
        shape = tensor.shape
        width = int(shape[-1])
        out[name] = y[:, offset : offset + width]
        offset += width

    if offset != y.shape[1]:
        raise ValueError(
            f"Target width mismatch for multi-output model. "
            f"Model expects total output width {offset}, but y has width {y.shape[1]}."
        )

    return out


def _merge_predictions(
    y_pred: Union[np.ndarray, List[np.ndarray], Tuple[np.ndarray, ...], Dict[str, np.ndarray]],
    model: tf.keras.Model,
) -> np.ndarray:
    """
    Convert Keras predict output into one 2D ndarray so scaling/reporting stays compatible.
    """
    if isinstance(y_pred, np.ndarray):
        if y_pred.ndim == 1:
            return y_pred.reshape(-1, 1)
        return y_pred

    output_names = _keras_output_names(model)

    if isinstance(y_pred, dict):
        parts = []
        for name in output_names:
            arr = np.asarray(y_pred[name])
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            parts.append(arr)
        return np.concatenate(parts, axis=1)

    if isinstance(y_pred, (list, tuple)):
        parts = []
        for arr in y_pred:
            arr = np.asarray(arr)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            parts.append(arr)
        return np.concatenate(parts, axis=1)

    raise TypeError(f"Unsupported prediction type: {type(y_pred)}")


def print_model_structure(model):
    """
    Print a readable text summary to the terminal.
    """
    # line_length omitted — Keras 3 picks width from the environment (like a real terminal).
    model.summary(expand_nested=True)


def save_model_structure_image(model, save_path="architecture.png", rankdir="TB"):
    """
    Save a diagram of the architecture.

    Requires:
      - pydot
      - graphviz installed on the system
    """
    try:
        save_dir = os.path.dirname(os.path.abspath(save_path))
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        tf.keras.utils.plot_model(
            model,
            to_file=save_path,
            show_shapes=True,
            show_dtype=False,
            show_layer_names=True,
            expand_nested=True,
            show_trainable=True,
            rankdir=rankdir,
        )
        logger.info(f"Architecture diagram saved to: {save_path}")
    except Exception as e:
        logger.warning(
            "Could not save architecture diagram. "
            "Make sure pydot and graphviz are installed. "
            f"Reason: {e}"
        )


# ---------------- SEQUENTIAL BUILDER ----------------
def _build_sequential_model(
    input_dim: int,
    output_dim: int,
    config: Dict[str, Any],
) -> tf.keras.Model:
    architecture = _as_list(config.get("architecture"), "architecture")
    if not architecture:
        raise ValueError("Sequential architecture must contain at least one layer.")

    model = tf.keras.Sequential(name=config.get("model_name", "ANN"))

    for i, layer_cfg in enumerate(architecture):
        layer_cfg = _require_dict(layer_cfg, f"architecture[{i}]")
        layer_type = str(layer_cfg.get("type", "")).strip()

        if layer_type == "Dense":
            units = _resolve_units(layer_cfg.get("units"), output_dim)
            kwargs = {
                "units": units,
                "activation": layer_cfg.get("activation", "linear"),
                "kernel_regularizer": _build_regularizer(layer_cfg),
                "name": layer_cfg.get("name"),
            }
            if i == 0:
                kwargs["input_shape"] = (input_dim,)
            model.add(tf.keras.layers.Dense(**kwargs))

        elif layer_type == "Dropout":
            model.add(
                tf.keras.layers.Dropout(
                    rate=float(layer_cfg["rate"]),
                    name=layer_cfg.get("name"),
                )
            )

        else:
            raise ValueError(f"Unsupported sequential layer type: {layer_type}")

    return model


# ---------------- GRAPH / SUBNET BUILDER ----------------
def _get_tensor_from_registry(
    registry: Dict[str, tf.Tensor],
    name: str,
) -> tf.Tensor:
    if name not in registry:
        raise ValueError(f"Unknown input tensor reference: '{name}'")
    return registry[name]


def _ensure_inputs_field(node_cfg: Dict[str, Any], node_name: str) -> List[str]:
    inputs = node_cfg.get("inputs")
    if inputs is None:
        raise ValueError(f"Graph node '{node_name}' is missing 'inputs'.")
    inputs = _as_list(inputs, f"graph.nodes[{node_name}].inputs")
    if not inputs:
        raise ValueError(f"Graph node '{node_name}' must reference at least one input.")
    return [str(x) for x in inputs]


def _build_graph_model(
    input_dim: int,
    output_dim: int,
    config: Dict[str, Any],
) -> tf.keras.Model:
    graph = _require_dict(config.get("graph"), "graph")

    input_name = str(graph.get("input_name", "features")).strip() or "features"
    input_tensor = tf.keras.Input(shape=(input_dim,), name=input_name)

    registry: Dict[str, tf.Tensor] = {input_name: input_tensor}

    nodes = _as_list(graph.get("nodes", []), "graph.nodes")
    if not nodes:
        raise ValueError("graph.nodes must contain at least one node.")

    for idx, node_cfg in enumerate(nodes):
        node_cfg = _require_dict(node_cfg, f"graph.nodes[{idx}]")
        node_name = str(node_cfg.get("name", "")).strip()
        op = str(node_cfg.get("op", "")).strip()

        if not node_name:
            raise ValueError(f"graph.nodes[{idx}] is missing a non-empty 'name'.")
        if node_name in registry:
            raise ValueError(f"Duplicate graph node name: '{node_name}'")
        if not op:
            raise ValueError(f"graph.nodes[{idx}] is missing 'op'.")

        input_names = _ensure_inputs_field(node_cfg, node_name)
        input_tensors = [_get_tensor_from_registry(registry, name) for name in input_names]

        if op == "Dense":
            if len(input_tensors) != 1:
                raise ValueError(f"Graph Dense node '{node_name}' must have exactly one input.")
            units = _resolve_units(node_cfg.get("units"), output_dim)
            tensor = tf.keras.layers.Dense(
                units=units,
                activation=node_cfg.get("activation", "linear"),
                kernel_regularizer=_build_regularizer(node_cfg),
                name=node_name,
            )(input_tensors[0])

        elif op == "Dropout":
            if len(input_tensors) != 1:
                raise ValueError(f"Graph Dropout node '{node_name}' must have exactly one input.")
            tensor = tf.keras.layers.Dropout(
                rate=float(node_cfg["rate"]),
                name=node_name,
            )(input_tensors[0])

        elif op == "Concatenate":
            if len(input_tensors) < 2:
                raise ValueError(f"Graph Concatenate node '{node_name}' needs at least two inputs.")
            axis = int(node_cfg.get("axis", -1))
            tensor = tf.keras.layers.Concatenate(axis=axis, name=node_name)(input_tensors)

        elif op == "Add":
            if len(input_tensors) < 2:
                raise ValueError(f"Graph Add node '{node_name}' needs at least two inputs.")
            tensor = tf.keras.layers.Add(name=node_name)(input_tensors)

        elif op == "Slice":
            if len(input_tensors) != 1:
                raise ValueError(f"Graph Slice node '{node_name}' must have exactly one input.")
            indices = node_cfg.get("indices")
            indices = _as_list(indices, f"graph.nodes[{node_name}].indices")
            tensor = SliceLayer(indices=indices, name=node_name)(input_tensors[0])

        elif op == "Identity":
            if len(input_tensors) != 1:
                raise ValueError(f"Graph Identity node '{node_name}' must have exactly one input.")
            tensor = tf.identity(input_tensors[0], name=node_name)

        else:
            raise ValueError(f"Unsupported graph op '{op}' in node '{node_name}'.")

        registry[node_name] = tensor

    output_names = _as_list(graph.get("outputs", []), "graph.outputs")
    if not output_names:
        raise ValueError("graph.outputs must contain at least one output name.")

    output_tensors = []
    for output_name in output_names:
        output_name = str(output_name)
        output_tensors.append(_get_tensor_from_registry(registry, output_name))

    model = tf.keras.Model(
        inputs=input_tensor,
        outputs=output_tensors if len(output_tensors) > 1 else output_tensors[0],
        name=config.get("model_name", "ANN"),
    )
    return model


# ---------------- MODEL GENERATION ----------------
def generate_model(train_features, train_targets, config):
    val_size = float(config["training"].get("validation_split", 0.2))
    if not (0.0 < val_size < 1.0):
        raise ValueError(f"training.validation_split must be between 0 and 1, got {val_size}")

    random_state = int(
        config.get("data_split", {}).get("random_state", config.get("random_state", 42))
    )

    train_f, val_f, train_t, val_t = train_test_split(
        train_features,
        train_targets,
        test_size=val_size,
        random_state=random_state,
    )

    arch_type = _architecture_type(config)
    input_dim = int(train_features.shape[1])
    output_dim = int(train_targets.shape[1])

    if arch_type == "sequential":
        model = _build_sequential_model(input_dim=input_dim, output_dim=output_dim, config=config)
    elif arch_type == "graph":
        model = _build_graph_model(input_dim=input_dim, output_dim=output_dim, config=config)
    else:
        raise ValueError(
            f"Unsupported architecture_type '{arch_type}'. "
            f"Supported values: 'sequential', 'graph'."
        )

    optimizer = _build_optimizer(config)

    output_names = _keras_output_names(model)
    loss_cfg = _normalize_loss_for_multi_output(config["training"].get("loss", "mse"), output_names)
    metrics_cfg = _normalize_metrics_for_multi_output(config["training"].get("metrics", ["mae"]), output_names)

    model.compile(
        optimizer=optimizer,
        loss=loss_cfg,
        metrics=metrics_cfg,
    )

    callbacks = []
    if config.get("early_stopping"):
        callbacks.append(tf.keras.callbacks.EarlyStopping(**config["early_stopping"]))

    train_t_fit = _split_targets_for_model(train_t, model)
    val_t_fit = _split_targets_for_model(val_t, model)

    history = model.fit(
        train_f,
        train_t_fit,
        validation_data=(val_f, val_t_fit),
        epochs=int(config["training"]["epochs"]),
        batch_size=int(config["training"]["batch_size"]),
        callbacks=callbacks,
        verbose=1,
    )

    return model, history


# ---------------- PREDICT ----------------
def predict(model_dir, X_new):
    """
    Run prediction using a trained ANN model.
    Returns a single 2D ndarray even for multi-output graph models.
    """
    X_new = np.asarray(X_new, dtype=np.float32)

    if X_new.ndim == 1:
        X_new = X_new.reshape(1, -1)

    if np.isnan(X_new).any():
        raise ValueError("X_new contains NaN values.")

    model_path = os.path.join(model_dir, "model.keras")
    legacy_model_path = os.path.join(model_dir, os.path.basename(model_dir) + ".keras")
    feature_scaler_path = os.path.join(model_dir, "feature_scaler.pkl")
    target_scaler_path = os.path.join(model_dir, "target_scaler.pkl")

    if not os.path.exists(model_path):
        if os.path.exists(legacy_model_path):
            model_path = legacy_model_path
        else:
            raise FileNotFoundError(
                f"ANN model file not found. Checked: {model_path} and {legacy_model_path}"
            )

    model = tf.keras.models.load_model(
        model_path,
        custom_objects={"SliceLayer": SliceLayer},
    )

    f_scaler = joblib.load(feature_scaler_path) if os.path.exists(feature_scaler_path) else None
    t_scaler = joblib.load(target_scaler_path) if os.path.exists(target_scaler_path) else None

    if f_scaler is not None:
        expected_features = getattr(f_scaler, "n_features_in_", None)
        if expected_features is not None and int(expected_features) != int(X_new.shape[1]):
            raise ValueError(
                f"Feature count mismatch: model expects {int(expected_features)} features, "
                f"got {int(X_new.shape[1])}."
            )
        X_norm = f_scaler.transform(X_new).astype(np.float32)
    else:
        X_norm = X_new.astype(np.float32)

    y_pred_raw = model.predict(X_norm, verbose=0)
    y_pred_norm = _merge_predictions(y_pred_raw, model)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    return y_pred


# ---------------- REPORT GENERATION ----------------
def generate_report(
    model,
    history,
    f_train,
    f_test,
    t_train,
    t_test,
    f_scaler,
    t_scaler,
    config,
    train_duration,
    save_path,
):
    if f_scaler is not None:
        f_test_eval = f_scaler.transform(f_test).astype(np.float32)
    else:
        f_test_eval = np.asarray(f_test, dtype=np.float32)

    y_pred_raw = model.predict(f_test_eval, verbose=0)
    y_pred_norm = _merge_predictions(y_pred_raw, model)

    if t_scaler is not None:
        y_pred = t_scaler.inverse_transform(y_pred_norm)
    else:
        y_pred = y_pred_norm

    perf_metrics = report.calculate_metrics(t_test, y_pred)

    gpu_devices = tf.config.list_physical_devices("GPU")
    gpu_details = []
    if gpu_devices:
        for gpu in gpu_devices:
            details = tf.config.experimental.get_device_details(gpu)
            gpu_details.append(
                {
                    "name": details.get("device_name", "Unknown GPU"),
                    "compute_capability": details.get("compute_capability", None),
                }
            )

    process = psutil.Process(os.getpid())
    peak_ram_gb = round(process.memory_info().rss / (1024 ** 3), 2)

    model_path = os.path.join(save_path, "model.keras")
    model_size_mb = (
        round(os.path.getsize(model_path) / (1024 ** 2), 2)
        if os.path.exists(model_path)
        else None
    )

    total_samples = f_train.shape[0] + f_test.shape[0]
    val_split = float(config["training"].get("validation_split", 0.2))
    train_samples = int(f_train.shape[0] * (1 - val_split))
    validation_samples = int(f_train.shape[0] * val_split)

    test_size = float(config.get("data_split", {}).get("test_size", 0.2))
    random_state = int(config.get("data_split", {}).get("random_state", config.get("random_state", 42)))

    feature_norm_used, target_norm_used = normalization.normalization_usage_flags(
        config,
        n_features=int(f_train.shape[1]),
        n_targets=int(t_train.shape[1]),
        feature_default="standard",
        target_default="standard",
    )

    full_report = {
        "model_info": {
            "model_name": config["model_name"],
            "model_type": config["model_type"],
            "framework": "TensorFlow",
            "framework_version": tf.__version__,
            "architecture_type": _architecture_type(config),
            "trainable_parameters": int(model.count_params()),
            "model_size_mb": model_size_mb,
            "training_duration_sec": train_duration,
            "completion_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "data_info": {
            "input_dim": int(f_train.shape[1]),
            "output_dim": int(t_train.shape[1]),
            "total_samples": int(total_samples),
            "train_samples": int(train_samples),
            "validation_samples": int(validation_samples),
            "test_samples": int(f_test.shape[0]),
            "split_strategy": "train_test_split",
            "test_size": test_size,
            "validation_split": val_split,
            "random_state": random_state,
        },
        "training_summary": {
            "epochs_completed": int(len(history.history["loss"])),
            "final_train_loss": float(history.history["loss"][-1]),
            "final_val_loss": float(history.history["val_loss"][-1]),
            "best_val_loss": float(min(history.history["val_loss"])),
        },
        "performance": {
            "metrics": perf_metrics,
            "evaluation_protocol": {
                "evaluation_dataset": "held-out test set",
                "predictions_inverse_transformed": target_norm_used,
                "normalization_used": feature_norm_used or target_norm_used,
                "feature_normalization_used": feature_norm_used,
                "target_normalization_used": target_norm_used,
            },
        },
        "system_info": report.get_system_info(),
        "hardware_info": {
            "gpu_utilized": len(gpu_details) > 0,
            "gpu_count": len(gpu_details),
            "gpu_details": gpu_details if gpu_details else "CPU Mode",
            "peak_process_ram_gb": peak_ram_gb,
        },
        "configuration": config,
    }

    return full_report


# ---------------- TRAINING PIPELINE ----------------
def _prepare_config_for_training(X, y, config):
    """
    Make a safe copy and resolve AUTO units + auto-fix loss/metrics for multi-output graph models.
    """
    config = _deepcopy_jsonish(config)
    arch_type = _architecture_type(config)

    if arch_type == "sequential":
        architecture = _as_list(config.get("architecture"), "architecture")
        if not architecture:
            raise ValueError("Sequential architecture cannot be empty.")
        last_layer = _require_dict(architecture[-1], "architecture[-1]")
        if _is_auto_units(last_layer.get("units")):
            last_layer["units"] = int(y.shape[1])

    elif arch_type == "graph":
        graph = _require_dict(config.get("graph"), "graph")
        nodes = _as_list(graph.get("nodes", []), "graph.nodes")
        for node in nodes:
            node = _require_dict(node, "graph.nodes[]")
            if str(node.get("op", "")).strip() == "Dense" and _is_auto_units(node.get("units")):
                node["units"] = int(y.shape[1])

        # CRITICAL FIX: Auto-configure loss and metrics when there are multiple outputs
        output_names = _as_list(graph.get("outputs", []), "graph.outputs")
        if len(output_names) > 1:
            training = config.setdefault("training", {})

            # Fix loss
            loss = training.get("loss")
            if loss is None or not isinstance(loss, dict):
                training["loss"] = {name: "mse" for name in output_names}
            elif isinstance(loss, dict):
                training["loss"] = {name: loss.get(name, "mse") for name in output_names}

            # Fix metrics
            metrics = training.get("metrics")
            if metrics is None or not isinstance(metrics, dict):
                training["metrics"] = {name: ["mae"] for name in output_names}
            elif isinstance(metrics, (str, list)):
                training["metrics"] = {name: metrics if isinstance(metrics, list) else [metrics]
                                       for name in output_names}
            elif isinstance(metrics, dict):
                training["metrics"] = {name: metrics.get(name, ["mae"]) for name in output_names}

    else:
        raise ValueError(
            f"Unsupported architecture_type '{arch_type}'. "
            f"Supported values: 'sequential', 'graph'."
        )

    return config


def train_model_pipeline(X, y, config, model_base_dir):
    data_split_cfg = config.get("data_split", {})
    test_size = float(data_split_cfg.get("test_size", 0.2))
    random_state = int(data_split_cfg.get("random_state", config.get("random_state", 42)))

    f_train, f_test, t_train, t_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    norm = dict(config.get("normalization") or {})
    norm.setdefault("feature_method", "standard")
    norm.setdefault("target_method", "standard")
    config = dict(config)
    config["normalization"] = norm

    f_train_n, f_test_n, t_train_n, t_test_n, f_scaler, t_scaler = normalization.normalize_train_test_split(
        config,
        f_train,
        f_test,
        t_train,
        t_test,
        feature_default="standard",
        target_default="standard",
        none_dtype=np.float32,
        scaled_dtype=np.float32,
    )

    config = _prepare_config_for_training(X, y, config)

    start_time = time.time()
    model, history = generate_model(f_train_n, t_train_n, config)
    train_duration = time.time() - start_time
    logger.info(f"Training completed in {train_duration:.2f} seconds.")

    save_path = os.path.join(model_base_dir, config["model_name"])
    os.makedirs(save_path, exist_ok=True)

    # Save trained model
    model_file = os.path.join(save_path, "model.keras")
    model.save(model_file)

    # Save text summary
    summary_file = os.path.join(save_path, "model_summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        model.summary(
            print_fn=lambda line: f.write(line + "\n"),
            expand_nested=True,
        )
    logger.info(f"Model summary saved to: {summary_file}")

    # Save architecture diagram in the same folder
    diagram_file = os.path.join(save_path, "architecture.png")
    save_model_structure_image(
        model,
        save_path=diagram_file,
        rankdir="TB",
    )

    if f_scaler is not None:
        joblib.dump(f_scaler, os.path.join(save_path, "feature_scaler.pkl"))
    if t_scaler is not None:
        joblib.dump(t_scaler, os.path.join(save_path, "target_scaler.pkl"))

    with open(os.path.join(save_path, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    history_file = os.path.join(save_path, "history.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history.history, f, indent=4)

    report_data = generate_report(
        model,
        history,
        f_train,
        f_test,
        t_train,
        t_test,
        f_scaler,
        t_scaler,
        config,
        train_duration,
        save_path,
    )
    report.save_report(report_data, save_path)
    report.log_metric(report_data["performance"]["metrics"], config["model_type"], logger)

    logger.info("Report successfully generated.")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    FILE_PATH = "/mnt/storage/emon/projects/Conure/data/workspace/IND2/sweep/Inductor_Coplanar_2/simulation_data.npz"
    MODEL_BASE_DIR = "/mnt/storage/emon/projects/Conure/data/workspace/IND2/model/DAMN"

    train_config = {
        "model_name": "TX11_ANN_subnets",
        "model_type": "ANN",
        "architecture_type": "graph",
        "data_split": {
            "test_size": 0.2,
            "random_state": 42,
        },
        "normalization": {
            "feature_method": "standard",
            "target_method": "standard",
        },
        "training": {
            "epochs": 100,
            "batch_size": 32,
            "loss": "mse",
            "metrics": ["mae"],
            "validation_split": 0.2,
            "optimizer": {
                "type": "Adam",
                "learning_rate": 0.001,
                "momentum": 0.9,
            },
        },
        "early_stopping": {
            "monitor": "val_loss",
            "patience": 15,
            "restore_best_weights": True,
        },
        "graph": {
            "input_name": "features",
            "nodes": [
                {"name": "apothem", "op": "Slice", "inputs": ["features"], "indices": [0]},
                {"name": "width",   "op": "Slice", "inputs": ["features"], "indices": [1]},
                {"name": "spacing", "op": "Slice", "inputs": ["features"], "indices": [2]},

                {"name": "apothem_h1", "op": "Dense", "inputs": ["apothem"], "units": 100, "activation": "relu"},
                {"name": "width_h1",   "op": "Dense", "inputs": ["width"],   "units": 50,  "activation": "relu"},
                {"name": "spacing_h1", "op": "Dense", "inputs": ["spacing"], "units": 20,  "activation": "relu"},

                {"name": "apothem_h2", "op": "Dense", "inputs": ["apothem_h1"], "units": 500, "activation": "relu"},
                {"name": "width_h2",   "op": "Dense", "inputs": ["width_h1"],   "units": 200, "activation": "relu"},
                {"name": "spacing_h2", "op": "Dense", "inputs": ["spacing_h1"], "units": 120, "activation": "relu"},

                {"name": "apothem_h3", "op": "Dense", "inputs": ["apothem_h2"], "units": 1000, "activation": "relu"},

                {"name": "merge_width_spacing", "op": "Concatenate", "inputs": ["width_h2", "spacing_h2"]},
                {"name": "ws_h3", "op": "Dense", "inputs": ["merge_width_spacing"], "units": 400, "activation": "relu"},

                {"name": "Lp", "op": "Dense", "inputs": ["apothem_h3"], "units": 1, "activation": "linear"},
                {"name": "Ls", "op": "Dense", "inputs": ["apothem_h3"], "units": 1, "activation": "linear"},
                {"name": "Qp", "op": "Dense", "inputs": ["ws_h3"],      "units": 1, "activation": "linear"},
                {"name": "Qs", "op": "Dense", "inputs": ["ws_h3"],      "units": 1, "activation": "linear"},
                {"name": "k",  "op": "Dense", "inputs": ["spacing_h2"], "units": 1, "activation": "linear"},
            ],
            "outputs": ["Lp", "Ls", "Qp", "Qs", "k"],
        },
    }

    # Build only for inspection
    config_for_build = _prepare_config_for_training(
        X=np.zeros((4, 3), dtype=np.float32),
        y=np.zeros((4, 5), dtype=np.float32),
        config=train_config,
    )

    model = _build_graph_model(
        input_dim=3,
        output_dim=5,
        config=config_for_build,
    )

    print_model_structure(model)
    save_model_structure_image(
        model,
        save_path=os.path.join(MODEL_BASE_DIR, "architecture.png"),
        rankdir="TB",
    )

    logger.info("Subnet ANN model structure built successfully.")