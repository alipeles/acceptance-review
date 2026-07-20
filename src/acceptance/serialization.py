"""Byte-stable serialization.

One definition of "canonical" shared by the transcript store (M0.4) and
persisted review state (M0.5): sorted keys and tight separators, so identical
data serializes to identical bytes across runs, processes, and tool versions.
This is what makes M0.5's "two recorded runs produce byte-identical review
state" a property of the format, not an accident of dict insertion order.
"""

from __future__ import annotations

import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
