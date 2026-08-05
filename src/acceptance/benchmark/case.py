"""Benchmark-case schema (§15 Benchmark case, §11.1 metrics; M-B0.1, revised M-B5a.2).

A case pairs a real (or offline-mutated, or hand-curated) input with
human-verified ground truth, so the checker's output can be scored against
it.

The ground truth is an **obligation tree**: the obligation is the spine
(CLAUDE.md — "obligations are the spine everything maps to"), and each one
carries its own stable `id`, the tests relevant to it (`candidate_tests`), how
strong that evidence is (`evidence_class`, a §9.3 class), and why
(`evidence_rationale`). `gaps` are the findings a good reviewer should raise,
each linked to the obligation it concerns. This mirrors exactly the tree the
tool must show a user — obligation -> candidate tests -> evidence strength (with
a reason) — and makes the §11.1 metrics fall out of it:

    obligations                 -> obligation-decomposition accuracy
    obligation.candidate_tests  -> test-to-obligation mapping accuracy
    obligation.evidence_class   -> evidence-classification agreement
    gaps                        -> gap-detection recall / false-alarm precision

Identifiers, not prose, are the join keys: `obligation_id` on a gap and the
test ids in `candidate_tests` are validated to resolve, so ground truth can't
carry a dangling reference, an obligation with no evidence class, or a weak
result with no stated reason.

`unrequested_changes` is the code→obligation dual of `gaps` (a gap is an
obligation with no matching code; an unrequested change is code with no
matching obligation) and is therefore obligation-*less* by construction —
scored as its own precision/recall pair (DR-081), never folded into the gap
metric (M3.5.1). Each carries a required `disposition` (M3.5.4): in_service /
separable / risky, human-labeled the same way `evidence_class` is.

`reviewer_output` and `score` start empty and are filled in by the runner
(M-B0.2) and scorer (M-B0.3) — a case is valid the moment it carries real
ground truth, before it has ever been run.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from acceptance.model_base import PersistableModel
from acceptance.review_state import (
    EvidenceClassification,
    ObligationType,
    Review,
    UnrequestedChangeDisposition,
)

# EvidenceClassification (§9.3 strength classes) is defined in review_state.py so
# the checker (evidence/strength.py, M5.3) and the benchmark both use it without
# the checker depending on this benchmark module. Used by the ground-truth models
# below (GroundTruthObligation.evidence_class).


class BenchmarkCaseSource(PersistableModel):
    kind: Literal["dataset", "real_pr", "mutant", "agent_run", "archetype"]
    identifier: str


class BenchmarkCaseInputs(PersistableModel):
    """What the checker-under-test runner (M-B0.2) feeds to the checker."""

    repo: str
    task_text: str
    base_revision: str
    head_revision: str
    declaration_text: str | None = None


class GroundTruthObligation(PersistableModel):
    """One obligation in the expected decomposition, with the tests a reviewer
    would examine for it, its evidence strength, and why — a node in the
    obligation tree.

    `candidate_tests` are the tests relevant to this obligation (§9.1 "candidate
    tests"); a test can be a candidate yet establish nothing (mocked, circular,
    non-discriminating), which is exactly what `evidence_class` records.
    `evidence_rationale` states *why* the class is what it is — required so a
    weak or negative result can never appear without an explanation (§13.6).

    `expected_type` is the `ObligationType` a correct decomposition gives this
    obligation, and is the one field here that scores the *decompose* stage
    rather than what came after it (#195). Optional because it is knowable only
    where a human has judged the type — the decompose-stability corpus does that
    for a handful of obligations and says nothing about the rest, and a case must
    be able to stay silent rather than invent a label. Silence is not agreement:
    an obligation with no `expected_type` contributes to no type metric at all.

    `required_symbols` are identifiers the task text names in this obligation's
    source and which the obligation must therefore still name (#195). Kept
    separate from `description` because it cannot ride on description matching:
    `align_obligations` matches on the underlying requirement and would happily
    align "Source statistics from `benchmark/scoring.py::disclose_variance`" to
    "The statistics come from the existing variance path" — they *are* the same
    requirement. That is the aligner working correctly, and it is exactly why a
    symbol dropped from an obligation is invisible to every set metric. An
    obligation that has discarded the one identifier in its source text gives the
    mapping stage strictly less to work with (#173)."""

    id: str
    description: str
    explicit: bool
    evidence_class: EvidenceClassification
    evidence_rationale: str
    candidate_tests: list[str] = Field(default_factory=list)  # test ids (pytest nodeids)
    expected_type: ObligationType | None = None
    required_symbols: list[str] = Field(default_factory=list)


class GroundTruthGap(PersistableModel):
    """A finding a good reviewer should raise. `obligation_id` links it to the
    obligation it concerns, or is None when the gap is not about a task
    obligation (e.g. a declaration overclaim the task never requested)."""

    id: str
    description: str
    obligation_id: str | None = None
    severity: str | None = None


class GroundTruthUnrequestedChange(PersistableModel):
    """A diff region the ground truth says no obligation calls for — the
    code→obligation dual of a gap (§9.2, DR-081). Obligation-less by
    construction, so it is *not* linked to an obligation id the way a
    `GroundTruthGap` can be.

    `file` identifies the diff region at file granularity (matching the
    checker's `Finding.links`, not an exact hunk header — a hand-authored
    exact hunk header would be brittle to keep in sync with the fixture's
    real diff). Coarser than line-level, but matches the granularity the
    existing gap metric already scores at (by obligation, not by line
    range).

    `disposition` is required (M3.5.4): every unrequested change in the
    ground truth is labeled in_service / separable / risky by a human, the
    same "no result without a reason" discipline `evidence_rationale`
    already enforces on obligations. Per-disposition scoring accuracy is
    deferred to Stage 2 (DR-081); the label exists now for human validation
    and to seed that future metric."""

    id: str
    description: str
    file: str
    disposition: UnrequestedChangeDisposition


class GroundTruthOpenQuestion(PersistableModel):
    """An open question a correct decomposition does — or does not — raise.

    Both directions are ground truth, and neither is the default (#195). A
    question the task file never answers *must* be raised, and dropping it is the
    tool silently converting "I don't know" into "nothing to see" — the failure
    this product exists to detect in others, and the one the decompose-stability
    corpus documents oscillating across seven runs. A question the task file
    already answers in another section *must not* be raised (#178); raising it is
    noise that a reader has to triage.

    So `should_be_raised` carries the label and `rationale` says why, under the
    same "no result without a reason" discipline as `evidence_rationale`. There
    is no third state: a question this corpus has no opinion about is simply
    absent from the ground truth and scored against nothing."""

    id: str
    description: str
    should_be_raised: bool
    rationale: str
    aliases: list[str] = Field(default_factory=list)

    def matches(self, question_id: str) -> bool:
        """Whether a reviewer's open-question id refers to this question.

        Id, not description: the decomposer names a question with a slug it
        chooses, and the corpus shows the same question arriving as different
        slugs across runs (`report-format`, `oq-output-format`). `aliases` holds
        the slugs actually observed, so matching is grounded in the corpus rather
        than in a guess about how a model will phrase things.

        This does NOT survive a decomposer that invents a slug the corpus has
        never seen — a real limitation, and the reason a semantic alignment for
        open questions is worth having (it does not exist yet;
        `align_obligations` is prompted for acceptance criteria and would be
        misapplied here)."""
        return question_id == self.id or question_id in self.aliases


class GroundTruthLabels(PersistableModel):
    obligations: list[GroundTruthObligation] = Field(default_factory=list)
    gaps: list[GroundTruthGap] = Field(default_factory=list)
    unrequested_changes: list[GroundTruthUnrequestedChange] = Field(default_factory=list)
    open_questions: list[GroundTruthOpenQuestion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_tree_integrity(self) -> "GroundTruthLabels":
        if not self.obligations:
            raise ValueError("GroundTruthLabels requires at least one obligation")

        obligation_ids = [o.id for o in self.obligations]
        if any(not oid.strip() for oid in obligation_ids):
            raise ValueError("every obligation id must be a non-empty string")
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("obligation ids must be unique")

        gap_ids = [g.id for g in self.gaps]
        if any(not gid.strip() for gid in gap_ids):
            raise ValueError("every gap id must be a non-empty string")
        if len(set(gap_ids)) != len(gap_ids):
            raise ValueError("gap ids must be unique")

        known = set(obligation_ids)
        for gap in self.gaps:
            if gap.obligation_id is not None and gap.obligation_id not in known:
                raise ValueError(
                    f"gap {gap.id!r} references unknown obligation {gap.obligation_id!r}"
                )
        for obligation in self.obligations:
            if any(not test_id.strip() for test_id in obligation.candidate_tests):
                raise ValueError(
                    f"obligation {obligation.id!r} has an empty test id in candidate_tests"
                )
            if not obligation.evidence_rationale.strip():
                raise ValueError(
                    f"obligation {obligation.id!r} must have a non-empty evidence_rationale"
                )

        question_ids = [q.id for q in self.open_questions]
        if any(not qid.strip() for qid in question_ids):
            raise ValueError("every open-question id must be a non-empty string")
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("open-question ids must be unique")
        for question in self.open_questions:
            if not question.rationale.strip():
                raise ValueError(
                    f"open question {question.id!r} must have a non-empty rationale"
                )

        unrequested_ids = [u.id for u in self.unrequested_changes]
        if any(not uid.strip() for uid in unrequested_ids):
            raise ValueError("every unrequested-change id must be a non-empty string")
        if len(set(unrequested_ids)) != len(unrequested_ids):
            raise ValueError("unrequested-change ids must be unique")
        if any(not u.file.strip() for u in self.unrequested_changes):
            raise ValueError("every unrequested change must name a non-empty file")
        return self


class BenchmarkScore(PersistableModel):
    """§11.1 metrics computed for a case, once scored (M-B0.3)."""

    gap_recall: float | None = None
    gap_precision: float | None = None
    decomposition_accuracy: float | None = None
    decomposition_precision: float | None = None
    # Not comparable across #164 — see BenchmarkReport.mapping_accuracy.
    mapping_accuracy: float | None = None
    evidence_agreement: float | None = None
    unrequested_precision: float | None = None
    unrequested_recall: float | None = None
    # Decompose-stage metrics (#195). None on any case whose ground truth takes
    # no position — most archetypes label no open questions and no types.
    open_question_recall: float | None = None
    open_question_precision: float | None = None
    obligation_type_accuracy: float | None = None


class BenchmarkCase(PersistableModel):
    case_id: str
    source: BenchmarkCaseSource
    inputs: BenchmarkCaseInputs
    ground_truth: GroundTruthLabels
    reviewer_output: Review | None = None
    score: BenchmarkScore | None = None
