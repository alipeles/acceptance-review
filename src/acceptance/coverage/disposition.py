"""Separability classification for unrequested changes (M3.5.3, §9.2, DR-081).

Every unrequested change (detected by unrequested.py) gets a **disposition** —
how a reviewer should treat it:

- `in_service`  — needed to deliver an obligation (a refactor/helper the
  requested work depends on), even though nothing asked for it directly.
  Removing it would leave an obligation incomplete.
- `separable`   — coherent, self-contained work, valuable but distinct; belongs
  in its own PR / backlog item. Removing it leaves every obligation complete.
- `risky`       — edits existing public interface, dependencies, or adjacent
  behavior in a way that could hide a regression. Scrutinize.

The classifier is a **hybrid** (chosen deliberately, not for cheapness):

1. Deterministic fast-paths for the unambiguous cases, using judgments already
   produced upstream — no new model call:
   - the change's region overlaps a region the M3.1 coverage classifier marked
     `addressed` for some obligation → the obligation's implementation lives
     there → **in_service**. (This is the two-axis reconciliation from #85: a
     coverage-mapped region is never a bare unrequested flag.) Only `addressed`
     counts — a `partially_addressed` region can be the one that *violates* a
     leave-as-is obligation, which is ambiguous and escalates.
   - a pure new-file addition that no obligation's coverage claims → new,
     self-contained work → **separable**.
2. Everything else — edits to existing code with no clean coverage attribution —
   is the genuinely ambiguous case (indirect dependency? distinct work?
   regression risk?), so it escalates to a schema-constrained model judgment
   through the M0.4 harness (recorded for replay).

Known limitation (documented, not silently accepted): the deterministic
in_service path only sees *direct* coverage overlap, and the pure-addition path
can't tell a genuinely independent new file from a new load-bearing helper that
a requested feature imports. Both residual cases are indirect dependencies; a
call-graph reach analysis (M2.2 machinery) would tighten them. The model path
covers the modifies-existing ambiguity, which is the bulk of the hard cases.

Detection stays recall-forward (DR-081 dec. 3): an in_service change is still a
correctly *detected* unrequested change and still a Finding — the disposition
governs how it is *treated*, not whether it was found.
"""

from __future__ import annotations

from typing import Literal

from acceptance.config import ScopeExpansionPolicy
from acceptance.coverage.classify import CoverageStatus, ImplementationCoverage
from acceptance.coverage.prompt import DiffRef
from acceptance.coverage.unrequested import UnrequestedChange
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import ChangeSet, Obligation, UnrequestedChangeDisposition

_SPLIT_RECOMMENDATION = (
    "Consider splitting this into its own PR / backlog item — it is separable "
    "from the mandate."
)
_SCRUTINIZE_RECOMMENDATION = (
    "Scrutinize: this edits existing public/adjacent behavior and could hide a "
    "regression."
)

_RECOMMENDATION = {
    UnrequestedChangeDisposition.SEPARABLE: _SPLIT_RECOMMENDATION,
    UnrequestedChangeDisposition.RISKY: _SCRUTINIZE_RECOMMENDATION,
    UnrequestedChangeDisposition.IN_SERVICE: None,
}


class DispositionedChange(PersistableModel):
    """An unrequested change with its disposition, why, and how it was decided."""

    change: UnrequestedChange
    disposition: UnrequestedChangeDisposition
    rationale: str
    recommendation: str | None = None
    decided_by: Literal["structural", "model"] = "structural"


_SYSTEM_PROMPT = """\
You classify one UNREQUESTED code change — a change no listed obligation called
for — into exactly one disposition, using the removability litmus:

  Would EVERY obligation still be satisfied if this change were removed?

- in_service: NO — some obligation depends on this change (e.g. a refactor or
  helper the requested feature needs), even though nothing requested it
  directly. Removing it would leave an obligation incomplete.
- separable: YES, and it is coherent, self-contained work — valuable but a
  DISTINCT unit that belongs in its own PR / backlog item.
- risky: YES, but it edits existing public interface, dependencies, or adjacent
  behavior in a way that could hide a regression. Scrutinize.

Policy knob: under a STRICT scope-expansion policy, treat an edit to existing
adjacent behavior as `risky`; under a LOOSE policy, treat it as merely
`separable`. Load-bearing changes are `in_service` and public-interface or
dependency edits are `risky` under BOTH policies.

Return the `disposition` and a short `rationale`."""


class _DispositionJudgment(StrictResponseModel):
    disposition: UnrequestedChangeDisposition
    rationale: str


def _region_key(ref: DiffRef) -> tuple[str, str]:
    return (ref.file, ref.hunk_header)


def _addressed_regions(coverages: list[ImplementationCoverage]) -> set[tuple[str, str]]:
    return {
        _region_key(ref)
        for coverage in coverages
        if coverage.status == CoverageStatus.ADDRESSED
        for ref in coverage.diff_refs
    }


def _is_load_bearing(change: UnrequestedChange, addressed: set[tuple[str, str]]) -> bool:
    return any(_region_key(ref) in addressed for ref in change.diff_refs)


def _is_pure_addition(change: UnrequestedChange, change_set: ChangeSet) -> bool:
    if not change.diff_refs:
        return False
    status_by_path = {f.path: f.status for f in change_set.files}
    return all(status_by_path.get(ref.file) == "added" for ref in change.diff_refs)


def _dispositioned(
    change: UnrequestedChange,
    disposition: UnrequestedChangeDisposition,
    rationale: str,
    decided_by: Literal["structural", "model"],
) -> DispositionedChange:
    return DispositionedChange(
        change=change,
        disposition=disposition,
        rationale=rationale,
        recommendation=_RECOMMENDATION[disposition],
        decided_by=decided_by,
    )


def _render_judgment_prompt(
    change: UnrequestedChange,
    obligations: list[Obligation],
    coverages: list[ImplementationCoverage],
    change_set: ChangeSet,
    policy: ScopeExpansionPolicy,
) -> str:
    status_by_id = {c.obligation_id: c.status.value for c in coverages}
    lines = [f"Scope-expansion policy: {policy.value}", "", "## Obligations (with coverage)"]
    for obligation in obligations:
        status = status_by_id.get(obligation.id, "unclassified")
        lines.append(f"- id={obligation.id} [{status}]: {obligation.description}")
    lines.append("")
    lines.append("## Unrequested change under review")
    lines.append(f"kind={change.kind.value}; rationale={change.rationale}")
    lines.append("")
    lines.append("### Changed hunks")
    hunk_by_key = {
        (f.path, hunk.header): hunk for f in change_set.files for hunk in f.hunks
    }
    for ref in change.diff_refs:
        status = next((f.status for f in change_set.files if f.path == ref.file), "?")
        lines.append(f"[{ref.file} ({status})] {ref.hunk_header}")
        hunk = hunk_by_key.get((ref.file, ref.hunk_header))
        if hunk is not None:
            lines.append(hunk.content)
    return "\n".join(lines)


def _judge_disposition(
    change: UnrequestedChange,
    obligations: list[Obligation],
    coverages: list[ImplementationCoverage],
    change_set: ChangeSet,
    policy: ScopeExpansionPolicy,
    client: ModelClient,
) -> DispositionedChange:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _render_judgment_prompt(change, obligations, coverages, change_set, policy),
        },
    ]
    result = client.complete(messages, _DispositionJudgment)
    return _dispositioned(change, result.disposition, result.rationale, decided_by="model")


def classify_dispositions(
    changes: list[UnrequestedChange],
    obligations: list[Obligation],
    coverages: list[ImplementationCoverage],
    change_set: ChangeSet,
    policy: ScopeExpansionPolicy,
    client: ModelClient,
) -> list[DispositionedChange]:
    """Classify each unrequested change's disposition (hybrid: deterministic
    fast-paths, model judgment for the ambiguous rest)."""
    addressed = _addressed_regions(coverages)
    results: list[DispositionedChange] = []
    for change in changes:
        if _is_load_bearing(change, addressed):
            results.append(
                _dispositioned(
                    change,
                    UnrequestedChangeDisposition.IN_SERVICE,
                    "The change's region is where an obligation is addressed; it is "
                    "load-bearing for that obligation.",
                    decided_by="structural",
                )
            )
        elif _is_pure_addition(change, change_set):
            results.append(
                _dispositioned(
                    change,
                    UnrequestedChangeDisposition.SEPARABLE,
                    "A self-contained addition in newly added file(s) that no "
                    "obligation's coverage claims.",
                    decided_by="structural",
                )
            )
        else:
            results.append(
                _judge_disposition(change, obligations, coverages, change_set, policy, client)
            )
    return results
