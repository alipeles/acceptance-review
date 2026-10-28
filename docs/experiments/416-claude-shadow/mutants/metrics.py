"""The metrics #379's findings table reports, for one arm's verdicts.

Accuracy counts a missing verdict as wrong, as ``score_heldout.py::summary``
does. Precision and recall are over cases that got a verdict; "fails" is the
positive class (the mutant was killed).
"""

from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(mid - half, 3), round(mid + half, 3)]


def _ratio(a: int, b: int):
    return round(a / b, 3) if b else None


def summary(said: list[bool | None], y: list[bool], cost_total: float | None = None) -> dict:
    n = len(y)
    pairs = list(zip(said, y, strict=True))
    tp = sum(s is True and t for s, t in pairs)
    fp = sum(s is True and not t for s, t in pairs)
    tn = sum(s is False and not t for s, t in pairs)
    fn = sum(s is False and t for s, t in pairs)
    out = {
        "accuracy": round((tp + tn) / n, 3),
        "accuracy_95pct_interval": wilson(tp + tn, n),
        "precision_on_fails": _ratio(tp, tp + fp),
        "precision_on_fails_95pct_interval": wilson(tp, tp + fp) if tp + fp else None,
        "recall_on_fails": _ratio(tp, tp + fn),
        "precision_on_survives": _ratio(tn, tn + fn),
        "recall_on_survives": _ratio(tn, tn + fp),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "no_verdict": sum(s is None for s in said),
    }
    if cost_total is not None:
        out["cost_per_case"] = round(cost_total / n, 5)
    return out
