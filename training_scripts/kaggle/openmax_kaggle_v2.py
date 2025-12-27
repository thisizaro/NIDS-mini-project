"""
OpenMax algorithm v2 — Fixed for Kaggle.

Fixes over v1 (openmax_kaggle.py):
  1. fit_weibull uses scipy.stats.weibull_min (not exponweib) — exponweib.fit
     returns 4 values but v1 unpacked into 3 → silent failure.
  2. New hybrid_openmax_predict: uses penultimate-layer distances for Weibull
     revision but logit-layer scores for recalibration — the correct OpenMax
     formulation from Bendale & Boult (2016).
  3. softmax_threshold_predict: simple MSP (Maximum Softmax Probability) baseline
     for unknown detection — works when Weibull-based OpenMax is unreliable.
  4. All arrays cast to float64 internally to avoid float16 overflow.
"""

import numpy as np
from scipy.stats import weibull_min


# ═══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS (same API as v1, but fixed)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_mavs(activation_vectors, labels, num_classes):
    """Compute Mean Activation Vectors for each class."""
    avs = activation_vectors.astype(np.float64)
    mavs = {}
    class_avs = {}
    for cls in range(num_classes):
        mask = labels == cls
        if mask.sum() == 0:
            continue
        cls_avs = avs[mask]
        class_avs[cls] = cls_avs
        mavs[cls] = cls_avs.mean(axis=0)
    return mavs, class_avs


def compute_distances(class_avs, mavs, distance_type="cosine"):
    """Compute distances between each sample's AV and its class MAV."""
    distances = {}
    for cls in class_avs:
        mav = mavs[cls].astype(np.float64)
        avs = class_avs[cls].astype(np.float64)
        if distance_type == "cosine":
            dot = avs @ mav
            norms_avs = np.linalg.norm(avs, axis=1)
            norm_mav = np.linalg.norm(mav)
            denom = np.maximum(norms_avs * norm_mav, 1e-10)
            dists = 1.0 - dot / denom
        else:
            dists = np.linalg.norm(avs - mav, axis=1)
        distances[cls] = dists
    return distances


def fit_weibull(distances, tail_size):
    """Fit Weibull distribution to tail distances using weibull_min."""
    weibull_params = {}
    for cls, dists in distances.items():
        sorted_dists = np.sort(dists)[::-1]
        tail = sorted_dists[:min(tail_size, len(sorted_dists))].astype(np.float64)
        if len(tail) < 3:
            weibull_params[cls] = None
            continue
        try:
            c, loc, scale = weibull_min.fit(tail, floc=0)
            if np.isfinite(c) and np.isfinite(scale) and c > 0 and scale > 0:
                weibull_params[cls] = (c, loc, scale)
            else:
                weibull_params[cls] = None
        except Exception:
            weibull_params[cls] = None
    return weibull_params


# ═══════════════════════════════════════════════════════════════════════════════
# STANDARD OPENMAX (operates on logit vectors — dimension = num_classes)
# ═══════════════════════════════════════════════════════════════════════════════

def openmax_predict(activation_vectors, mavs, weibull_params,
                    alpha_rank, num_classes, distance_type="cosine",
                    batch_size=10000):
    """
    Standard OpenMax on logit-space vectors (dimension = num_classes).

    This is the correct usage: pass the pre-softmax logits so that
    avs[:, :num_classes] selects all class scores for recalibration.

    Returns:
        predictions: (N,) predicted class indices (num_classes = unknown)
        probabilities: (N, num_classes+1) OpenMax probability vectors
    """
    N, D = activation_vectors.shape
    all_probs = np.zeros((N, num_classes + 1), dtype=np.float64)

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
        avs = activation_vectors[start:end].astype(np.float64)
        B = avs.shape[0]

        ranked = np.argsort(avs[:, :num_classes], axis=1)[:, ::-1]

        rank_alpha = np.zeros((B, num_classes), dtype=np.float64)
        for j in range(min(alpha_rank, num_classes)):
            cls_indices = ranked[:, j]
            weight = (alpha_rank + 1 - (j + 1)) / alpha_rank
            rank_alpha[np.arange(B), cls_indices] = weight

        if distance_type == "cosine":
            dot = avs @ mav_matrix.T
            norms_avs = np.linalg.norm(avs, axis=1, keepdims=True)
            norms_mav = np.linalg.norm(mav_matrix, axis=1, keepdims=True).T
            denom = np.maximum(norms_avs * norms_mav, 1e-10)
            dists = 1.0 - dot / denom
        else:
            dists = np.linalg.norm(avs[:, None, :] - mav_matrix[None, :, :], axis=2)

        omega = np.ones((B, num_classes), dtype=np.float64)
        for cls in range(num_classes):
            if not wb_valid[cls]:
                continue
            weibull_cdf = 1.0 - np.exp(-((dists[:, cls] / wb_scales[cls]) ** wb_shapes[cls]))
            omega[:, cls] = 1.0 - rank_alpha[:, cls] * weibull_cdf

        avs_known = avs[:, :num_classes]
        recalibrated = avs_known * omega
        unknown_activation = np.sum(avs_known * (1.0 - omega), axis=1, keepdims=True)

        all_acts = np.concatenate([recalibrated, unknown_activation], axis=1)
        all_acts -= all_acts.max(axis=1, keepdims=True)
        exp_acts = np.exp(all_acts)
        probs = exp_acts / exp_acts.sum(axis=1, keepdims=True)

        all_probs[start:end] = probs

    predictions = np.argmax(all_probs, axis=1)
    return predictions, all_probs


# ═══════════════════════════════════════════════════════════════════════════════
# HYBRID OPENMAX (penultimate distances + logit recalibration)
# ═══════════════════════════════════════════════════════════════════════════════

def hybrid_openmax_predict(logits, penultimate_avs, mavs_penultimate,
                           weibull_params, alpha_rank, num_classes,
                           distance_type="cosine", batch_size=10000):
    """
    Hybrid OpenMax — the proper formulation from Bendale & Boult (2016):
      - Distances computed in penultimate (feature) space → Weibull CDF → omega
      - Recalibration applied to logit (pre-softmax) scores

    This separates "how far is this sample from known clusters" (penultimate)
    from "what are the class scores" (logits).

    Args:
        logits:              (N, num_classes) pre-softmax class scores
        penultimate_avs:     (N, D) penultimate layer activations
        mavs_penultimate:    dict {cls: mav_vector} from penultimate space
        weibull_params:      dict {cls: (shape, loc, scale)} fitted on penultimate distances
        alpha_rank:          number of top classes to revise
        num_classes:         number of known classes
        distance_type:       "cosine" or "euclidean"

    Returns:
        predictions: (N,) — num_classes means "unknown"
        probabilities: (N, num_classes+1)
    """
    N = logits.shape[0]
    D_pen = penultimate_avs.shape[1]
    all_probs = np.zeros((N, num_classes + 1), dtype=np.float64)

    # Build MAV matrix for penultimate space
    mav_matrix = np.zeros((num_classes, D_pen), dtype=np.float64)
    wb_shapes = np.zeros(num_classes, dtype=np.float64)
    wb_scales = np.zeros(num_classes, dtype=np.float64)
    wb_valid = np.zeros(num_classes, dtype=bool)

    for cls in range(num_classes):
        if cls in mavs_penultimate:
            mav_matrix[cls] = mavs_penultimate[cls]
        if weibull_params.get(cls) is not None:
            wb_shapes[cls] = weibull_params[cls][0]
            wb_scales[cls] = weibull_params[cls][2]
            wb_valid[cls] = True

    for start in range(0, N, batch_size):
        end = min(start + batch_size, N)
        log_batch = logits[start:end].astype(np.float64)       # (B, num_classes)
        pen_batch = penultimate_avs[start:end].astype(np.float64)  # (B, D_pen)
        B = log_batch.shape[0]

        # Rank by logit magnitude (which classes does the model think this is?)
        ranked = np.argsort(log_batch, axis=1)[:, ::-1]  # (B, num_classes)

        rank_alpha = np.zeros((B, num_classes), dtype=np.float64)
        for j in range(min(alpha_rank, num_classes)):
            cls_indices = ranked[:, j]
            weight = (alpha_rank + 1 - (j + 1)) / alpha_rank
            rank_alpha[np.arange(B), cls_indices] = weight

        # Distances in PENULTIMATE space
        if distance_type == "cosine":
            dot = pen_batch @ mav_matrix.T
            norms_pen = np.linalg.norm(pen_batch, axis=1, keepdims=True)
            norms_mav = np.linalg.norm(mav_matrix, axis=1, keepdims=True).T
            denom = np.maximum(norms_pen * norms_mav, 1e-10)
            dists = 1.0 - dot / denom
        else:
            dists = np.linalg.norm(
                pen_batch[:, None, :] - mav_matrix[None, :, :], axis=2
            )

        # Weibull CDF → omega (revision weights)
        omega = np.ones((B, num_classes), dtype=np.float64)
        for cls in range(num_classes):
            if not wb_valid[cls]:
                continue
            scale = max(wb_scales[cls], 1e-10)
            weibull_cdf = 1.0 - np.exp(-((dists[:, cls] / scale) ** wb_shapes[cls]))
            omega[:, cls] = 1.0 - rank_alpha[:, cls] * weibull_cdf

        # Recalibrate LOGITS (not penultimate features)
        recalibrated = log_batch * omega
        unknown_activation = np.sum(log_batch * (1.0 - omega), axis=1, keepdims=True)

        # Softmax over [recalibrated known, unknown]
        all_acts = np.concatenate([recalibrated, unknown_activation], axis=1)
        all_acts -= all_acts.max(axis=1, keepdims=True)
        exp_acts = np.exp(all_acts)
        probs = exp_acts / exp_acts.sum(axis=1, keepdims=True)

        all_probs[start:end] = probs

    predictions = np.argmax(all_probs, axis=1)
    return predictions, all_probs


# ═══════════════════════════════════════════════════════════════════════════════
# SOFTMAX THRESHOLD (MSP baseline)
# ═══════════════════════════════════════════════════════════════════════════════

def softmax_threshold_predict(softmax_probs, threshold, num_classes):
    """
    Maximum Softmax Probability (MSP) baseline for open-set detection.

    If the model's max confidence is below `threshold`, classify as unknown.
    Simple but effective — standard baseline in open-set recognition literature.

    Args:
        softmax_probs:  (N, num_classes) softmax output from classifier
        threshold:      confidence threshold (e.g. 0.78)
        num_classes:    number of known classes

    Returns:
        predictions: (N,) — num_classes means "unknown"
        probabilities: (N, num_classes+1) with unknown column appended
    """
    probs = softmax_probs.astype(np.float64)
    max_conf = probs.max(axis=1)
    predictions = np.argmax(probs, axis=1)

    # Below threshold → unknown
    predictions[max_conf < threshold] = num_classes

    # Build probability vector with unknown column
    unknown_prob = np.clip(1.0 - max_conf, 0, 1).reshape(-1, 1)
    full_probs = np.concatenate([probs, unknown_prob], axis=1)
    # Renormalize
    full_probs /= full_probs.sum(axis=1, keepdims=True)

    return predictions, full_probs


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY: Sweep thresholds for MSP
# ═══════════════════════════════════════════════════════════════════════════════

def sweep_msp_thresholds(softmax_known, y_true_known, softmax_unknown,
                         num_classes, thresholds=None):
    """
    Sweep MSP thresholds and return a DataFrame of results.

    Args:
        softmax_known:    (N_k, num_classes) softmax probs for known test set
        y_true_known:     (N_k,) true labels for known test set
        softmax_unknown:  (N_u, num_classes) softmax probs for unknown test set
        num_classes:      number of known classes
        thresholds:       list of thresholds to try (default: 0.50 to 0.99)

    Returns:
        list of dicts with keys: threshold, known_acc, unknown_det, h_score
    """
    if thresholds is None:
        thresholds = np.arange(0.50, 1.00, 0.02)

    max_conf_known = softmax_known.max(axis=1)
    max_conf_unknown = softmax_unknown.max(axis=1)

    results = []
    for th in thresholds:
        pred_k = np.argmax(softmax_known, axis=1)
        pred_k[max_conf_known < th] = num_classes
        ka = np.mean((pred_k != num_classes) & (pred_k == y_true_known))
        ud = np.mean(max_conf_unknown < th)
        hs = 2 * ka * ud / (ka + ud) if (ka + ud) > 0 else 0
        results.append({
            "threshold": round(float(th), 2),
            "known_acc": round(float(ka), 4),
            "unknown_det": round(float(ud), 4),
            "h_score": round(float(hs), 4),
        })
    return results
