"""Decompose-stage instability measurement (#193).

The counterpart to `instability.py`, which measures the whole review pipeline.
This one measures **decomposition alone**, and exists because the pipeline
harness cannot answer #193's questions:

- `run_once` calls `classify_case`, so every draw pays for mapping, evidence
  extraction, discrimination and coverage. Decompose is a small fraction of that
  cost and none of the rest is being measured here.
- Worse, it is not *isolation*. A decompose number read off a full-pipeline run
  is contaminated by whatever mapping and discrimination did downstream, and
  #191's four measurements are the standing demonstration that those stages move
  independently of the obligation set they range over.

## The spine is the requirement id, not the obligation text

`build_registry` mints `section-ordinal` ids from the PARSE, never from the
model, so the same task file yields the same requirement ids on every run. That
makes a stable join key available for free, and almost every axis below is keyed
on it rather than on aligned free text.

This matters more than it sounds. `align_obligations` is a model call, so an
axis keyed on alignment costs money and carries the aligner's own judgement into
the measurement. An axis keyed on the requirement id costs nothing and is
exactly reproducible. Only the content-vs-shape comparison genuinely needs the
aligner, and it is therefore the one part that takes a client and can be skipped.

## Symbols ride their own axis, deliberately

#193 §3 is that `benchmark/scoring.py::disclose_variance` degrades into "the
existing benchmark variance path" between two runs over byte-identical text.
That loss is invisible to every set metric, because the aligner correctly
matches the degraded obligation to the intact one — they *are* the same
requirement. `GroundTruthObligation.required_symbols` records the same
observation for the labelled corpus; this module computes the live version of it,
against the requirement's own source text, with no labels needed.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path

from pydantic import Field

from acceptance.benchmark.instability import (
    ClassDistribution,
    Difference,
    DifferenceClass,
    MeasurementProvenance,
    PresenceRow,
    RunKey,
    RunSnapshot,
    compare_runs,
    seeds_for,
)
from acceptance.benchmark.scoring import MetricStats, metric_stats
from acceptance.config import DEFAULT_MODEL, Mode, RunConfig
from acceptance.llm import ModelClient
from acceptance.model_base import PersistableModel
from acceptance.requirement.obligations import Decomposition, decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.rerun import task_digest
from acceptance.review_state import RequirementRef

DEFAULT_DECOMPOSE_RUNS = 3

# A symbol is either a backticked span carrying no whitespace — the convention
# every task file in the corpus uses for a path, a function or a flag — or a
# bare `file.py::name` reference, which appears unbackticked often enough to be
# worth catching. Prose in backticks ("`the existing path`") is excluded by the
# whitespace rule rather than by trying to guess at identifier syntax.
_BACKTICKED = re.compile(r"`([^`\s]+)`")
_QUALIFIED = re.compile(r"\b[\w./-]+\.py::\w+\b")


def symbols_in(text: str) -> list[str]:
    """Identifiers a requirement names, in first-appearance order.

    Order is deliberate and not sorted: it keeps the report readable against the
    source text. De-duplicated because a requirement naming one symbol twice
    states one requirement about it.
    """
    found: list[str] = []
    for match in (*_BACKTICKED.finditer(text), *_QUALIFIED.finditer(text)):
        symbol = match.group(1) if match.re is _BACKTICKED else match.group(0)
        if symbol not in found:
            found.append(symbol)
    return found


def _symbol_key(requirement_id: str, symbol: str) -> str:
    return f"{requirement_id} :: {symbol}"


class DecomposeSnapshot(RunSnapshot):
    """One decompose draw, reduced to the axes #193 is written against.

    Subclasses `RunSnapshot` rather than replacing it so `compare_runs` works on
    it unchanged — the content-vs-shape machinery is stage-agnostic and there is
    no reason for a second copy of it. `evidence_classes` and `defect_verdicts`
    stay empty here, honestly: no evidence stage ran.

    Every `*_by_requirement` field is keyed on the registry id, so two runs are
    comparable without a model call.
    """

    dispositions: dict[str, str] = Field(default_factory=dict)
    obligation_ids_by_requirement: dict[str, list[str]] = Field(default_factory=dict)
    types_by_requirement: dict[str, list[str]] = Field(default_factory=dict)
    descriptions_by_requirement: dict[str, list[str]] = Field(default_factory=dict)
    # `<requirement id> :: <symbol>` for every symbol that survived out of its
    # requirement's text into at least one of that requirement's obligations.
    # A list of what survived rather than a map of what was required, so
    # `_presence_rows` can count it directly.
    surviving_symbols: list[str] = Field(default_factory=list)
    # Every symbol the task file named, whether it survived or not. Constant
    # across runs over one task file, and carried so a report can state the
    # denominator without re-parsing.
    required_symbols: list[str] = Field(default_factory=list)


def snapshot_decomposition(result: Decomposition, run: RunKey) -> DecomposeSnapshot:
    """Reduce one decomposition to its measured axes."""
    by_id = {obligation.id: obligation for obligation in result.obligations}
    requirements: list[RequirementRef] = list(result.requirement_map.requirements)

    dispositions: dict[str, str] = {}
    ids_by_requirement: dict[str, list[str]] = {}
    types_by_requirement: dict[str, list[str]] = {}
    descriptions_by_requirement: dict[str, list[str]] = {}
    surviving: list[str] = []
    required: list[str] = []

    for requirement in requirements:
        entry = result.requirement_map.disposition_for(requirement.id)
        # A requirement with no disposition at all is itself the finding this
        # stage's shape exists to prevent, so it is recorded rather than skipped.
        dispositions[requirement.id] = entry.disposition.value if entry else "absent"
        obligation_ids = list(entry.obligation_ids) if entry else []
        ids_by_requirement[requirement.id] = obligation_ids

        derived = [by_id[oid] for oid in obligation_ids if oid in by_id]
        types_by_requirement[requirement.id] = [o.type.value for o in derived]
        descriptions_by_requirement[requirement.id] = [o.description for o in derived]

        haystack = " ".join(o.description for o in derived)
        for symbol in symbols_in(requirement.text):
            key = _symbol_key(requirement.id, symbol)
            required.append(key)
            if symbol in haystack:
                surviving.append(key)

    return DecomposeSnapshot(
        run=run,
        obligations={o.id: o.description for o in result.obligations},
        open_questions=[q.question for q in result.open_questions],
        dispositions=dispositions,
        obligation_ids_by_requirement=ids_by_requirement,
        types_by_requirement=types_by_requirement,
        descriptions_by_requirement=descriptions_by_requirement,
        surviving_symbols=surviving,
        required_symbols=required,
    )


def decompose_once(
    task_text: str,
    run: RunKey,
    transcript_root: Path | None = None,
    client_factory: Callable[[RunConfig], ModelClient] | None = None,
) -> DecomposeSnapshot:
    """One independent draw of decomposition over `task_text`, snapshotted.

    `Mode.RECORD` for the same reason `run_once` uses it: varying the seed is
    the whole point, and a replayed draw would return the previous one by
    construction and measure nothing.
    """
    config = RunConfig(model=run.model, mode=Mode.RECORD, seed=run.seed)
    if transcript_root is not None:
        config = config.model_copy(update={"transcript_root": transcript_root})

    client = client_factory(config) if client_factory is not None else config.build_client()
    parsed = parse_task_file(task_text)
    result = decompose(parsed, client, batch_size=config.decompose_batch_size)
    return snapshot_decomposition(result, run)


# --------------------------------------------------------------------------
# Aggregation — every axis below this line is free of model calls
# --------------------------------------------------------------------------


def _presence_rows(snapshots: Sequence[DecomposeSnapshot], selector) -> list[PresenceRow]:
    """How many runs each subject appeared in.

    A local copy of `instability._presence_rows` rather than an import of a
    private name from a sibling module. Six lines, and the alternative is a
    cross-module dependency on something explicitly marked internal.
    """
    counter: Counter[str] = Counter()
    for snapshot in snapshots:
        counter.update(set(selector(snapshot)))
    return [
        PresenceRow(subject=subject, runs_present=count, runs_total=len(snapshots))
        for subject, count in sorted(counter.items())
    ]


def _distribution(
    snapshots: Sequence[DecomposeSnapshot],
    selector: Callable[[DecomposeSnapshot], dict[str, object]],
) -> list[ClassDistribution]:
    """For each requirement, how its answer was distributed across the runs.

    A subject whose counts have one entry was answered identically every time.
    `ClassDistribution.unanimous()` is therefore the stability test, and it is
    exact rather than a tolerance.
    """
    counters: dict[str, Counter[str]] = {}
    for snapshot in snapshots:
        for subject, value in selector(snapshot).items():
            counters.setdefault(subject, Counter())[_render(value)] += 1
    return [
        ClassDistribution(subject=subject, counts=dict(counter))
        for subject, counter in sorted(counters.items())
    ]


def _render(value: object) -> str:
    """One requirement's answer on one axis, as a comparable string.

    A list is rendered in order, not as a set: two runs that derive the same
    obligations in a different order have not agreed, because the order decides
    which one downstream reads first and, for `linking.py`, which one survives a
    merge.
    """
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    return str(value)


class DecomposeInstability(PersistableModel):
    """One model's decompose variance over N draws of one task file."""

    model: str
    runs: list[RunKey] = Field(default_factory=list)

    # Keyed on requirement id — no model call, exactly reproducible.
    disposition_distribution: list[ClassDistribution] = Field(default_factory=list)
    obligation_id_distribution: list[ClassDistribution] = Field(default_factory=list)
    description_distribution: list[ClassDistribution] = Field(default_factory=list)
    type_distribution: list[ClassDistribution] = Field(default_factory=list)
    obligation_count_distribution: list[ClassDistribution] = Field(default_factory=list)
    symbol_survival: list[PresenceRow] = Field(default_factory=list)

    # Keyed on aligned text — costs model calls, and is None when no client was
    # supplied. Empty lists would read as "nothing moved", which is the one
    # reading a skipped measurement must never produce.
    content_differences: list[Difference] | None = None
    shape_differences: list[Difference] | None = None
    content_difference_count: MetricStats | None = None
    shape_difference_count: MetricStats | None = None

    def unstable_requirements(self, selector: str = "description_distribution") -> list[str]:
        """Requirement ids whose answer on `selector` was not unanimous."""
        rows: list[ClassDistribution] = getattr(self, selector)
        return [row.subject for row in rows if not row.unanimous()]

    def symbols_lost(self) -> list[PresenceRow]:
        """Symbols that survived in some runs and not others, or in none.

        Both are findings and they are different ones: a symbol that never
        survives is a systematic loss, while one that survives intermittently is
        the instability #193 §3 records. `PresenceRow.stable()` separates them.
        """
        return [row for row in self.symbol_survival if row.runs_present < row.runs_total]


class DecomposePerturbation(PersistableModel):
    """What moved under an edit that should not have reached it.

    `watched` counts only requirements present in BOTH task files, so the added
    bullet's own requirement is never in the numerator or the denominator. The
    ratio defect queued against the pipeline harness — a numerator counting
    subjects its denominator excludes — is avoided here by construction.
    """

    name: str
    watched_requirements: int
    moved_requirements: list[str] = Field(default_factory=list)

    def sensitivity(self) -> float | None:
        if self.watched_requirements == 0:
            return None
        return len(self.moved_requirements) / self.watched_requirements


class DecomposeInstabilityReport(PersistableModel):
    provenance: MeasurementProvenance
    per_model: list[DecomposeInstability] = Field(default_factory=list)
    perturbation: DecomposePerturbation | None = None


def summarize_decompose(
    model: str,
    snapshots: Sequence[DecomposeSnapshot],
    client: ModelClient | None = None,
) -> DecomposeInstability:
    """Aggregate N draws into one model's report.

    `client` is optional and its absence is recorded as `None` rather than as an
    empty difference list — see `DecomposeInstability.content_differences`.
    """
    report = DecomposeInstability(
        model=model,
        runs=[snapshot.run for snapshot in snapshots],
        disposition_distribution=_distribution(snapshots, lambda s: s.dispositions),
        obligation_id_distribution=_distribution(
            snapshots, lambda s: s.obligation_ids_by_requirement
        ),
        description_distribution=_distribution(snapshots, lambda s: s.descriptions_by_requirement),
        type_distribution=_distribution(snapshots, lambda s: s.types_by_requirement),
        obligation_count_distribution=_distribution(
            snapshots,
            lambda s: {key: len(value) for key, value in s.obligation_ids_by_requirement.items()},
        ),
        symbol_survival=_presence_rows(snapshots, lambda s: s.surviving_symbols),
    )
    if client is None:
        return report

    content: list[Difference] = []
    shape: list[Difference] = []
    content_counts: list[float] = []
    shape_counts: list[float] = []
    for index, left in enumerate(snapshots):
        for right in snapshots[index + 1 :]:
            differences = compare_runs(left, right, client)
            pair_content = [d for d in differences if d.classification is DifferenceClass.CONTENT]
            pair_shape = [d for d in differences if d.classification is DifferenceClass.SHAPE]
            content.extend(pair_content)
            shape.extend(pair_shape)
            content_counts.append(float(len(pair_content)))
            shape_counts.append(float(len(pair_shape)))

    report.content_differences = content
    report.shape_differences = shape
    report.content_difference_count = metric_stats(content_counts)
    report.shape_difference_count = metric_stats(shape_counts)
    return report


# --------------------------------------------------------------------------
# Perturbation
# --------------------------------------------------------------------------

UNRELATED_EXCLUSION = "- Anything to do with how the changelog is formatted."


def append_unrelated_exclusion(task_text: str, bullet: str = UNRELATED_EXCLUSION) -> str:
    """Add one irrelevant bullet to `## Scope exclusions`.

    This perturbation is not invented: it is #193 §4's finding replayed. Adding a
    single bullet to Scope exclusions and nothing else silenced an entire
    requirement in an untouched section, which is the sharpest isolation in the
    corpus.

    Appended at the END of the section, deliberately. `build_registry` mints
    `section-ordinal` ids positionally, so appending leaves every existing
    requirement id untouched, while an insertion would renumber the rest of the
    section and make every later requirement look changed for a reason that has
    nothing to do with the judge. That fragility is itself worth knowing about —
    it is why requirement identity across task-file versions is #209 — but it
    must not contaminate this measurement.
    """
    lines = task_text.splitlines()
    heading = None
    for index, line in enumerate(lines):
        if line.strip().lower().startswith("## scope exclusions"):
            heading = index
            break
    if heading is None:
        raise ValueError("task file has no '## Scope exclusions' section to perturb")

    end = heading + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    while end > heading + 1 and not lines[end - 1].strip():
        end -= 1

    return "\n".join([*lines[:end], bullet, *lines[end:]]) + "\n"


def _moved_requirements(
    baseline: DecomposeSnapshot,
    perturbed: DecomposeSnapshot,
) -> list[str]:
    """Requirements whose answer changed, over the requirements both runs share.

    Compares disposition, obligation count and description text. Ids are
    excluded: an id that moved while the description held is churn worth
    reporting on the resample axis, but it is not evidence that the perturbation
    reached this requirement's meaning.
    """
    shared = sorted(set(baseline.dispositions) & set(perturbed.dispositions))
    moved: list[str] = []
    for requirement_id in shared:
        same = baseline.dispositions[requirement_id] == perturbed.dispositions[
            requirement_id
        ] and baseline.descriptions_by_requirement.get(
            requirement_id
        ) == perturbed.descriptions_by_requirement.get(requirement_id)
        if not same:
            moved.append(requirement_id)
    return moved


def measure_decompose_instability(
    task_text: str,
    models: Sequence[str] = (DEFAULT_MODEL,),
    runs: int = DEFAULT_DECOMPOSE_RUNS,
    case_id: str = "ad-hoc",
    perturb: bool = True,
    transcript_root: Path | None = None,
    client_factory: Callable[[RunConfig], ModelClient] | None = None,
    comparison_client: ModelClient | None = None,
) -> DecomposeInstabilityReport:
    """N draws per model over one task file, plus one perturbed draw.

    The perturbed draw shares its seed with the first baseline draw, so the only
    difference between them is the added bullet.
    """
    seeds = seeds_for(runs)
    per_model: list[DecomposeInstability] = []
    perturbation: DecomposePerturbation | None = None

    for model in models:
        snapshots = [
            decompose_once(
                task_text,
                RunKey(model=model, seed=seed, index=index),
                transcript_root=transcript_root,
                client_factory=client_factory,
            )
            for index, seed in enumerate(seeds)
        ]
        per_model.append(summarize_decompose(model, snapshots, comparison_client))

        if perturb and perturbation is None and snapshots:
            perturbed = decompose_once(
                append_unrelated_exclusion(task_text),
                RunKey(model=model, seed=seeds[0], index=0, perturbed=True),
                transcript_root=transcript_root,
                client_factory=client_factory,
            )
            moved = _moved_requirements(snapshots[0], perturbed)
            perturbation = DecomposePerturbation(
                name="append-unrelated-exclusion",
                watched_requirements=len(
                    set(snapshots[0].dispositions) & set(perturbed.dispositions)
                ),
                moved_requirements=moved,
            )

    return DecomposeInstabilityReport(
        provenance=MeasurementProvenance(
            case_id=case_id,
            task_digest=task_digest(task_text),
            models=list(models),
            runs_per_model=runs,
            seeds=seeds,
            perturbation="append-unrelated-exclusion" if perturbation else None,
            determinism_mode=Mode.RECORD.value,
        ),
        per_model=per_model,
        perturbation=perturbation,
    )
