"""
Shared utilities for NIDS autoencoder training & evaluation.
Place this file alongside your notebooks or upload to Colab.
"""

import numpy as np
import pandas as pd
import os
import json
import datetime
import pickle
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    precision_recall_fscore_support,
)


# ─────────────────────────────────────────────
# Paths  (edit once, used everywhere)
# ─────────────────────────────────────────────
DRIVE_ROOT = "/content/drive/MyDrive/Colab Notebooks/nids"
DATASET_DIR = os.path.join(DRIVE_ROOT, "CICIDS2017-dataset")
PREPROCESSING_DIR = os.path.join(DRIVE_ROOT, "preprocessing_tools")
MODELS_ROOT = os.path.join(DRIVE_ROOT, "models")

MONDAY_CSV = os.path.join(
    DATASET_DIR, "Monday-WorkingHours.pcap_ISCX.csv"
)

ATTACK_FILES = [
    os.path.join(DATASET_DIR, f)
    for f in [
        "Tuesday-WorkingHours.pcap_ISCX.csv",
        "Wednesday-workingHours.pcap_ISCX.csv",
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
        "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
        "Friday-WorkingHours-Morning.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    ]
]

LABEL_COLUMN = "Label"


# ─────────────────────────────────────────────
# Data loading & preprocessing
# ─────────────────────────────────────────────
def load_monday_benign(path=None):
    """Load Monday CSV (benign-only) and return raw DataFrame."""
    path = path or MONDAY_CSV
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    print(f"Loaded {path}  shape={df.shape}")
    print(f"Label distribution:\n{df[LABEL_COLUMN].value_counts()}")
    return df


def extract_features(df):
    """Separate features from label, clean inf/nan."""
    features = [c for c in df.columns if c != LABEL_COLUMN]
    X = df[features].copy()
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X = X.fillna(X.median(numeric_only=True))
    labels = df[LABEL_COLUMN] if LABEL_COLUMN in df.columns else None
    return X, labels, features


def fit_scaler(X_df, save_path=None):
    """Fit MinMaxScaler on training features and optionally save."""
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X_df)
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(scaler, save_path)
        print(f"Scaler saved → {save_path}")
    return scaler, X_scaled


def apply_scaler(scaler, X_df):
    """Transform features using a pre-fit scaler."""
    return scaler.transform(X_df)


def prepare_train_data(monday_path=None, scaler_save_path=None):
    """
    End-to-end: load Monday benign → extract features → fit scaler → return.
    Returns: X_scaled (ndarray), scaler, feature_columns
    """
    df = load_monday_benign(monday_path)
    benign = df[df[LABEL_COLUMN] == "BENIGN"]
    X_df, _, feature_cols = extract_features(benign)
    scaler, X_scaled = fit_scaler(X_df, save_path=scaler_save_path)
    return X_scaled.astype("float32"), scaler, feature_cols


# ─────────────────────────────────────────────
# Model saving helpers
# ─────────────────────────────────────────────
def get_model_dir(model_family, config_name):
    """Return and create a directory under MODELS_ROOT/family/config_name."""
    d = os.path.join(MODELS_ROOT, model_family, config_name)
    os.makedirs(d, exist_ok=True)
    return d


def save_training_artifacts(model_dir, history, threshold, extra_meta=None):
    """Save training history plot, loss CSV, threshold, and optional metadata."""
    # history CSV
    hist_df = pd.DataFrame(history.history)
    hist_df.to_csv(os.path.join(model_dir, "training_history.csv"), index=False)

    # loss plot
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(hist_df["loss"], label="train_loss")
    if "val_loss" in hist_df:
        ax.plot(hist_df["val_loss"], label="val_loss")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Training Loss")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(model_dir, "loss_curve.png"), dpi=150)
    plt.close(fig)

    # threshold
    with open(os.path.join(model_dir, "threshold.json"), "w") as f:
        json.dump({"threshold": float(threshold)}, f)

    # extra metadata
    if extra_meta:
        with open(os.path.join(model_dir, "meta.json"), "w") as f:
            json.dump(extra_meta, f, indent=2, default=str)

    print(f"Artifacts saved → {model_dir}")


def compute_threshold(errors, method="percentile", percentile=97):
    """
    Compute anomaly threshold from training reconstruction errors.
    method: 'percentile' or 'gaussian' (mean + 3*std)
    """
    if method == "percentile":
        return float(np.percentile(errors, percentile))
    else:
        return float(errors.mean() + 3 * errors.std())


# ─────────────────────────────────────────────
# Reconstruction error
# ─────────────────────────────────────────────
def reconstruction_mse(original, reconstructed):
    """Per-sample MSE.  Works for 2-D (dense) or 3-D (conv/lstm) arrays."""
    axes = tuple(range(1, original.ndim))
    return np.mean(np.power(original - reconstructed, 2), axis=axes)


# ─────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────
def evaluate_on_attack_files(
    model,
    scaler,
    feature_cols,
    threshold,
    benign_path=None,
    attack_paths=None,
    reshape_fn=None,
):
    """
    Evaluate one model against every attack file.
    reshape_fn: optional callable to reshape X before predict (e.g. for CNN/LSTM).
    Returns a DataFrame of per-attack-file metrics.
    """
    benign_path = benign_path or MONDAY_CSV
    attack_paths = attack_paths or ATTACK_FILES

    # load benign
    X_benign, _ = _load_and_scale(benign_path, scaler, feature_cols)
    if reshape_fn:
        X_benign = reshape_fn(X_benign)
    recon_benign = model.predict(X_benign, verbose=0)
    benign_errors = reconstruction_mse(X_benign, recon_benign)

    rows = []
    for fpath in attack_paths:
        name = os.path.basename(fpath)
        X_atk, _ = _load_and_scale(fpath, scaler, feature_cols)
        if reshape_fn:
            X_atk = reshape_fn(X_atk)
        recon_atk = model.predict(X_atk, verbose=0)
        atk_errors = reconstruction_mse(X_atk, recon_atk)

        y_true = np.concatenate(
            [np.zeros(len(benign_errors)), np.ones(len(atk_errors))]
        )
        y_scores = np.concatenate([benign_errors, atk_errors])
        y_pred = (y_scores > threshold).astype(int)

        prec, rec, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0
        )
        auc_val = roc_auc_score(y_true, y_scores)
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        acc = (tp + tn) / (tp + tn + fp + fn)

        rows.append(
            {
                "Attack": name,
                "Threshold": threshold,
                "Accuracy": acc,
                "Precision": prec,
                "Recall": rec,
                "F1": f1,
                "AUC": auc_val,
                "TP": tp,
                "TN": tn,
                "FP": fp,
                "FN": fn,
            }
        )

    return pd.DataFrame(rows)


def _load_and_scale(csv_path, scaler, feature_cols):
    """Internal: load CSV, extract features, apply scaler."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    labels = df[LABEL_COLUMN] if LABEL_COLUMN in df.columns else None
    X = df[feature_cols].copy()
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X = X.fillna(X.median(numeric_only=True))
    X_scaled = scaler.transform(X).astype("float32")
    return X_scaled, labels


# ─────────────────────────────────────────────
# Plotting helpers
# ─────────────────────────────────────────────
def plot_error_distribution(train_errors, threshold, title="", save_path=None):
    """Histogram of reconstruction errors with threshold line."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(train_errors, bins=100, alpha=0.7, label="Train MSE")
    ax.axvline(threshold, color="r", linestyle="--", label=f"Threshold={threshold:.6f}")
    ax.set_xlabel("Reconstruction MSE")
    ax.set_ylabel("Count")
    ax.set_title(title or "Reconstruction Error Distribution")
    ax.legend()
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_roc_curves(results_df, model_name="", save_path=None):
    """Plot ROC curves if raw scores are provided (placeholder for extension)."""
    pass  # extend if needed
