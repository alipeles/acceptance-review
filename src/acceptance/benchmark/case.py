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
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import (
    DefectType,
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
    # Set when the ground truth's position is that this obligation admits no
    # plausible static defect — #270's shape, an obligation true by construction.
    # That is a *label*, distinct in both directions from `None`, which says the
    # ground truth takes no position on this obligation's defects at all. The
    # distinction is the whole of DefectSet's own "nothing found" versus "not
    # looked at" rule, restated on the labelling side: without it a case with no
    # defect labels scores an enumerator that invented three defects the same as
    # one that correctly recorded none.
    no_plausible_defect_reason: str | None = None


class GroundTruthDefect(PersistableModel):
    """One way of failing an obligation that a competent reviewer should record,
    and the tests that would fail if the delivered code contained it (#315).

    The label counterpart of `review_state.Defect`, and deliberately the same
    shape: `type` is drawn from the same `DefectType` vocabulary the enumerator
    spends, with `OTHER` allowed, so a labelled defect and a recorded one can be
    compared on classification without a translation table.

    `killed_by` is what separates the two failures this issue exists to tell
    apart. Enumeration recall asks whether the review recorded this defect at
    all; kill agreement asks whether it then got the tests right. An **empty**
    `killed_by` is a real label, not a missing one: archetype #4 is the case
    where a present, relevant test kills nothing, and a defect no test catches
    is exactly the finding the review is supposed to produce.

    `description` is free text and is never matched verbatim — see
    `defect_scoring.align_defects`, which matches on what two descriptions
    describe, for the same reason `align_obligations` exists.
    """

    id: str
    obligation_id: str
    type: DefectType
    description: str
    killed_by: list[str] = Field(default_factory=list)  # test ids (pytest nodeids)


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
    defects: list[GroundTruthDefect] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_tree_integrity(self) -> GroundTruthLabels:
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
                raise ValueError(f"open question {question.id!r} must have a non-empty rationale")

        unrequested_ids = [u.id for u in self.unrequested_changes]
        if any(not uid.strip() for uid in unrequested_ids):
            raise ValueError("every unrequested-change id must be a non-empty string")
        if len(set(unrequested_ids)) != len(unrequested_ids):
            raise ValueError("unrequested-change ids must be unique")
        if any(not u.file.strip() for u in self.unrequested_changes):
            raise ValueError("every unrequested change must name a non-empty file")

        self._check_defect_integrity(known)
        return self

    def _check_defect_integrity(self, obligation_ids: set[str]) -> None:
        """Defect labels resolve, and say nothing they cannot say (#315).

        Rejecting rather than loading, for the reason the rest of this validator
        does: ground truth that carries a dangling reference scores the checker
        against something no reviewer could have produced, and the failure is
        silent — a defect labelled against an obligation the case does not define
        can never be matched, so it depresses enumeration recall forever while
        looking like a real miss.

        `killed_by` is checked against the tests the case actually supplies, that
        being the union of every obligation's `candidate_tests`. A label naming a
        test outside it is either a typo or a test the case does not have, and
        both make kill agreement unscoreable in the same invisible way.
        """
        defect_ids = [d.id for d in self.defects]
        if any(not did.strip() for did in defect_ids):
            raise ValueError("every defect id must be a non-empty string")
        if len(set(defect_ids)) != len(defect_ids):
            raise ValueError("defect ids must be unique")

        supplied_tests = {t for o in self.obligations for t in o.candidate_tests}
        for defect in self.defects:
            if defect.obligation_id not in obligation_ids:
                raise ValueError(
                    f"defect {defect.id!r} references unknown obligation {defect.obligation_id!r}"
                )
            if not defect.description.strip():
                raise ValueError(f"defect {defect.id!r} must have a non-empty description")
            for test_id in defect.killed_by:
                if not test_id.strip():
                    raise ValueError(f"defect {defect.id!r} has an empty test id in killed_by")
                if test_id not in supplied_tests:
                    raise ValueError(
                        f"defect {defect.id!r} is killed_by {test_id!r}, which no "
                        "obligation lists as a candidate test"
                    )

        # "No plausible defect" and a labelled defect are contradictory claims
        # about the same obligation. Left to coexist, the pair would let a case
        # score an enumerator both for recording the defect and for correctly
        # recording none.
        labelled = {d.obligation_id for d in self.defects}
        for obligation in self.obligations:
            if obligation.no_plausible_defect_reason is None:
                continue
            if not obligation.no_plausible_defect_reason.strip():
                raise ValueError(
                    f"obligation {obligation.id!r} has an empty "
                    "no_plausible_defect_reason; omit the field to take no position"
                )
            if obligation.id in labelled:
                raise ValueError(
                    f"obligation {obligation.id!r} says no defect is plausible but "
                    "also carries labelled defects"
                )


class DefectScore(PersistableModel):
    """Every defect-set figure for one case (#315), each independently absent-able.

    Lives here rather than in `defect_scoring.py` so that module can import it
    without a cycle, and beside `BenchmarkScore` because it is one.

    Counts travel with the shares because a share alone cannot be read: "recall
    1.0" over one labelled defect and over twenty are different claims, and
    DR-312 requires the denominator to be disclosed wherever the figure renders.
    """

    enumeration_recall: float | None = None
    recall_by_type: dict[DefectType, float] = Field(default_factory=dict)
    type_agreement: float | None = None
    other_share: float | None = None
    kill_agreement: float | None = None
    labelled: int = 0
    recorded: int = 0
    matched: int = 0
    predicted: int = 0


class BenchmarkScore(PersistableModel):
    """§11.1 metrics computed for a case, once scored (M-B0.3)."""

    gap_recall: float | None = None
    gap_precision: float | None = None
    # Not comparable across #202, for the reason #164 gives at mapping_accuracy:
    # decomposition is now asked for one disposition per identified requirement
    # rather than for a flat obligation list, so the question put to the model
    # changed. Figures either side of that change must not be plotted as a trend
    # or cited as a regression.
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
    # Defect-set figures (#315). A nested record rather than flat fields because
    # every figure inside it shares one denominator disclosure, and because it
    # is absent as a whole on a case with no defect labels — which is different
    # from each figure being individually absent.
    defects: DefectScore | None = None


class BenchmarkCase(PersistableModel):
    case_id: str
    source: BenchmarkCaseSource
    inputs: BenchmarkCaseInputs
    ground_truth: GroundTruthLabels
    reviewer_output: Review | None = None
    score: BenchmarkScore | None = None


class EmptyRequirementRegistryError(RuntimeError):
    """A case's task file yields no requirements, so the case cannot run.

    Raised rather than scored, and raised for the same reason
    `UnresolvableRevisionError` and `MissingRunInputError` are: a case that
    quietly degrades is worse than one that breaks. Those two lose an input that
    is visibly absent. This one loses an input that is visibly *present* — the
    task file is right there and reads fine — but that the parser routes into
    `unclaimed` rather than into requirements, so nothing downstream ever sees a
    requirement to decompose.

    That failure produced no error for as long as it existed (#228). Every
    archetype headed its mandate `# Task: <title>`, which is not the `task`
    heading `parse_task_file` recognises, so all thirteen built an empty
    registry; `decompose` correctly made no model call over no requirements, and
    the scorer correctly reported that nothing was recovered. Each stage was
    right and the number was meaningless: it measured a decomposition of
    nothing, not a degraded decomposition.

    **A zero here is not a score.** It is the absence of a run, and the two are
    indistinguishable once a float reaches a report — which is why this is an
    exception and not a metric of 0.0.
    """


def require_nonempty_registry(case_id: str, task_text: str) -> None:
    """Raise unless `task_text` yields at least one identified requirement.

    Called by every corpus case builder before it returns a case, so an
    unreadable task file fails at the point the case is assembled rather than
    surfacing as a plausible-looking zero several stages later.

    The check is deliberately the *real* parse — `parse_task_file` then
    `build_registry`, the same two calls `decompose` makes — rather than a
    cheaper proxy such as looking for a `# Task` heading. A proxy would pass
    exactly when the parser changed its mind about what a requirement is, which
    is the case worth catching.
    """
    if build_registry(parse_task_file(task_text)):
        return
    raise EmptyRequirementRegistryError(
        f"case {case_id!r} has a task file that yields no requirements, so the "
        f"case did not run. This is not a score of zero: there was nothing for "
        f"the checker to decompose, map or judge, and any metric computed over "
        f"it would measure the absence of input rather than the quality of the "
        f"output. Check that the task file uses the section headings "
        f"`parse_task_file` recognises — a mandate headed `# Task: <title>` is "
        f"not the `task` heading, and puts the whole mandate in `unclaimed`."
    )
