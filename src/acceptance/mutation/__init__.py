"""Targeted mutation: inject one named plausible defect and see who notices.

The review has already named, for each obligation, the concrete ways the change
could fail it. Until this package existed those names were only ever judged by
reading — a prediction about whether each candidate test would catch each
defect. Here the prediction is replaced by an observation: build the smallest
edit that makes the defect true, run the candidate tests against an altered copy
of the project, and record which of them went red.

`docs/DR-171-mutation-targeting.md` is the design, as revised 2026-09-14. Three
of its decisions shape every module here:

- **Decision 4.** The mutant runs against *every* candidate test. Which tests go
  red is the mapping; nothing selects beforehand, because the only cheap
  selector measured (line coverage) missed 43 of 268 recorded kills.
- **Decision 7.** This runs *before* the static pair judgement, which then sees
  only what execution could not settle. Injection replaces that judgement where
  it reaches, rather than correcting it afterwards.
- **Decision 8.** Every attempt carries a typed outcome, and the two that settle
  nothing carry a reason. A defect nothing can see is indistinguishable from one
  that survived.
"""

from __future__ import annotations

from acceptance.mutation.attempt import (
    MutationAttempt,
    MutationDescriptor,
    MutationOutcomeKind,
)
from acceptance.mutation.region import Region, regions_for

__all__ = [
    "MutationAttempt",
    "MutationDescriptor",
    "MutationOutcomeKind",
    "Region",
    "regions_for",
]
