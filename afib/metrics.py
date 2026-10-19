"""The final CinC 2017 metric (paper equation 1, not the old webpage)."""

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score

LABELS = ("N", "A", "O", "~")
LABEL_NAMES = {"N": "Normal", "A": "AFib", "O": "Other rhythm", "~": "Noisy"}


def official_f1(y_true, y_pred):
    """Average N/A/O F1, retaining noisy observations in FP/FN counts."""
    if len(y_true) != len(y_pred) or len(y_true) == 0:
        raise ValueError("Labels must have equal, nonzero length")
    if not set(y_true).union(y_pred).issubset(LABELS):
        raise ValueError("Unknown class label")
    return float(
        f1_score(y_true, y_pred, labels=list(LABELS[:3]), average="macro", zero_division=0)
    )


def evaluate(y_true, y_pred):
    """Return JSON-compatible full four-class evaluation."""
    return {
        "official_mean_f1": official_f1(y_true, y_pred),
        "per_class": classification_report(
            y_true, y_pred, labels=list(LABELS), output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(LABELS)).tolist(),
        "label_order": list(LABELS),
        "n_test": int(np.size(y_true)),
    }
