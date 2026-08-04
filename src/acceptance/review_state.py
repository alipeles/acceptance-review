"""Review-state data model (§15).

Typed, persisted review state: obligations, mappings, findings, and evidence
tiers are explicit fields, not free text (CLAUDE.md invariant). Findings also
record which component produced them and are validated against that
component's authorized tier ceiling (evidence_tier.py, M0.3). The Benchmark
case schema (M-B0.1) lives in benchmark/case.py and reuses Review here as its
reviewer-output slot rather than duplicating it.

Schemas are pydantic models: validation and round-trip (de)serialization come
from the library rather than hand-rolled per class.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from acceptance.evidence_tier import Component, EvidenceTier, authorize_tier
from acceptance.model_base import PersistableModel as _Model
from acceptance.serialization import canonical_json
from acceptance.source_ref import TextSpan

__all__ = [
    "Component",
    "EvidenceTier",
    "TextSpan",
    "ObligationType",
    "EvidenceClassification",
    "UnrequestedChangeDisposition",
    "UNREQUESTED_CHANGE",
    "DECLARATION_ABSENT",
    "DECLARATION_MISMATCH",
    "Project",
    "TaskSource",
    "MandateInterpretation",
    "BuilderDeclaration",
    "DiffHunk",
    "FileChange",
    "ChangeSet",
    "Obligation",
    "OpenQuestion",
    "TestEvidence",
    "ExecutionEvidence",
    "Link",
    "Finding",
    "TestRecommendation",
    "CompletionVerdict",
    "CompletionResult",
    "DeterminismControls",
    "ReviewProvenance",
    "ObligationChange",
    "ReviewDelta",
    "Review",
]


class ObligationType(str, Enum):
    """§7.3 obligation types."""

    FUNCTIONAL = "functional"
    BOUNDARY = "boundary"
    ERROR_HANDLING = "error_handling"
    INVARIANT = "invariant"
    REGRESSION = "regression"
    COMPATIBILITY = "compatibility"
    EXPLANATION_OBSERVABILITY = "explanation_observability"
    DOCS_CONFIG = "docs_config"
    HUMAN_REVIEW = "human_review"


# The canonical `Finding.type` string for a §9.2 unrequested-change finding.
# Single-sourced here because the obligation-less Finding invariant keys on it
# and the M3 producers (benchmark/coverage.py) and scorer (benchmark/scoring.py)
# must agree on the exact spelling.
UNREQUESTED_CHANGE = "unrequested_change"

# The canonical `Finding.type` for §7.4's "declaration absent" minor finding
# (M6.1) — single-sourced for the same reason as UNREQUESTED_CHANGE.
DECLARATION_ABSENT = "declaration_absent"

# The canonical `Finding.type` for a §7.4 declaration-vs-evidence discrepancy
# (M6.2): a declaration claim matching neither the task nor the code/tests —
# e.g. a claimed behavior the code doesn't implement and no test exercises.
DECLARATION_MISMATCH = "declaration_mismatch"

# The canonical `Finding.type` for a model answer that named an id we never
# supplied (#163). It is a fact about the review's own machinery, not about the
# delivered code — but it is never advisory: it means a judgment we asked for was
# not obtained, and the affected obligation is left `indeterminate` so the
# verdict cannot come back clean on a question that was never actually answered.
UNUSABLE_ANSWER = "unusable_answer"

# Finding types allowed to be obligation-less (related_obligation is None).
# Almost every finding is *about* an obligation and must name it; an
# unrequested change is the code→obligation dual and is obligation-less by
# construction (§9.2, DR-081). A declaration-absent finding is about the
# review's inputs, not any one obligation (M6.1). A declaration-mismatch is a
# claim matching neither the task nor the code — obligation-less too, and
# advisory / low-weight on the verdict, since nothing was actually mis-delivered
# in the code (M6.2, issue #31); distinct from an unrequested change, which is
# real code that *was* changed. An unusable answer is obligation-less when the id
# the model returned belongs to no obligation we supplied — which is the whole
# point of the finding, so it cannot be required to name one (#163).
_OBLIGATION_LESS_TYPES = frozenset(
    {UNREQUESTED_CHANGE, DECLARATION_ABSENT, DECLARATION_MISMATCH, UNUSABLE_ANSWER}
)


class UnrequestedChangeDisposition(str, Enum):
    """How to treat a §9.2 unrequested change (DR-081 decision 4). Set only on
    unrequested-change findings; `separable` and `risky` are not exclusive and
    `separable` is orthogonal to value. The classifier is M3.5.3."""

    IN_SERVICE = "in_service"  # a refactor/interface edit made to deliver an obligation
    SEPARABLE = "separable"  # coherent but distinct work — recommend its own PR/backlog item
    RISKY = "risky"  # touches public surface/deps/adjacent behavior; scrutinize


class Project(_Model):
    repo: str
    default_branch: str
    test_framework: str
    source_locations: list[str] = Field(default_factory=list)
    test_locations: list[str] = Field(default_factory=list)
    test_command: str | None = None
    execution_feasible: bool | None = None
    review_policy: str | None = None


class TaskSource(_Model):
    kind: Literal["local_file", "issue"]
    identifier: str
    snapshot: str
    text: str
    references: list[str] = Field(default_factory=list)


class MandateInterpretation(_Model):
    interpreted_outcome: str
    constraints: list[str] = Field(default_factory=list)
    explicit_obligations: list[str] = Field(default_factory=list)
    inferred_obligations: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    user_confirmations: list[str] = Field(default_factory=list)


class BuilderDeclaration(_Model):
    """The nine §7.4 template sections, as raw text."""

    mandate_as_understood: str
    implementation_summary: str
    scope_exclusions: str
    assumptions: str
    changed_components: str
    test_evidence: str
    regression_evidence: str
    known_limitations: str
    additional_behavioral_changes: str


class DiffHunk(_Model):
    """One `@@ -a,b +c,d @@` unified-diff hunk."""

    header: str
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    content: str


class FileChange(_Model):
    """One changed file between base and head (M2.1, §13.3 Git change analysis)."""

    path: str
    status: Literal["added", "modified", "deleted", "renamed"]
    category: Literal["source", "test", "config", "other"]
    old_path: str | None = None  # set when status == "renamed"
    hunks: list[DiffHunk] = Field(default_factory=list)


class ChangeSet(_Model):
    base_revision: str
    head_revision: str
    files: list[FileChange] = Field(default_factory=list)
    # Paths matched by the reviewed repo's .acceptance/ignore (#105) —
    # excluded from `files` (and therefore from every downstream capability),
    # kept here for auditability rather than dropped silently.
    ignored_paths: list[str] = Field(default_factory=list)


# §9.3 test-evidence strength classifications. Distinct from EvidenceTier
# (evidence_tier.py), which grades *how* evidence was produced, not how strong
# it is. Defined over the plausible-violation space — the §8.2 mapped mutants —
# with one bright line: does the mapped test catch at least one plausible
# violation? These are static PREDICTIONS of which mutants a mapped test would
# kill, validated against executed ground truth (§8.2); that agreement is what
# §11.1 scores. Keep in sync with spec §9.3 (the full definitions live there):
#   strongly_supported      - kills all mapped mutants
#   partially_supported     - kills at least one, but not all, mapped mutants
#   nominally_supported     - a present, relevant-looking test survives all
#                             mapped mutants (zero discriminating power); with
#                             no relevant test it is unsupported, not nominal
#   unsupported             - no mapped, obligation-relevant test at all
#   requires_other_evidence - needs non-test evidence (docs, visual, deploy)
#   indeterminate           - cannot run / cannot decide statically
EvidenceClassification = Literal[
    "strongly_supported",
    "partially_supported",
    "nominally_supported",
    "unsupported",
    "requires_other_evidence",
    "indeterminate",
]

# Evidence states a re-run can meaningfully *improve on* — used by M7.5 to decide
# whether an obligation's movement counts as a gap closing. `requires_other_evidence`
# is excluded deliberately: code tests are the wrong instrument for it, so tests
# appearing is not the gap closing.
_WEAK_OR_MISSING_EVIDENCE = frozenset(
    {"partially_supported", "nominally_supported", "unsupported", "indeterminate", None}
)


class Obligation(_Model):
    """A discrete, typed obligation derived from the task (§7.3, §9.1; M1.2).

    `id` is a stable slug so a reviewer obligation joins to the benchmark's
    ground-truth obligation by id. `source_spans` link it to the exact task
    text it derives from (M1.1). `explicit` is refined into explicit /
    reasonable-inferred / open-question by M1.3. `evidence_class` is the §9.3
    strength classification (M5.3); `achieved_evidence_tier` is separate — how
    that classification was produced (static prediction vs. executed), not how
    strong it is."""

    id: str
    description: str
    type: ObligationType
    importance: Literal["critical", "normal"]
    explicit: bool
    observable_behavior: str
    source_spans: list[TextSpan] = Field(default_factory=list)
    achieved_evidence_tier: EvidenceTier | None = None
    test_evidence: list[str] = Field(default_factory=list)
    evidence_class: EvidenceClassification | None = None
    # M3.1 implementation-coverage status, as its string value (the
    # `CoverageStatus` enum lives in coverage/classify.py, which imports from
    # here — same reason ReviewProvenance stores determinism_mode as a string).
    # The two axes are deliberately separate: coverage_status is "does the code
    # respond", evidence_class is "do the tests discriminate" (§9.2 vs §9.3).
    coverage_status: str | None = None
    # The code regions that satisfy this obligation, as "path#hunk" refs —
    # symmetric with `test_evidence`'s test node ids, so each obligation
    # carries BOTH axes' citations. Kept for every status, not just gaps: an
    # `addressed` obligation produces no finding, so without this the review
    # could say an obligation was satisfied but never say where (M7.4).
    coverage_refs: list[str] = Field(default_factory=list)
    # Set when an incremental re-run reused this obligation's judgment instead of
    # re-deriving it (M7.5): the revision the judgment was established against.
    # Recorded because a reader must be able to tell which parts of a review are
    # fresh — a carried-forward judgment is evidence about an older head, and
    # presenting it as current would overstate what this run actually checked.
    carried_forward_from: str | None = None


class Link(_Model):
    """A link to exact requirement text / code lines / test locations / a
    builder declaration — used by both `Finding` and
    `OpenQuestion.resolution_refs`. Defined here (ahead of `OpenQuestion`)
    rather than by `Finding` alone, since both need it and forward references
    don't resolve for pydantic model fields even under
    `from __future__ import annotations`."""

    kind: Literal["requirement", "code", "test", "declaration"]
    ref: str
    text: str | None = None


class OpenQuestion(_Model):
    """A material ambiguity in the task that needs user judgment (§7.3, §9.3).

    Surfaced instead of silently inventing an obligation — uncertainty is a
    first-class, expected output. `source_spans` link to the underspecified
    task text.

    `resolved`/`resolution_rationale`/`resolution_refs` are set by
    `coverage/open_questions.py`'s `apply_open_question_resolutions` (#113):
    when the diff itself makes the answer clear, that judgment is recorded
    here rather than left as something a conversation concluded and the tool
    immediately forgets on the next run."""

    id: str
    question: str
    importance: Literal["critical", "normal"] = "normal"
    source_spans: list[TextSpan] = Field(default_factory=list)
    resolved: bool = False
    resolution_rationale: str | None = None
    resolution_refs: list[Link] = Field(default_factory=list)


class TestEvidence(_Model):
    __test__ = False  # not a pytest test class; name matches §15's "Test evidence"

    identifier: str
    location: str
    inputs: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)
    expected_value_provenance: str | None = None
    mocks: list[str] = Field(default_factory=list)
    relevant_path: bool | None = None
    mapped_obligations: list[str] = Field(default_factory=list)
    static_assessment: str | None = None


class ExecutionEvidence(_Model):
    run_id: str
    command: str
    result: Literal["pass", "fail", "skip"]
    reviewed_revision: str
    coverage_of_obligation_lines: bool | None = None
    mutation_descriptor: str | None = None
    outcome: Literal["killed", "survived"] | None = None


class Finding(_Model):
    """Typed and linked (CLAUDE.md invariant): cannot be built without an
    evidence tier and at least one link target, and the producing component
    must be authorized for the claimed tier (§8.1, M0.3).

    Findings are *about* an obligation and must name it in `related_obligation`;
    the only exception is a finding whose type is in `_OBLIGATION_LESS_TYPES`
    (an unrequested change, §9.2, which is obligation-less by construction).
    A `disposition` — how to treat an unrequested change — may be set only on
    an unrequested-change finding (DR-081)."""

    type: str
    severity: str
    description: str
    evidence_tier: EvidenceTier
    produced_by: Component
    links: list[Link]
    related_obligation: str | None = None
    disposition: UnrequestedChangeDisposition | None = None
    supporting_evidence: list[str] = Field(default_factory=list)
    uncertainty: str | None = None
    recommended_action: str | None = None

    @field_validator("links")
    @classmethod
    def _require_at_least_one_link(cls, value: list[Link]) -> list[Link]:
        if not value:
            raise ValueError("Finding requires at least one link target")
        return value

    @model_validator(mode="after")
    def _require_authorized_tier(self) -> "Finding":
        authorize_tier(self.produced_by, self.evidence_tier)
        return self

    @model_validator(mode="after")
    def _obligation_less_only_for_allowed_types(self) -> "Finding":
        obligation_less_ok = self.type in _OBLIGATION_LESS_TYPES
        if self.related_obligation is None and not obligation_less_ok:
            raise ValueError(
                f"Finding of type {self.type!r} must name a related_obligation; "
                f"only {sorted(_OBLIGATION_LESS_TYPES)} may be obligation-less"
            )
        if self.related_obligation is not None and self.type == UNREQUESTED_CHANGE:
            raise ValueError(
                "an unrequested_change finding is obligation-less by construction; "
                "it must not carry a related_obligation"
            )
        return self

    @model_validator(mode="after")
    def _disposition_only_for_unrequested_change(self) -> "Finding":
        if self.disposition is not None and self.type != UNREQUESTED_CHANGE:
            raise ValueError(
                f"disposition is only valid on an {UNREQUESTED_CHANGE!r} finding, "
                f"not {self.type!r}"
            )
        return self


class TestRecommendation(_Model):
    """A §9.5 structured recommendation for additional test evidence (M7.1).

    Emitted for a criterion whose evidence is missing/weak, in a
    machine-readable form a coding agent can pick up and implement in a single
    iteration. The product recommends — it never modifies code (§9.5). Each
    field is one of §9.5's discrete prescriptions; `plausible_defect` is the
    surviving §8.2 defect the recommended test must catch, so a green run
    demonstrably closes the gap rather than nominally addressing it (§8.4)."""

    __test__ = False  # not a pytest test class; name matches §9.5's "recommendation"

    obligation_id: str
    criterion: str  # the obligation's observable behavior, restated
    required_inputs: str
    boundary_conditions: str
    expected_output: str
    required_assertions: list[str] = Field(default_factory=list)
    plausible_defect: str
    repo_conventions: str


class CompletionVerdict(str, Enum):
    """§10.1 step 11 overall completion result. A positive verdict
    (`no_material_gaps`) is bounded — "no material gaps at the achievable
    evidence tier," never proof of correctness (§3.7)."""

    NO_MATERIAL_GAPS = "no_material_gaps"
    INCOMPLETE = "incomplete"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_NON_CODE_REVIEW = "needs_non_code_review"
    UNABLE_TO_DETERMINE = "unable_to_determine"


class CompletionResult(_Model):
    """The overall completion verdict, derived deterministically from the
    findings (M7.2). Kept a pure rollup so the headline result is auditable —
    it traces to the exact findings that produced it, never a free-text model
    conclusion (§13.6). `escalation_candidates` names the obligations whose
    evidence is indeterminate — the set where spending more effort (deeper
    retrieval, execution, §8/M8) could move the verdict; the seam a future
    "try harder" loop attaches to, re-deriving this same function afterward."""

    verdict: CompletionVerdict
    rationale: str
    limitations: list[str] = Field(default_factory=list)
    escalation_candidates: list[str] = Field(default_factory=list)


class DeterminismControls(_Model):
    """A seed/temperature pair.

    `None` means the control is **not in force**. For requested controls that is
    "we asked for nothing"; for honoured controls it is the stronger statement
    that the provider ignored the control and ran at its own default. Both are
    real: Anthropic rejects `seed` outright and `claude-sonnet-5` accepts only
    `temperature=1`, so a run there honours neither control (#158).
    """

    temperature: float | None = None
    seed: int | None = None


class ReviewProvenance(_Model):
    """How a review was produced (§13.6 trustworthiness). Stored so a reader
    can tell what determinism controls were in force — a fixed-seed replay is
    reproducible in a way a live sampled run is not, and M-B0.4's variance
    disclosure reads this. Mode is stored as its string value, not the harness
    `Mode` enum, so the data model stays independent of the LLM harness.

    Requested and honoured controls are separate fields because they diverge.
    The harness sends determinism controls through LiteLLM with `drop_params`,
    which lets a provider that rejects a control run anyway rather than failing
    the review — so what we asked for is intent, and only `controls_in_force`
    describes the run that actually happened (#160). Reporting a single set
    would have provenance claim a seed the provider never received.
    """

    determinism_mode: Literal["record", "replay"]
    model: str
    controls_requested: DeterminismControls
    # None until some model call is observed. A review can legitimately make no
    # model call at all, and such a run must not inherit a claim that the
    # configured controls held — see `determinism`.
    controls_in_force: DeterminismControls | None = None
    # How many items one partitioned request covered (DR-164). Observed from the
    # calls, not read from configuration, so it reports the partitioning that was
    # actually in force. None means no partitioned call was made — a different
    # claim from a partition of size one.
    request_partition_size: int | None = None

    def determinism(self) -> Literal["pinned", "unpinned", "indeterminate"]:
        """Whether this run is reproducible, derived rather than stored.

        Derived for the same reason as `Review.evidence_tier_summary`: a stored
        copy alongside the controls it summarizes is a second source of truth
        that can drift. `indeterminate` is a real answer, not a fallback — with
        no observed call there is no evidence either way, and the uncertainty is
        first-class (§9.3).
        """
        if self.controls_in_force is None:
            return "indeterminate"
        requested = self.controls_requested
        honoured = self.controls_in_force
        for name in ("temperature", "seed"):
            asked = getattr(requested, name)
            if asked is not None and getattr(honoured, name) != asked:
                return "unpinned"
        return "pinned"


class ObligationChange(_Model):
    """How one obligation moved between a prior review and this one (M7.5)."""

    obligation_id: str
    description: str
    previous_coverage_status: str | None = None
    coverage_status: str | None = None
    previous_evidence_class: EvidenceClassification | None = None
    evidence_class: EvidenceClassification | None = None

    def closed_gap(self) -> bool:
        """Whether this movement is a gap closing — the §13.5 #9 outcome.

        Derived rather than stored, like `Review.evidence_tier_summary`: a stored
        flag beside the statuses it summarizes is a second source of truth.
        """
        was_gap = self.previous_coverage_status is not None and (
            self.previous_coverage_status != "addressed"
        )
        was_weak = self.previous_evidence_class in _WEAK_OR_MISSING_EVIDENCE
        now_addressed = self.coverage_status == "addressed"
        now_supported = self.evidence_class == "strongly_supported"
        return (was_gap and now_addressed) or (was_weak and now_supported)


class ReviewDelta(_Model):
    """What changed since the prior review this run built on (M7.5).

    Persisted rather than only rendered, so "the gap you were told about is now
    closed" is inspectable review state and not a sentence in a report that the
    next run forgets — the same reason open-question resolutions are stored.
    """

    prior_reviewed_revision: str
    previous_verdict: str | None = None
    verdict: str | None = None
    obligation_changes: list[ObligationChange] = Field(default_factory=list)
    carried_forward_obligation_ids: list[str] = Field(default_factory=list)

    def closed_gaps(self) -> list[ObligationChange]:
        return [change for change in self.obligation_changes if change.closed_gap()]


class Review(_Model):
    mode: str
    reviewed_revision: str
    provenance: ReviewProvenance | None = None
    task_source: TaskSource | None = None
    # Present only on an incremental re-run (M7.5); None on a first review.
    delta: ReviewDelta | None = None
    mandate: MandateInterpretation | None = None
    declaration: BuilderDeclaration | None = None
    change_set: ChangeSet | None = None
    obligation_map: list[Obligation] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[TestRecommendation] = Field(default_factory=list)
    completion: CompletionResult | None = None
    limitations: list[str] = Field(default_factory=list)
    recommendation: str | None = None

    def to_canonical_json(self) -> str:
        """Byte-stable persisted form: identical review state serializes to
        identical bytes across runs (M0.5 acceptance). Distinct from the
        human-readable CLI report rendered in M0.6."""
        return canonical_json(self.to_dict())

    def evidence_tier_summary(self) -> dict[str, int]:
        """Tier counts derived from obligations/findings, not stored — the
        achieved tier lives on each Obligation/Finding; a separate stored
        copy here would be a second source of truth that can drift."""
        counts: dict[str, int] = {}
        for obligation in self.obligation_map:
            if obligation.achieved_evidence_tier is not None:
                key = obligation.achieved_evidence_tier.name
                counts[key] = counts.get(key, 0) + 1
        for finding in self.findings:
            key = finding.evidence_tier.name
            counts[key] = counts.get(key, 0) + 1
        return counts
