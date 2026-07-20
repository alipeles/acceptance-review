"""Review-state stub.

Provisional placeholder for the §15 data model. M0.2 replaces this with the
full typed schemas (Obligation, Finding with enforced evidence tier, etc.);
until then this only exists so M0.1's CLI has a named structured object to
return instead of an ad hoc dict.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Review:
    mode: str
    reviewed_revision: str
    mandate: Any = None
    declaration: Any = None
    change_set: Any = None
    obligation_map: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    evidence_tiers: dict = field(default_factory=dict)
    limitations: list = field(default_factory=list)
    recommendation: Any = None

    def to_dict(self) -> dict:
        return asdict(self)
