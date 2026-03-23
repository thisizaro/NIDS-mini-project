"""
OpenMax algorithm for open-set recognition in NIDS.
Based on Algorithm 1 & 2 from: "Unknown intrusion traffic detection method
based on unsupervised learning and open-set recognition"
(Fang & Xie, 2025, Nature Scientific Reports)

OpenMax replaces the SoftMax layer to introduce an "unknown" class probability
using Extreme Value Theory (Weibull distribution fitting on activation vector tails).

Key concepts:
  - Activation Vector (AV): output of penultimate layer (before softmax)
  - Mean Activation Vector (MAV): mean AV for each known class
  - Weibull fitting: fit tail distances between AVs and their class MAV
  - Recalibration: adjust known class probabilities, add unknown class
"""

import numpy as np
from scipy.spatial.distance import cosine as cosine_distance
from scipy.stats import exponweib


def compute_mavs(activation_vectors, labels, num_classes):
    """
    Compute Mean Activation Vectors (MAV) for each class.

    Args:
        activation_vectors: (N, D) array of penultimate layer activations
        labels: (N,) array of integer class labels
        num_classes: number of known classes

    Returns:
        mavs: dict {class_idx: mean_activation_vector}
        class_avs: dict {class_idx: list of activation vectors}
    """
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
    """
    Compute distances between each sample's AV and its class MAV.

    Args:
        class_avs: dict {class_idx: (N_cls, D) array}
        mavs: dict {class_idx: (D,) array}
        distance_type: "cosine" or "euclidean"

    Returns:
        distances: dict {class_idx: (N_cls,) array of distances}
    """
    distances = {}
    for cls in class_avs:
        mav = mavs[cls]
        avs = class_avs[cls]
        if distance_type == "cosine":
            dists = np.array([cosine_distance(av, mav) for av in avs])
        else:  # euclidean
            dists = np.linalg.norm(avs - mav, axis=1)
        distances[cls] = dists
    return distances


def fit_weibull(distances, tail_size):
    """
    Fit Weibull distribution to the tail of distances for each class.
    (Algorithm 2: FitHigh)

    Args:
        distances: dict {class_idx: (N_cls,) array of distances}
        tail_size: number of largest distances to use for fitting (eta)

    Returns:
        weibull_params: dict {class_idx: (shape, loc, scale)} Weibull parameters
    """
    weibull_params = {}

    for cls, dists in distances.items():
        # Sort descending, take tail_size largest distances
        sorted_dists = np.sort(dists)[::-1]
        tail = sorted_dists[:min(tail_size, len(sorted_dists))]

        if len(tail) < 3:
            # Not enough data to fit
            weibull_params[cls] = None
            continue

        try:
            # Fit Weibull distribution (exponweib with a=1 is standard Weibull)
            shape, loc, scale = exponweib.fit(tail, floc=0, f0=1)
            weibull_params[cls] = (shape, loc, scale)
        except Exception:
            weibull_params[cls] = None

    return weibull_params


def openmax_recalibrate(activation_vector, mavs, weibull_params,
                         alpha_rank, num_classes, distance_type="cosine"):
    """
    OpenMax recalibration (Algorithm 1).

    Adjusts the activation vector of known classes using Weibull CDF,
    and introduces an unknown class activation.

    Args:
        activation_vector: (D,) single sample's penultimate activations
        mavs: dict of MAVs per class
        weibull_params: dict of Weibull params per class
        alpha_rank: number of top classes to recalibrate
        num_classes: number of known classes
        distance_type: "cosine" or "euclidean"

    Returns:
        openmax_probs: (num_classes+1,) probability vector
                       (last element = unknown class probability)
    """
    # Get softmax scores from the activation vector
    # (these are the raw penultimate activations, not softmax outputs)
    # We sort by activation magnitude to find the top-alpha classes
    ranked_classes = np.argsort(activation_vector)[::-1]

    # Compute rank-based alpha weights (Eq. in Algorithm 1, line 8-10)
    rank_alpha = np.zeros(num_classes)
    for j in range(num_classes):
        if j < alpha_rank:
            rank_alpha[ranked_classes[j]] = (alpha_rank + 1 - (j + 1)) / alpha_rank
        else:
            rank_alpha[ranked_classes[j]] = 0.0

    # Compute Weibull CDF for each class (omega values)
    omega = np.zeros(num_classes)
    for cls in range(num_classes):
        if cls not in mavs or weibull_params.get(cls) is None:
            continue

        mav = mavs[cls]
        if distance_type == "cosine":
            dist = cosine_distance(activation_vector, mav)
        else:
            dist = np.linalg.norm(activation_vector - mav)

        shape, loc, scale = weibull_params[cls]
        # CDF of Weibull: probability that distance is <= observed distance
        omega[cls] = 1.0 - rank_alpha[cls] * (1.0 - np.exp(-((dist / scale) ** shape)))

    # Recalibrate activation vectors (line 14-15 in Algorithm 1)
    recalibrated = activation_vector.copy()
    unknown_activation = 0.0

    for cls in range(num_classes):
        recalibrated[cls] = activation_vector[cls] * omega[cls]
        unknown_activation += activation_vector[cls] * (1.0 - omega[cls])

    # Compute probabilities with the unknown class (line 18-19)
    # Append unknown activation and apply softmax
    all_activations = np.append(recalibrated[:num_classes], unknown_activation)

    # Softmax
    exp_av = np.exp(all_activations - np.max(all_activations))
    openmax_probs = exp_av / exp_av.sum()

    return openmax_probs


def openmax_predict(activation_vectors, mavs, weibull_params,
                    alpha_rank, num_classes, distance_type="cosine"):
    """
    Apply OpenMax to a batch of activation vectors.

    Args:
        activation_vectors: (N, D) array
        mavs, weibull_params: from fit_weibull
        alpha_rank: number of top classes to recalibrate
        num_classes: number of known classes
        distance_type: "cosine" or "euclidean"

    Returns:
        predictions: (N,) predicted class indices (num_classes = unknown)
        probabilities: (N, num_classes+1) OpenMax probability vectors
    """
    N = len(activation_vectors)
    probabilities = np.zeros((N, num_classes + 1))

    for i in range(N):
        probabilities[i] = openmax_recalibrate(
            activation_vectors[i], mavs, weibull_params,
            alpha_rank, num_classes, distance_type
        )

    predictions = np.argmax(probabilities, axis=1)
    return predictions, probabilities
