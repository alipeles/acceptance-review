"""Semantic obligation alignment for §11.1 scoring (#118).

The benchmark metrics (scoring.py) join reviewer output to ground truth by
obligation *description*. A real `decompose` run produces semantically-correct
criteria whose wording never matches the human-authored ground truth verbatim
("Use monthly_price / days_in_month as the daily rate" vs "Daily rate is
monthly_price divided by days_in_month"), so an exact-string join scores ~0 for
a perfect decomposition.

This aligns reviewer criteria to the ground-truth criteria they describe the
same requirement as, via a schema-constrained model judgment (LLM-as-judge) —
robust to paraphrase where a string compare is not, and deterministic in tests
through the M0.4 replay harness. The alignment is bijective (each side matched
at most once, enforced greedily), so an over-decomposed extra criterion is left
unmatched and correctly costs precision.

This is benchmark *measurement* infrastructure — it runs against known ground
truth, not in the product's own review path.

One exception, and it is why `stage` is a parameter rather than a constant here:
`requirement/carry.py` reuses this function to match a reworded requirement to
the prior run's wording. That call is part of a review, so its spend has to be
attributed like any other (#264), and only the caller knows which stage it
belongs to. A benchmark caller passes nothing and stays out of the review's
per-stage footer, which is where it belongs.
"""

from __future__ import annotations

from acceptance.llm import ModelClient, StrictResponseModel

_SYSTEM_PROMPT = """\
You align two lists of acceptance criteria: GROUND TRUTH (human-authored) and
REVIEWER (produced by a tool). Match each reviewer criterion to the ONE
ground-truth criterion that states the SAME requirement — the same behavior or
rule, even if worded differently. Not every criterion has a match; leave
unmatched ones out. Each ground-truth criterion and each reviewer criterion may
appear in at most one match.

Match on the underlying requirement, not surface wording. Do NOT match two
criteria that concern different rules just because they mention the same nouns.

Return the matches as pairs of the given labels (e.g. ground_truth "g0",
reviewer "r2")."""


class _LabelMatch(StrictResponseModel):
    ground_truth: str
    reviewer: str


class _Alignment(StrictResponseModel):
    matches: list[_LabelMatch]


def _render_prompt(gt_labels: dict[str, str], rv_labels: dict[str, str]) -> str:
    lines = ["## Ground-truth criteria", ""]
    for label, desc in gt_labels.items():
        lines.append(f"[{label}] {desc}")
    lines.append("")
    lines.append("## Reviewer criteria")
    for label, desc in rv_labels.items():
        lines.append(f"[{label}] {desc}")
    return "\n".join(lines)


def align_obligations(
    ground_truth_descriptions: list[str],
    reviewer_descriptions: list[str],
    client: ModelClient,
    stage: str | None = None,
) -> dict[str, str]:
    """Return a `reviewer_description -> ground_truth_description` map for
    semantically-equivalent criteria (a bijection over the matched subset)."""
    if not ground_truth_descriptions or not reviewer_descriptions:
        return {}

    gt_labels = {f"g{i}": desc for i, desc in enumerate(ground_truth_descriptions)}
    rv_labels = {f"r{i}": desc for i, desc in enumerate(reviewer_descriptions)}

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _render_prompt(gt_labels, rv_labels)},
    ]
    result = client.complete(messages, _Alignment, stage=stage)

    alignment: dict[str, str] = {}
    used_gt: set[str] = set()
    used_rv: set[str] = set()
    for match in result.matches:
        if (
            match.ground_truth in gt_labels
            and match.reviewer in rv_labels
            and match.ground_truth not in used_gt
            and match.reviewer not in used_rv
        ):
            alignment[rv_labels[match.reviewer]] = gt_labels[match.ground_truth]
            used_gt.add(match.ground_truth)
            used_rv.add(match.reviewer)
    return alignment
