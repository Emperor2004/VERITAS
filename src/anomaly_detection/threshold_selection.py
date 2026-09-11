"""
Automatic threshold/contamination selection for the anomaly detector.

IsolationForest's `contamination` parameter only controls where the binary
anomaly/normal cutoff sits on top of already-computed anomaly scores -- it
does not change the scores themselves (decision_function/score_samples are
contamination-independent in sklearn's implementation; only the internal
predict() threshold, `offset_`, depends on it). That means the right way to
"tune contamination" is not to refit the forest repeatedly with different
values, but to fit once and choose where to cut the resulting score curve.

Two strategies are provided:

1. select_threshold_knee -- fully unsupervised. Finds the point of maximum
   curvature ("knee") in the sorted anomaly-score curve. This is the
   generalizable, label-free method and the one to use on real, unlabeled
   industry data. It's an algorithmic, reproducible version of what
   "trial and error" is usually actually approximating: eyeballing a score
   histogram for a natural break point.

2. select_threshold_grid_search -- supervised, using ground truth. Only
   usable here because phase 1 deliberately injected a labeled operational
   anomaly rate. This will converge near that injection rate almost by
   construction. It exists to validate that the unsupervised method above
   lands in a sane neighborhood on this dataset -- NOT to be presented as
   a general threshold-selection technique, since real deployments will
   not have this label available.
"""
from __future__ import annotations
import numpy as np
from sklearn.metrics import f1_score


def select_threshold_knee(anomaly_scores: np.ndarray) -> dict:
    """Classic knee/elbow detection: find the point of maximum perpendicular
    distance from the chord connecting the first and last point of the
    sorted score curve. Returns the score cutoff and resulting count."""
    sorted_scores = np.sort(anomaly_scores)
    n = len(sorted_scores)

    x = np.arange(n)
    x_norm = (x - x.min()) / (x.max() - x.min() + 1e-12)
    y_norm = (sorted_scores - sorted_scores.min()) / (sorted_scores.max() - sorted_scores.min() + 1e-12)

    p1 = np.array([x_norm[0], y_norm[0]])
    p2 = np.array([x_norm[-1], y_norm[-1]])
    line_vec = p2 - p1
    line_vec_norm = line_vec / (np.linalg.norm(line_vec) + 1e-12)

    points = np.stack([x_norm, y_norm], axis=1) - p1
    proj_len = points @ line_vec_norm
    proj_points = np.outer(proj_len, line_vec_norm)
    perp = points - proj_points
    distances = np.linalg.norm(perp, axis=1)

    knee_idx = int(np.argmax(distances))
    n_anomalies = int(n - knee_idx)

    return {
        "method": "knee",
        "cutoff_score": float(sorted_scores[knee_idx]),
        "contamination": round(n_anomalies / n, 4),
        "n_flagged": n_anomalies,
        "note": (
            "Unsupervised, label-free threshold derived from the shape of this "
            "run's own score distribution. This is the method to use on real, "
            "unlabeled production data."
        ),
    }


def select_threshold_grid_search(anomaly_scores: np.ndarray, ground_truth: np.ndarray,
                                  candidate_contaminations: list | None = None) -> dict:
    """Supervised validation only -- see module docstring. Grid-searches
    contamination values and picks the one maximizing F1 against the
    injected ground truth label."""
    if candidate_contaminations is None:
        candidate_contaminations = [round(c, 3) for c in np.arange(0.005, 0.15, 0.005)]

    n = len(anomaly_scores)
    sorted_desc_idx = np.argsort(-anomaly_scores)  # most anomalous first

    best = {"contamination": None, "f1": -1.0, "n_flagged": 0, "cutoff_score": None}
    for c in candidate_contaminations:
        k = max(1, int(round(c * n)))
        y_pred = np.zeros(n, dtype=bool)
        y_pred[sorted_desc_idx[:k]] = True
        f1 = f1_score(ground_truth, y_pred, zero_division=0)
        if f1 > best["f1"]:
            cutoff = float(anomaly_scores[sorted_desc_idx[k - 1]])
            best = {"contamination": c, "f1": round(float(f1), 4), "n_flagged": k, "cutoff_score": cutoff}

    best["method"] = "grid_search_supervised"
    best["warning"] = (
        "This threshold was tuned against injected ground truth and will trivially "
        "converge near the phase-1 injection rate. Do not present this as a "
        "general contamination value -- it is a validation check, not a "
        "production threshold-selection method."
    )
    return best