"""Fixed operating-point object-detection matching (not classification accuracy)."""
from __future__ import annotations
import math


def overlap(a, b):
    x = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    y = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = x * y
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def match(predictions, truths, threshold=0.5):
    """Confidence-descending, class-aware, one-to-one greedy IoU matching.

    A duplicate prediction cannot match a truth twice. No true negatives are
    defined for boxes; empty denominators are null, not fabricated 100% scores.
    """
    used = set()
    matched = []
    for prediction in sorted(predictions, key=lambda item: -item["confidence"]):
        if not math.isfinite(prediction["confidence"]):
            raise ValueError("Non-finite prediction")
        candidates = [(overlap(prediction["box"], truth["box"]), index) for index, truth in enumerate(truths)
                      if index not in used and truth["classId"] == prediction["classId"]]
        score, index = max(candidates, default=(0.0, -1))
        correct = index >= 0 and score >= threshold
        if correct:
            used.add(index)
        matched.append({**prediction, "correct": correct, "matchedIou": score if correct else None})
    tp = len(used)
    fp, fn = len(predictions) - tp, len(truths) - tp
    return {"truthCount": len(truths), "predictionCount": len(predictions), "tp": tp, "fp": fp, "fn": fn,
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn), "predictions": matched}
