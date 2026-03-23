"""
OpenMax algorithm — Optimized version.

Changes over openmax.py:
  - openmax_predict_batched: vectorized batch prediction (no Python per-sample loop)
  - cosine distances computed via numpy broadcasting instead of scipy per-sample
  - Same algorithm logic, just faster
"""

import numpy as np
from scipy.spatial.distance import cosine as cosine_distance
from scipy.stats import exponweib


def compute_mavs(activation_vectors, labels, num_classes):
    """Compute Mean Activation Vectors for each class. (unchanged)"""
    mavs = {}
    class_avs = {}
    for cls in range(num_classes):
        mask = labels == cls
        if mask.sum() == 0:
            continue
        cls_avs = activation_vectors[mask]
        class_avs[cls] = cls_avs
        mavs[cls] = cls_avs.mean(axis=0)
    return mavs, class_avs


def compute_distances(class_avs, mavs, distance_type="cosine"):
    """Compute distances between each sample's AV and its class MAV. Vectorized cosine."""
    distances = {}
    for cls in class_avs:
        mav = mavs[cls]
        avs = class_avs[cls]
        if distance_type == "cosine":
            # Vectorized cosine distance: 1 - (a·b)/(|a||b|)
            dot = avs @ mav
            norms_avs = np.linalg.norm(avs, axis=1)
            norm_mav = np.linalg.norm(mav)
            denom = norms_avs * norm_mav
            denom = np.maximum(denom, 1e-10)  # avoid division by zero
            dists = 1.0 - dot / denom
        else:
            dists = np.linalg.norm(avs - mav, axis=1)
        distances[cls] = dists
    return distances


def fit_weibull(distances, tail_size):
    """Fit Weibull distribution to tail distances. (unchanged)"""
    weibull_params = {}
    for cls, dists in distances.items():
        sorted_dists = np.sort(dists)[::-1]
        tail = sorted_dists[:min(tail_size, len(sorted_dists))]
        if len(tail) < 3:
            weibull_params[cls] = None
            continue
        try:
            shape, loc, scale = exponweib.fit(tail, floc=0, f0=1)
            weibull_params[cls] = (shape, loc, scale)
        except Exception:
            weibull_params[cls] = None
    return weibull_params


def openmax_predict(activation_vectors, mavs, weibull_params,
                    alpha_rank, num_classes, distance_type="cosine",
                    batch_size=10000):
    """
    Vectorized OpenMax prediction. Processes in batches to avoid huge temporary arrays.

    Returns:
        predictions: (N,) predicted class indices (num_classes = unknown)
        probabilities: (N, num_classes+1) OpenMax probability vectors
    """
    N, D = activation_vectors.shape
    all_probs = np.zeros((N, num_classes + 1), dtype=np.float64)

    # Pre-compute MAV matrix and Weibull params arrays for vectorized ops
    mav_matrix = np.zeros((num_classes, D), dtype=np.float64)
    wb_shapes = np.zeros(num_classes, dtype=np.float64)
    wb_scales = np.zeros(num_classes, dtype=np.float64)
    wb_valid = np.zeros(num_classes, dtype=bool)

    for cls in range(num_classes):
        if cls in mavs:
            mav_matrix[cls] = mavs[cls]
        if weibull_params.get(cls) is not None:
            wb_shapes[cls] = weibull_params[cls][0]
            wb_scales[cls] = weibull_params[cls][2]
            wb_valid[cls] = True

    for start in range(0, N, batch_size):
        end = min(start + batch_size, N)
        avs = activation_vectors[start:end].astype(np.float64)  # (B, D)
        B = avs.shape[0]

        # Rank classes by activation magnitude for each sample
        ranked = np.argsort(avs[:, :num_classes], axis=1)[:, ::-1]  # (B, num_classes)

        # Compute rank-based alpha weights: (B, num_classes)
        rank_alpha = np.zeros((B, num_classes), dtype=np.float64)
        for j in range(min(alpha_rank, num_classes)):
            cls_indices = ranked[:, j]  # (B,)
            weight = (alpha_rank + 1 - (j + 1)) / alpha_rank
            rank_alpha[np.arange(B), cls_indices] = weight

        # Compute distances from each sample to each class MAV: (B, num_classes)
        if distance_type == "cosine":
            # avs: (B, D), mav_matrix: (num_classes, D)
            dot = avs @ mav_matrix.T  # (B, num_classes)
            norms_avs = np.linalg.norm(avs, axis=1, keepdims=True)  # (B, 1)
            norms_mav = np.linalg.norm(mav_matrix, axis=1, keepdims=True).T  # (1, num_classes)
            denom = np.maximum(norms_avs * norms_mav, 1e-10)
            dists = 1.0 - dot / denom  # (B, num_classes)
        else:
            # Euclidean: (B, 1, D) - (1, num_classes, D) → (B, num_classes)
            dists = np.linalg.norm(avs[:, None, :] - mav_matrix[None, :, :], axis=2)

        # Weibull CDF: omega(cls) = 1 - alpha(cls) * (1 - exp(-(dist/scale)^shape))
        # Only for valid classes
        omega = np.ones((B, num_classes), dtype=np.float64)
        for cls in range(num_classes):
            if not wb_valid[cls]:
                continue
            weibull_cdf = 1.0 - np.exp(-((dists[:, cls] / wb_scales[cls]) ** wb_shapes[cls]))
            omega[:, cls] = 1.0 - rank_alpha[:, cls] * weibull_cdf

        # Recalibrate
        avs_known = avs[:, :num_classes]  # (B, num_classes)
        recalibrated = avs_known * omega  # (B, num_classes)
        unknown_activation = np.sum(avs_known * (1.0 - omega), axis=1, keepdims=True)  # (B, 1)

        # Softmax over [recalibrated, unknown]
        all_acts = np.concatenate([recalibrated, unknown_activation], axis=1)  # (B, num_classes+1)
        all_acts -= all_acts.max(axis=1, keepdims=True)  # numerical stability
        exp_acts = np.exp(all_acts)
        probs = exp_acts / exp_acts.sum(axis=1, keepdims=True)

        all_probs[start:end] = probs

    predictions = np.argmax(all_probs, axis=1)
    return predictions, all_probs
