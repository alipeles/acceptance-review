"""Judgement-instability harness (#189).

Every claim we hold about this reviewer's instability has been a hand-judged
anecdote costing a full run plus a manual verdict on each finding. This module
turns that into a measurement.

Three sources of movement, kept apart because they are different defects and one
blended figure would send them to the wrong fix:

- **resample** — the same request drawn N times;
- **perturbation** — a change to the request that is irrelevant to the judgement
  being watched;
- **model** — the same input judged by different models.

The measured surface is the **whole pipeline**, not only the evidence stages.
Gate 1 for #189 caught the decompose stage dropping an entire scope exclusion on
unchanged text (#193), so decomposition instability is observed, not theoretical.

## Content vs shape — the distinction that decides what is a defect

A **content difference** is a requirement, open question or judgement present in
one run and absent in another. Something was lost, and that is a *quality* defect
in the judge: a determinism layer that pinned the output would only freeze the
loss in place.

A **shape difference** is the same content partitioned differently — three
obligations in one run where another produced one. Nothing was lost, and this is
what the determinism layer exists to pin (#192).

They are reported as separate figures and never summed. `align_obligations` is
what separates them: content with no aligned counterpart *and* not covered by the
other run's set as a whole is a loss; content that is covered but partitioned
differently is shape.

## Why this issues live calls

Replaying a recorded call is guaranteed byte-identical — that guarantee is not
what is in question here. Measuring the judge means genuinely independent draws,
so runs vary the seed and use `Mode.RECORD`. This is the one part of the stability
work that costs money, and the defaults are sized accordingly: one model, three
runs. Measuring more than one model is something the caller opts into.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from pathlib import Path
from typing import Any, Callable, Sequence

from pydantic import Field

from acceptance.benchmark.alignment import align_obligations
from acceptance.benchmark.case import BenchmarkCase
from acceptance.benchmark.coverage import classify_case
from acceptance.benchmark.scoring import MetricStats, metric_stats
from acceptance.config import DEFAULT_MODEL, Mode, RunConfig
from acceptance.evidence.discrimination import (
    ObligationDiscrimination,
    PlausibleDefect,
    _Discrimination,
)
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.review_state import Review

DEFAULT_RUNS_PER_MODEL = 3
DEFAULT_MODELS: tuple[str, ...] = (DEFAULT_MODEL,)


# Seeds are derived rather than random so a measurement is repeatable from its
# recorded provenance. Varying the seed is the point: a fixed seed is what makes
# ordinary runs reproducible, and reproducibility is precisely what must be
# suspended to observe the judge's own variance.
def seeds_for(runs: int, first: int = 1000) -> list[int]:
    return [first + index for index in range(runs)]


class DifferenceKind(str, Enum):
    OBLIGATION = "obligation"
    OPEN_QUESTION = "open_question"
    EVIDENCE_CLASS = "evidence_class"
    DEFECT_VERDICT = "defect_verdict"


class DifferenceClass(str, Enum):
    """Never combine these into one number — they have different fixes."""

    CONTENT = "content"
    SHAPE = "shape"


class RunKey(PersistableModel):
    model: str
    seed: int | None
    index: int
    perturbed: bool = False

    def label(self) -> str:
        suffix = "+perturbed" if self.perturbed else ""
        return f"{self.model}#{self.index}(seed={self.seed}){suffix}"


class DefectVerdict(PersistableModel):
    obligation_id: str
    defect: str
    would_be_caught: bool


class RunSnapshot(PersistableModel):
    """One run reduced to the axes instability is measured over.

    Defect verdicts are captured from the discrimination stage as it runs rather
    than read back off the `Review`, because the per-defect judgment is not
    persisted in review state — that is #149, and fixing it here would mean
    changing the pipeline, which this task explicitly does not do.
    """

    run: RunKey
    obligations: dict[str, str] = Field(default_factory=dict)
    evidence_classes: dict[str, str | None] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
    defect_verdicts: list[DefectVerdict] = Field(default_factory=list)

    def description_for(self, obligation_id: str) -> str:
        return self.obligations.get(obligation_id, obligation_id)


class Difference(PersistableModel):
    kind: DifferenceKind
    classification: DifferenceClass
    subject: str
    present_in: str
    absent_from: str
    detail: str = ""


class PresenceRow(PersistableModel):
    subject: str
    runs_present: int
    runs_total: int

    def stable(self) -> bool:
        return self.runs_present in (0, self.runs_total)


class ClassDistribution(PersistableModel):
    subject: str
    counts: dict[str, int] = Field(default_factory=dict)

    def modal(self) -> str | None:
        if not self.counts:
            return None
        return max(sorted(self.counts), key=lambda key: self.counts[key])

    def unanimous(self) -> bool:
        return len(self.counts) <= 1


class ModelInstability(PersistableModel):
    model: str
    runs: list[RunKey] = Field(default_factory=list)
    obligation_presence: list[PresenceRow] = Field(default_factory=list)
    open_question_presence: list[PresenceRow] = Field(default_factory=list)
    evidence_class_distribution: list[ClassDistribution] = Field(default_factory=list)
    defect_verdict_distribution: list[ClassDistribution] = Field(default_factory=list)
    # Kept as two lists, never one total: a run that loses a requirement and a
    # run that partitions it differently are not the same defect.
    content_differences: list[Difference] = Field(default_factory=list)
    shape_differences: list[Difference] = Field(default_factory=list)
    content_difference_count: MetricStats = Field(default_factory=MetricStats)
    shape_difference_count: MetricStats = Field(default_factory=MetricStats)


class PerturbationResult(PersistableModel):
    name: str
    watched_judgements: int
    changed_judgements: int
    content_differences: list[Difference] = Field(default_factory=list)
    shape_differences: list[Difference] = Field(default_factory=list)

    def sensitivity(self) -> float | None:
        """Proportion of watched judgements that moved. None when nothing was
        watched — a fabricated 0.0 would read as stability."""
        if self.watched_judgements == 0:
            return None
        return self.changed_judgements / self.watched_judgements


class AgreementAxis(str, Enum):
    """Which judgement two models are being compared on.

    Agreement is reported on every axis, not only evidence classes. The axis
    where this corpus found the worst instability is open-question presence
    (#193) — a model comparison blind to it would miss the finding that prompted
    the measurement.
    """

    EVIDENCE_CLASS = "evidence_class"
    DEFECT_VERDICT = "defect_verdict"
    OBLIGATION_PRESENCE = "obligation_presence"
    OPEN_QUESTION_PRESENCE = "open_question_presence"


class CrossModelAgreement(PersistableModel):
    subject: str
    axis: AgreementAxis = AgreementAxis.EVIDENCE_CLASS
    modal_class_by_model: dict[str, str | None] = Field(default_factory=dict)
    agreeing_pairs: int = 0
    total_pairs: int = 0

    def agreement(self) -> float | None:
        if self.total_pairs == 0:
            return None
        return self.agreeing_pairs / self.total_pairs


class MeasurementProvenance(PersistableModel):
    """Everything needed to compare a later measurement against this one."""

    case_id: str
    task_digest: str
    models: list[str] = Field(default_factory=list)
    runs_per_model: int = 0
    seeds: list[int] = Field(default_factory=list)
    perturbation: str | None = None
    determinism_mode: str = Mode.RECORD.value


class InstabilityReport(PersistableModel):
    provenance: MeasurementProvenance
    per_model: list[ModelInstability] = Field(default_factory=list)
    perturbation: PerturbationResult | None = None
    cross_model_agreement: list[CrossModelAgreement] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Capturing what the pipeline judged, without changing the pipeline
# --------------------------------------------------------------------------


class ObservingClient(ModelClient):
    """A `ModelClient` that keeps every parsed response it returns.

    The discrimination stage's per-defect verdicts never reach the `Review`
    (#149). Rather than change the pipeline to persist them — out of scope here —
    the harness passes this client in and reads the stage's own output as it goes.
    Delegation happens through `super().complete`, so recording, replay, request
    keying and determinism controls are untouched.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Per instance, never a class attribute: a shared mutable default would
        # leak one run's observations into the next one's snapshot and make every
        # run look identical — stability faked by the measuring instrument.
        self.observed: list[Any] = []

    def complete(self, *args: Any, **kwargs: Any) -> Any:
        # Forwarded blind, deliberately. Pinning the signature here re-declares
        # `ModelClient.complete`'s parameter list in a second place, and the two
        # drift silently: #259 added `stage_controls` and every harness run died
        # on an unexpected keyword argument, months after the harness closed.
        # The docstring's claim that delegation leaves the client untouched is
        # only true if this forwards everything.
        result = super().complete(*args, **kwargs)
        self.observed.append(result)
        return result


def _defect_verdicts(discriminations: Sequence[ObligationDiscrimination]) -> list[DefectVerdict]:
    return [
        DefectVerdict(
            obligation_id=judgement.obligation_id,
            defect=defect.description,
            would_be_caught=defect.would_be_caught,
        )
        for judgement in discriminations
        for defect in judgement.defects
    ]


def snapshot_review(
    review: Review,
    run: RunKey,
    discriminations: Sequence[ObligationDiscrimination] = (),
) -> RunSnapshot:
    return RunSnapshot(
        run=run,
        obligations={o.id: o.description for o in review.obligation_map},
        evidence_classes={o.id: o.evidence_class for o in review.obligation_map},
        open_questions=[q.question for q in review.open_questions],
        defect_verdicts=_defect_verdicts(discriminations),
    )


# --------------------------------------------------------------------------
# Content vs shape
# --------------------------------------------------------------------------

_COVERAGE_SYSTEM_PROMPT = """\
You are comparing two independent decompositions of the same document.

For each SUBJECT taken from one decomposition, decide whether its substance is \
covered by the OTHER decomposition taken as a whole — even if the other one \
splits or combines the material differently.

covered = true  -> the substance is present in the other list, only partitioned \
differently. Nothing was lost.
covered = false -> the substance is genuinely absent from the other list. \
Something was lost.

Judge substance, not wording. Two statements that say the same thing in different \
words are covered. A statement whose requirement is a strict part of a broader \
statement in the other list is covered. A statement asserting something no \
combination of the other list asserts is NOT covered.

Answer for every subject given, and for no other."""


class _CoverageItem(StrictResponseModel):
    subject: str
    covered: bool
    reason: str


class _CoverageJudgement(StrictResponseModel):
    items: list[_CoverageItem]


def _render_coverage_prompt(subjects: Sequence[str], other: Sequence[str]) -> str:
    lines = ["## Subjects", ""]
    lines += [f"- {subject}" for subject in subjects]
    lines += ["", "## The other decomposition, in full", ""]
    lines += [f"- {statement}" for statement in other]
    return "\n".join(lines)


def classify_unmatched(
    subjects: Sequence[str],
    other: Sequence[str],
    client: ModelClient,
) -> dict[str, DifferenceClass]:
    """Split unmatched statements into shape (covered elsewhere) and content (lost).

    A bijective alignment alone cannot make this call: when one run states as two
    obligations what another states as one, the extra obligation is unmatched but
    nothing was lost. Asking whether the other set *as a whole* covers it is what
    separates a re-partition from a loss.
    """
    if not subjects:
        return {}
    if not other:
        return {subject: DifferenceClass.CONTENT for subject in subjects}

    messages = [
        {"role": "system", "content": _COVERAGE_SYSTEM_PROMPT},
        {"role": "user", "content": _render_coverage_prompt(subjects, other)},
    ]
    result = client.complete(messages, _CoverageJudgement)

    by_subject = {item.subject: item for item in result.items}
    classified: dict[str, DifferenceClass] = {}
    for subject in subjects:
        item = by_subject.get(subject)
        # An unanswered subject is not evidence that nothing was lost. Treating
        # silence as "covered" would understate content loss, which is the class
        # that matters — so an unanswered subject counts as content.
        covered = bool(item and item.covered)
        classified[subject] = DifferenceClass.SHAPE if covered else DifferenceClass.CONTENT
    return classified


def _presence_differences(
    kind: DifferenceKind,
    left: RunSnapshot,
    right: RunSnapshot,
    left_items: Sequence[str],
    right_items: Sequence[str],
    client: ModelClient,
) -> list[Difference]:
    """Differences in which statements are present, classified content vs shape."""
    alignment = align_obligations(list(left_items), list(right_items), client)
    matched_right = set(alignment)
    matched_left = set(alignment.values())

    differences: list[Difference] = []
    for source, target, unmatched, present, absent in (
        (
            left_items,
            right_items,
            [i for i in left_items if i not in matched_left],
            left.run.label(),
            right.run.label(),
        ),
        (
            right_items,
            left_items,
            [i for i in right_items if i not in matched_right],
            right.run.label(),
            left.run.label(),
        ),
    ):
        for subject, classification in classify_unmatched(unmatched, target, client).items():
            differences.append(
                Difference(
                    kind=kind,
                    classification=classification,
                    subject=subject,
                    present_in=present,
                    absent_from=absent,
                    detail=(
                        "covered by the other run's set as a whole; only the partitioning differs"
                        if classification is DifferenceClass.SHAPE
                        else "not covered by the other run's set as a whole"
                    ),
                )
            )
    return differences


def _judgement_differences(left: RunSnapshot, right: RunSnapshot) -> list[Difference]:
    """Evidence-class and defect-verdict flips.

    A rating that moves is a content difference by the standing definition: the
    judgement made in one run is absent from the other. It is never a shape
    difference — there is no partitioning involved, the same subject simply got a
    different answer.
    """
    differences: list[Difference] = []
    shared = sorted(set(left.evidence_classes) & set(right.evidence_classes))
    for obligation_id in shared:
        before, after = left.evidence_classes[obligation_id], right.evidence_classes[obligation_id]
        if before != after:
            differences.append(
                Difference(
                    kind=DifferenceKind.EVIDENCE_CLASS,
                    classification=DifferenceClass.CONTENT,
                    subject=left.description_for(obligation_id),
                    present_in=left.run.label(),
                    absent_from=right.run.label(),
                    detail=f"{before} -> {after}",
                )
            )

    left_verdicts = {(v.obligation_id, v.defect): v.would_be_caught for v in left.defect_verdicts}
    right_verdicts = {(v.obligation_id, v.defect): v.would_be_caught for v in right.defect_verdicts}
    for key in sorted(set(left_verdicts) & set(right_verdicts)):
        if left_verdicts[key] != right_verdicts[key]:
            differences.append(
                Difference(
                    kind=DifferenceKind.DEFECT_VERDICT,
                    classification=DifferenceClass.CONTENT,
                    subject=f"{left.description_for(key[0])} :: {key[1]}",
                    present_in=left.run.label(),
                    absent_from=right.run.label(),
                    detail=f"would_be_caught {left_verdicts[key]} -> {right_verdicts[key]}",
                )
            )
    return differences


def compare_runs(left: RunSnapshot, right: RunSnapshot, client: ModelClient) -> list[Difference]:
    """Every difference between two runs, each classified content or shape."""
    differences = _presence_differences(
        DifferenceKind.OBLIGATION,
        left,
        right,
        list(left.obligations.values()),
        list(right.obligations.values()),
        client,
    )
    differences += _presence_differences(
        DifferenceKind.OPEN_QUESTION,
        left,
        right,
        left.open_questions,
        right.open_questions,
        client,
    )
    differences += _judgement_differences(left, right)
    return differences


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def _presence_rows(snapshots: Sequence[RunSnapshot], selector) -> list[PresenceRow]:
    counter: Counter[str] = Counter()
    for snapshot in snapshots:
        counter.update(set(selector(snapshot)))
    return [
        PresenceRow(subject=subject, runs_present=count, runs_total=len(snapshots))
        for subject, count in sorted(counter.items())
    ]


def _evidence_distributions(snapshots: Sequence[RunSnapshot]) -> list[ClassDistribution]:
    by_description: dict[str, Counter[str]] = {}
    for snapshot in snapshots:
        for obligation_id, evidence_class in snapshot.evidence_classes.items():
            description = snapshot.description_for(obligation_id)
            by_description.setdefault(description, Counter())[str(evidence_class)] += 1
    return [
        ClassDistribution(subject=subject, counts=dict(counts))
        for subject, counts in sorted(by_description.items())
    ]


def _defect_distributions(snapshots: Sequence[RunSnapshot]) -> list[ClassDistribution]:
    by_defect: dict[str, Counter[str]] = {}
    for snapshot in snapshots:
        for verdict in snapshot.defect_verdicts:
            subject = f"{snapshot.description_for(verdict.obligation_id)} :: {verdict.defect}"
            by_defect.setdefault(subject, Counter())[str(verdict.would_be_caught).lower()] += 1
    return [
        ClassDistribution(subject=subject, counts=dict(counts))
        for subject, counts in sorted(by_defect.items())
    ]


def summarize_model(
    model: str,
    snapshots: Sequence[RunSnapshot],
    client: ModelClient,
) -> ModelInstability:
    """Within-model instability: distributions, plus every pairwise difference."""
    content: list[Difference] = []
    shape: list[Difference] = []
    content_counts: list[float | None] = []
    shape_counts: list[float | None] = []

    for left, right in combinations(snapshots, 2):
        differences = compare_runs(left, right, client)
        pair_content = [d for d in differences if d.classification is DifferenceClass.CONTENT]
        pair_shape = [d for d in differences if d.classification is DifferenceClass.SHAPE]
        content += pair_content
        shape += pair_shape
        content_counts.append(float(len(pair_content)))
        shape_counts.append(float(len(pair_shape)))

    return ModelInstability(
        model=model,
        runs=[snapshot.run for snapshot in snapshots],
        obligation_presence=_presence_rows(snapshots, lambda s: s.obligations.values()),
        open_question_presence=_presence_rows(snapshots, lambda s: s.open_questions),
        evidence_class_distribution=_evidence_distributions(snapshots),
        defect_verdict_distribution=_defect_distributions(snapshots),
        content_differences=content,
        shape_differences=shape,
        content_difference_count=metric_stats(content_counts),
        shape_difference_count=metric_stats(shape_counts),
    )


def _presence_label(row: PresenceRow) -> str:
    """A presence row reduced to what a model can be compared on.

    Deliberately three-valued. Collapsing "sometimes" into either present or
    absent would let a model that cannot make up its mind agree with one that is
    consistent — which is the disagreement most worth seeing.
    """
    if row.runs_present == 0:
        return "absent"
    if row.runs_present == row.runs_total:
        return "present"
    return f"unstable ({row.runs_present}/{row.runs_total})"


def _axis_values(report: ModelInstability) -> dict[AgreementAxis, dict[str, str | None]]:
    return {
        AgreementAxis.EVIDENCE_CLASS: {
            dist.subject: dist.modal() for dist in report.evidence_class_distribution
        },
        AgreementAxis.DEFECT_VERDICT: {
            dist.subject: dist.modal() for dist in report.defect_verdict_distribution
        },
        AgreementAxis.OBLIGATION_PRESENCE: {
            row.subject: _presence_label(row) for row in report.obligation_presence
        },
        AgreementAxis.OPEN_QUESTION_PRESENCE: {
            row.subject: _presence_label(row) for row in report.open_question_presence
        },
    }


def cross_model_agreement(per_model: Sequence[ModelInstability]) -> list[CrossModelAgreement]:
    """How far models agree, on every judgement axis rather than one.

    Reported alongside within-model variance, never instead of it: a judgement
    that each model reproduces but that no two models share is a different
    problem from one a single model cannot reproduce, and only having both
    figures distinguishes them.

    All four axes are covered because the axis that exposed the worst instability
    in `tests/fixtures/decompose-stability/` is open-question presence, not
    evidence class. Comparing models on evidence classes alone would have been
    blind to the finding that motivated this harness.
    """
    by_model = {report.model: _axis_values(report) for report in per_model}
    models = sorted(by_model)
    pairs = list(combinations(models, 2))

    rows: list[CrossModelAgreement] = []
    for axis in AgreementAxis:
        subjects: set[str] = set()
        for values in by_model.values():
            subjects.update(values[axis])

        for subject in sorted(subjects):
            per = {model: by_model[model][axis].get(subject) for model in models}
            agreeing = sum(1 for a, b in pairs if per[a] is not None and per[a] == per[b])
            rows.append(
                CrossModelAgreement(
                    subject=subject,
                    axis=axis,
                    modal_class_by_model=per,
                    agreeing_pairs=agreeing,
                    total_pairs=len(pairs),
                )
            )
    return rows


# --------------------------------------------------------------------------
# Perturbation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Perturbation:
    """A change to the input that is irrelevant to the judgements being watched."""

    name: str
    apply: Callable[[BenchmarkCase], BenchmarkCase]


_UNRELATED_TEST = '''

def test_unrelated_addition_for_perturbation_measurement():
    """Added by the instability harness. Asserts nothing about the change under
    review — its only job is to be an irrelevant edit."""
    assert True
'''


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "instability-harness",
            "GIT_AUTHOR_EMAIL": "harness@example.invalid",
            "GIT_COMMITTER_NAME": "instability-harness",
            "GIT_COMMITTER_EMAIL": "harness@example.invalid",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(repo),
        },
    )


def add_unrelated_test(case: BenchmarkCase) -> BenchmarkCase:
    """Append a test that maps to no obligation, on a copy of the repo.

    This is #180's hypothesis made executable: if an obligation's rating moves
    because an unrelated test in a co-located file changed, this is the edit that
    should move it. The repo under review is never touched — the copy is what
    gets the commit, which is also how the no-writes guarantee is kept.
    """
    source = Path(case.inputs.repo)
    destination = Path(tempfile.mkdtemp(prefix="instability-perturbed-"))
    working = destination / source.name
    shutil.copytree(source, working)

    tests = sorted(working.rglob("test_*.py"))
    if not tests:
        raise ValueError(f"no test file to perturb under {source}")
    target = tests[0]
    target.write_text(target.read_text() + _UNRELATED_TEST, encoding="utf-8")

    _git(working, "add", str(target.relative_to(working)))
    _git(working, "commit", "-m", "Add an unrelated test (instability perturbation)")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=working, check=True, capture_output=True, text=True
    ).stdout.strip()

    inputs = case.inputs.model_copy(update={"repo": str(working), "head_revision": head})
    return case.model_copy(update={"inputs": inputs})


DEFAULT_PERTURBATION = Perturbation(name="add-unrelated-test", apply=add_unrelated_test)


# --------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------


def _observed_discriminations(observed: Sequence[Any]) -> list[ObligationDiscrimination]:
    """Recover the per-defect verdicts from what the discrimination stage returned.

    `complete` hands back the stage's *response* model, `_Discrimination`.
    `ObligationDiscrimination` is built inside `judge_discrimination` after that
    call returns, so it never passes through the client at all — filtering the
    observations for it matched nothing, and every measurement recorded an empty
    defect-verdict axis while reporting success. That is the axis DR-180
    localises the instability to, so the harness was silent on precisely the
    thing it exists to measure.

    Third drift from the same cause as #259's two: the harness assuming it
    observes the pipeline's own types rather than the wire's.

    `_Discrimination` is private and imported anyway. Its class name is the
    response schema's name and therefore sits inside the hashed request, so it
    cannot be renamed to something public without invalidating every recorded
    discrimination transcript.
    """
    return [
        ObligationDiscrimination(
            obligation_id=item.obligation_id,
            defects=[
                PlausibleDefect(
                    description=defect.description,
                    would_be_caught=defect.would_be_caught,
                    reason=defect.reason,
                )
                for defect in item.defects
            ],
            discriminating=any(defect.would_be_caught for defect in item.defects),
        )
        for response in observed
        if isinstance(response, _Discrimination)
        for item in response.obligations
    ]


def run_once(
    case: BenchmarkCase,
    run: RunKey,
    transcript_root: Path | None = None,
    client_factory: Callable[[RunConfig], ObservingClient] | None = None,
) -> RunSnapshot:
    """One independent draw over `case`, snapshotted."""
    config = RunConfig(model=run.model, mode=Mode.RECORD, seed=run.seed)
    if transcript_root is not None:
        config = config.model_copy(update={"transcript_root": transcript_root})

    if client_factory is not None:
        client = client_factory(config)
    else:
        client = ObservingClient(
            model=config.model,
            mode=config.mode,
            store=config.build_client().store,
            temperature=config.temperature,
            seed=config.seed,
            # Hand-rolled rather than taken from `config.build_client()`, so it
            # does not inherit parameters the factory gains. #259 added the
            # embedding prefilter to the pipeline and this construction kept
            # working right up until the harness next ran, which was here.
            embedding_model=config.embedding_model,
        )

    scored = classify_case(case, client)
    review = scored.reviewer_output
    if review is None:  # pragma: no cover - classify_case always attaches one
        raise RuntimeError("the pipeline returned no review")

    return snapshot_review(review, run, _observed_discriminations(client.observed))


def _perturbation_result(
    name: str,
    baseline: RunSnapshot,
    perturbed: RunSnapshot,
    client: ModelClient,
) -> PerturbationResult:
    differences = compare_runs(baseline, perturbed, client)
    content = [d for d in differences if d.classification is DifferenceClass.CONTENT]
    shape = [d for d in differences if d.classification is DifferenceClass.SHAPE]
    watched = len(baseline.obligations) + len(baseline.open_questions)
    # Sensitivity counts content movement only. A re-partitioning under an
    # irrelevant edit is untidy, not a wrong answer, and folding it in here would
    # be exactly the blended figure this harness exists to avoid.
    changed = len({d.subject for d in content})
    return PerturbationResult(
        name=name,
        watched_judgements=watched,
        changed_judgements=changed,
        content_differences=content,
        shape_differences=shape,
    )


def measure_instability(
    case: BenchmarkCase,
    models: Sequence[str] = DEFAULT_MODELS,
    runs_per_model: int = DEFAULT_RUNS_PER_MODEL,
    perturbation: Perturbation | None = DEFAULT_PERTURBATION,
    comparison_client: ModelClient | None = None,
    transcript_root: Path | None = None,
    client_factory: Callable[[RunConfig], ObservingClient] | None = None,
) -> InstabilityReport:
    """Measure how far this reviewer's judgements move over one input.

    Every parameter has a default, and the defaults are one model and three runs
    so that measuring more than one model is something the caller opts into
    rather than the cost of a default run.

    Nothing is written into the repository under review: runs read it, and the
    perturbation commits to a copy.
    """
    if runs_per_model < 2:
        raise ValueError("measuring variance needs at least two runs per model")
    if not models:
        raise ValueError("at least one model is required")

    seeds = seeds_for(runs_per_model)
    comparison_client = comparison_client or ModelClient(
        model=models[0],
        mode=Mode.RECORD,
        store=RunConfig(model=models[0], mode=Mode.RECORD).build_client().store,
    )

    per_model: list[ModelInstability] = []
    first_baseline: RunSnapshot | None = None
    for model in models:
        snapshots = [
            run_once(
                case,
                RunKey(model=model, seed=seed, index=index),
                transcript_root=transcript_root,
                client_factory=client_factory,
            )
            for index, seed in enumerate(seeds)
        ]
        if first_baseline is None:
            first_baseline = snapshots[0]
        per_model.append(summarize_model(model, snapshots, comparison_client))

    perturbation_result = None
    if perturbation is not None and first_baseline is not None:
        perturbed_case = perturbation.apply(case)
        perturbed = run_once(
            perturbed_case,
            RunKey(model=models[0], seed=seeds[0], index=0, perturbed=True),
            transcript_root=transcript_root,
            client_factory=client_factory,
        )
        perturbation_result = _perturbation_result(
            perturbation.name, first_baseline, perturbed, comparison_client
        )

    return InstabilityReport(
        provenance=MeasurementProvenance(
            case_id=case.case_id,
            task_digest=_digest(case.inputs.task_text),
            models=list(models),
            runs_per_model=runs_per_model,
            seeds=seeds,
            perturbation=perturbation.name if perturbation else None,
        ),
        per_model=per_model,
        perturbation=perturbation_result,
        cross_model_agreement=cross_model_agreement(per_model),
    )


def _digest(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
