"""The assembled static review pipeline (M7.4).

ONE pipeline, called by both consumers — the CLI (`acceptance check`) and the
benchmark (`benchmark/coverage.py::classify_case`). Before this existed the two
had drifted badly: every capability from M4 onward (test discovery/mapping,
evidence extraction, discrimination, strength, declaration comparison,
recommendations, verdict) was wired only into the benchmark path, so the CLI —
the very command used to dogfood the tool against its own changes — still ran
the M3-era chain and could not show test evidence or a verdict at all. Sharing
one function makes that divergence impossible by construction rather than by
keeping two copies in step.

Order follows §10.1: decompose → discover/map tests → extract, discriminate,
and classify test evidence → implementation coverage → unrequested changes and
their dispositions → resolve open questions → recommendations → declaration
comparison → completion verdict.
"""

from __future__ import annotations

from pathlib import Path

from acceptance.config import (
    DEFAULT_LINK_DISTANCE_THRESHOLD,
    DEFAULT_LINK_PAIR_BATCH_SIZE,
    ScopeExpansionPolicy,
    provenance_for,
)
from acceptance.coverage.classify import CoverageStatus, ImplementationCoverage, classify_coverage
from acceptance.coverage.declaration_comparison import (
    compare_declaration,
    declaration_mismatch_finding,
)
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.open_questions import (
    apply_open_question_resolutions,
    derive_obligations,
    resolve_open_questions,
)
from acceptance.coverage.recommendations import recommend_tests
from acceptance.coverage.unrequested import detect_unrequested_changes
from acceptance.defects.enumeration import enumerate_defects
from acceptance.defects.pair_mapping import DEFAULT_PAIR_BATCH_SIZE, judge_pairs
from acceptance.defects.support import (
    apply_derived_support,
    derive_support,
    tests_to_obligations,
)
from acceptance.evidence.discovery import discover_tests
from acceptance.evidence.extraction import extract_test_evidence
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.llm import ModelClient
from acceptance.requirement.declaration import declaration_absent_finding, parse_declaration
from acceptance.requirement.ledger import LedgerEntry
from acceptance.requirement.linking import link_duplicate_obligations
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.rerun import (
    carried_recommendations,
    compute_delta,
    task_source_for,
)
from acceptance.review_state import (
    UNREQUESTED_CHANGE,
    UNUSABLE_ANSWER,
    ChangeSet,
    Finding,
    Link,
    Obligation,
    Review,
    UnrequestedChangeDisposition,
)
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog
from acceptance.verdict import derive_verdict

_SEVERITY_BY_STATUS = {
    CoverageStatus.NOT_ADDRESSED: "high",
    CoverageStatus.PARTIALLY_ADDRESSED: "medium",
    CoverageStatus.UNCLEAR: "low",
    CoverageStatus.REQUIRES_NON_CODE_EVIDENCE: "low",
}

# An in_service change is accepted; separable should be split; risky demands
# scrutiny — so severity tracks disposition, not the change's raw kind.
_SEVERITY_BY_DISPOSITION = {
    UnrequestedChangeDisposition.IN_SERVICE: "low",
    UnrequestedChangeDisposition.SEPARABLE: "medium",
    UnrequestedChangeDisposition.RISKY: "high",
}


def coverage_finding(obligation: Obligation, coverage: ImplementationCoverage) -> Finding:
    if coverage.diff_refs:
        links = [
            Link(kind="code", ref=f"{ref.file}#{ref.hunk_header}", text=coverage.rationale)
            for ref in coverage.diff_refs
        ]
    else:
        links = [Link(kind="requirement", ref=obligation.id, text=obligation.description)]
    return Finding(
        type="coverage_gap",
        severity=_SEVERITY_BY_STATUS[coverage.status],
        description=coverage.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=links,
        related_obligation=obligation.description,
    )


def _apply_indeterminate(
    obligations: list[Obligation], unusable: UnusableAnswerLog
) -> list[Obligation]:
    """Mark obligations whose judgment was never obtained as `indeterminate`.

    Only the evidence axis: `indeterminate` says "we did not obtain this
    judgment", which is exactly what an unusable answer means. `verdict.py`
    already routes it to `unable_to_determine` and lists it as an escalation
    candidate, so a review that could not read part of its own reviewer cannot
    come back clean.
    """
    if not unusable.indeterminate_obligations:
        return obligations
    return [
        obligation.model_copy(update={"evidence_class": "indeterminate"})
        if obligation.id in unusable.indeterminate_obligations
        else obligation
        for obligation in obligations
    ]


def _in_original_order(original: list[Obligation], updated: list[Obligation]) -> list[Obligation]:
    """Re-key `updated` back onto `original`'s order.

    Every stage that judges a SUBSET writes back by concatenation, which puts
    the held-out obligations last and reorders the report for no reason the
    reader can see. That mattered little when one derived-question obligation
    was held out; #266 holds out every obligation a stage does not apply to, so
    the report's numbering would otherwise reshuffle according to which stage
    ran. Order is the mandate's, throughout.
    """
    by_id = {obligation.id: obligation for obligation in updated}
    return [by_id.get(obligation.id, obligation) for obligation in original]


def unusable_answer_finding(answer: UnusableAnswer) -> Finding:
    """Name the stage and the id, so a reader can tell which judgment is missing.

    Deliberately not advisory. An unrequested change or a declaration overclaim
    is about the delivered work and leaves the verdict alone; this is about the
    review itself failing to answer a question it asked, which is precisely the
    thing a reader must not mistake for a clean result.
    """
    # `reason` is what distinguishes the cases, so it has to reach the reader.
    # Without it every unusable answer is described as an id "never supplied",
    # which is true only of the original case — it is already wrong for #204's
    # no-linking rejection, where the response minted the id itself, and
    # `UnusableAnswer.reason` exists precisely because "a reader seeing only
    # `field=obligation_id` could not tell what was wrong with it". A reader told
    # the wrong story about why a judgment is missing cannot act on it.
    if answer.reason:
        description = (
            f"The {answer.stage} stage has no usable judgment for "
            f"{answer.returned_id!r} ({answer.field!r}): {answer.reason}."
        )
    else:
        description = (
            f"The {answer.stage} stage returned {answer.returned_id!r} for "
            f"{answer.field!r}, which was never supplied to that call. The "
            "judgment it was meant to carry was not obtained."
        )
    return Finding(
        type=UNUSABLE_ANSWER,
        severity="major",
        description=description,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref=answer.returned_id, text=answer.stage)],
    )


def unrequested_finding(dispositioned: DispositionedChange) -> Finding | None:
    change = dispositioned.change
    # No diff location to point to means nothing a human can act on; the
    # required-link invariant (Finding._require_at_least_one_link) would
    # reject it anyway, so skip rather than fabricate a link.
    if not change.diff_refs:
        return None
    return Finding(
        type=UNREQUESTED_CHANGE,
        severity=_SEVERITY_BY_DISPOSITION[dispositioned.disposition],
        description=change.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[
            Link(kind="code", ref=f"{ref.file}#{ref.hunk_header}", text=change.rationale)
            for ref in change.diff_refs
        ],
        disposition=dispositioned.disposition,
        recommended_action=dispositioned.recommendation,
    )


def _apply_coverage_status(
    obligations: list[Obligation], coverages: list[ImplementationCoverage]
) -> list[Obligation]:
    """Record each obligation's §9.2 coverage status AND the code regions that
    satisfy it, so the report can render the implementation-coverage axis
    faithfully instead of inferring it from which findings happen to exist —
    findings are lossy here (an `addressed` obligation produces none, and so
    does an unanalyzed one, yet they mean opposite things). Carrying the refs
    is what lets the review say *where* an obligation was satisfied, not just
    that it was."""
    coverage_by_id = {c.obligation_id: c for c in coverages}
    updated = []
    for obligation in obligations:
        coverage = coverage_by_id.get(obligation.id)
        updated.append(
            obligation.model_copy(
                update={
                    "coverage_status": coverage.status.value if coverage else None,
                    "coverage_refs": (
                        [f"{ref.file}#{ref.hunk_header}" for ref in coverage.diff_refs]
                        if coverage
                        else []
                    ),
                    # #153: what the completeness claim covered, for a boundary
                    # obligation confirmed by non-violation.
                    "scope_examined": (
                        [f"{ref.file}#{ref.hunk_header}" for ref in coverage.scope_examined]
                        if coverage
                        else []
                    ),
                }
            )
        )
    return updated


def run_review(
    task_text: str,
    change_set: ChangeSet,
    repo: Path,
    client: ModelClient,
    reviewed_revision: str,
    declaration_text: str | None = None,
    policy: ScopeExpansionPolicy = ScopeExpansionPolicy.STRICT,
    pair_batch_size: int = DEFAULT_PAIR_BATCH_SIZE,
    link_pair_batch_size: int = DEFAULT_LINK_PAIR_BATCH_SIZE,
    link_distance_threshold: float | None = DEFAULT_LINK_DISTANCE_THRESHOLD,
    task_identifier: str = "<inline>",
    prior: Review | None = None,
    ledger_prior: LedgerEntry | None = None,
    ledger_sink: list | None = None,
) -> Review:
    """Run the full static review pipeline and return the assembled Review.

    With `prior`, this is an incremental re-run (M7.5): obligations the new work
    could not have affected keep their prior judgments and the per-obligation
    model stages are asked only about the rest. Decomposition is deliberately
    NOT skipped — the same task text hashes to the same request, so it replays
    from its transcript at no cost, and re-running it keeps the obligation set
    derived from one place rather than two.
    """
    # One log for the whole run: every stage that asks the model to echo back an
    # id we supplied reports the ids it could not honour here (#163). Built
    # before the first such stage, which is decomposition — it supplies the
    # requirement ids.
    unusable = UnusableAnswerLog()

    parsed = parse_task_file(task_text)
    # `ledger_prior` is a DIFFERENT kind of prior from `prior` above, and the two
    # are deliberately not merged. `prior` is a stored Review, selected by git
    # ancestry, and it carries JUDGEMENTS forward — the ratings over an obligation
    # set. `ledger_prior` is a decompose ledger entry, named explicitly by the
    # operator, and it carries the OBLIGATION SET itself. #269 exists because the
    # second was missing: a changed task invalidated the whole decomposition, so
    # judgements were being carried over a set that had been re-derived and
    # re-identified underneath them.
    derived = decompose(parsed, client, unusable, prior=ledger_prior)
    # Obligation determination is two stages (#144). Derivation accounts for each
    # requirement alone and cannot link (#204), so a requirement stated twice
    # yields two obligations; linking resolves them into one obligation named by
    # both requirements. `derived` is kept, not discarded — it is persisted as
    # provenance so a movement in the final set can be attributed to the stage
    # that caused it.
    decomposition = link_duplicate_obligations(
        derived, client, unusable, link_pair_batch_size, link_distance_threshold, ledger_prior
    )

    # Open-question resolution runs HERE, ahead of every judging stage, because
    # a question the diff resolves yields an obligation (#214) and that
    # obligation has to be mapped, judged and rated like any other. Run after
    # the evidence stages — where it sat until #214 — it would produce an
    # obligation nothing had judged, which is the silence the change exists to
    # remove. It depends only on the questions and the diff, so it is free to
    # move.
    resolutions = resolve_open_questions(decomposition.open_questions, change_set, client, unusable)
    open_questions = apply_open_question_resolutions(decomposition.open_questions, resolutions)
    question_obligations = derive_obligations(open_questions, resolutions)
    derived_ids = {obligation.id for obligation in question_obligations}
    obligations = decomposition.obligations + question_obligations

    # Defect enumeration runs HERE, before test discovery, and the position is
    # the point (#313). The stage must never see a test — a denominator chosen
    # by something that can see what is already covered drifts toward it, and a
    # thin enumeration then earns a strong rating (#252). Running it before any
    # test has been discovered makes that structural rather than a promise: at
    # this line there is no test evidence in existence for it to be handed.
    #
    # Advisory in this milestone. Nothing below reads `defect_sets`, and no
    # verdict or rating depends on it. That is DR-312 decision 5's staged
    # migration: landing enumeration beside the existing chain rather than in
    # place of it is what lets a later rating movement be attributed to one
    # cause instead of three.
    defect_sets = enumerate_defects(
        obligations,
        change_set,
        client,
        unusable,
        prior=list(ledger_prior.defect_sets) if ledger_prior is not None else None,
    )

    # Every obligation reaches every stage below (#293). There used to be a
    # narrowing here — `obligations_to_rederive`, which dropped any obligation
    # none of whose cited files the change touched, for BOTH review axes at once.
    # That predicate is gone, and so is the rating carry that replaced it: the
    # test-evidence class is derived arithmetic over pair verdicts now (#316), so
    # every criterion is classified on every run and there is nothing left here
    # to decide about reuse. What carries is one level down — the defect set and
    # the pair verdict, each on its own content digest (DR-312 decision 6).
    #
    # The rule that governed this is not gone, only relocated: if stage 1's
    # output moved, an unchanged id may now stand for a different set of merged
    # requirements, so no stored judgement about it can be trusted (#144). The
    # ledger enforces it for the parts that still carry.

    # Only obligations that REQUIRE test evidence reach the stages that gather
    # it (#266). Previously every obligation did, and the ones no test could
    # ever bear on were filtered out three stages later, at the recommendation
    # step — after the mapper had already chosen among them and the strength
    # classifier had already rated them. Two costs, both observed: the mapper
    # picked between obligations that were never candidates, and ratings were
    # produced for obligations whose ratings the report then discarded, which
    # surfaced as rating movement nobody could explain.
    needs_tests = [o for o in obligations if o.required_evidence.requires_tests]
    no_tests = [o for o in obligations if not o.required_evidence.requires_tests]

    discovered = discover_tests(repo, change_set)

    # Pair judgement runs HERE — after discovery, because it needs the tests, and
    # before the mapping chain below only so a reader meets the two questions in
    # the order #312 replaces them. It could sit anywhere after this line: nothing
    # below reads `pair_mapping`, and nothing in it reads the mapping chain.
    #
    # SHADOW, and that is the whole point of this milestone (#314). The verdicts
    # are recorded and reported; no rating, recommendation or completion verdict
    # is derived from them until #316 flips the source. DR-312 decision 5's
    # reasoning: land it beside the existing chain and a carry defect shows as a
    # discrepancy against a stable baseline, land it in place of the chain and an
    # unexpected rating has three candidate causes and nothing to attribute it to.
    pair_mapping = judge_pairs(
        defect_sets,
        discovered.tests,
        change_set,
        client,
        repo=repo,
        batch_size=pair_batch_size,
        unusable=unusable,
        prior=list(ledger_prior.pair_verdicts) if ledger_prior is not None else None,
    )

    # Handed back rather than written here: the pipeline does not own the run id,
    # the parent pointer or the file, and a stage that wrote to disk on the way
    # past would make the benchmark's own runs leave ledger entries behind.
    #
    # Handed back HERE rather than after enumeration, which is where it used to
    # sit, because the entry now carries the pair verdicts as well and they do
    # not exist until the line above. One hand-back, so a caller cannot write an
    # entry holding half of what the run produced — the same reason it moved off
    # linking when #313 added the defect sets.
    if ledger_sink is not None:
        ledger_sink.append((derived, decomposition, defect_sets, pair_mapping.verdicts))

    # The rating, derived rather than judged (#316). Three stages used to stand
    # here — map tests to criteria, judge whether they discriminate, classify the
    # strength — and all three are gone. What replaces them is arithmetic over
    # records this run already holds: the ways a change could fail each criterion
    # (#313) and whether each candidate test would fail on each of them (#314).
    #
    # No model call, so no seed, no transcript and no draw. A rating that moves
    # between two runs now has a moved input behind it, which is what makes a
    # movement attributable at all (#150).
    #
    # The rating carry is gone with them, and that is DR-312 decision 6 rather
    # than an omission: the parts that carry are the defect set and the pair
    # verdict, and the class over them is "free arithmetic over carried parts",
    # always recomputed. #292's anchored re-judgement is retired for the same
    # reason — it existed to stop a re-asked judge moving a rating for no reason,
    # and nothing is re-asked.
    support = derive_support(needs_tests, defect_sets, pair_mapping.verdicts, pair_mapping.unjudged)
    needs_tests = apply_derived_support(needs_tests, support)

    # Still extracted, and still structural. The declaration comparison below
    # reads it, so it outlives the two stages that used to (#316). Its criterion
    # links are the derived edge now — test → defect → obligation — rather than
    # the retired mapping stage's answer.
    test_evidence = extract_test_evidence(
        repo, discovered.tests, change_set, tests_to_obligations(support)
    )

    obligations = _in_original_order(obligations, needs_tests + no_tests)
    # After the derivation, deliberately: an obligation whose judgment was never
    # obtained must not carry a class inferred from its absence. A re-run cannot
    # improve a judgment it did not re-examine, and neither can a first run claim
    # one it never made.
    obligations = _apply_indeterminate(obligations, unusable)

    # A derived obligation is `addressed` by construction — its resolution had
    # to cite the hunks that answer the question, so the code is already located
    # and asking the coverage stage whether it exists is a category error. It is
    # held out of both the call and the write-back, since `_apply_coverage_status`
    # nulls the status of any obligation it has no record for.
    #
    # An obligation that requires no CODE evidence is held out for the same
    # reason from the other direction (#266): asking whether the change
    # addresses something the change was never asked to contain produces a
    # verdict about nothing.
    def _classifiable(obligation: Obligation) -> bool:
        return obligation.id not in derived_ids and obligation.required_evidence.requires_code

    to_classify = [o for o in obligations if _classifiable(o)]
    held_out = [o for o in obligations if not _classifiable(o)]
    coverages = classify_coverage(to_classify, change_set, client, unusable)
    obligations = _in_original_order(
        obligations, _apply_coverage_status(to_classify, coverages) + held_out
    )
    unrequested = detect_unrequested_changes(obligations, change_set, client, unusable)
    dispositioned = classify_dispositions(
        unrequested, obligations, coverages, change_set, policy, client
    )
    prescribed = recommend_tests(
        obligations, defect_sets, pair_mapping.verdicts, change_set, client, unusable
    )
    recommendations = prescribed.recommendations
    # Re-applied after the recommendation stage, not only before it (#275). The
    # first call above runs at strength time, and an obligation this stage was
    # asked about and got no answer for is marked `indeterminate` here — after
    # that first pass. Without the second application the mark would be recorded
    # in the log and never reach the obligation, so the verdict would read the
    # strength the classifier assigned and come back clean over a prescription
    # nobody obtained.
    obligations = _apply_indeterminate(obligations, unusable)

    obligations_by_id = {obligation.id: obligation for obligation in obligations}
    findings = [
        coverage_finding(obligations_by_id[coverage.obligation_id], coverage)
        for coverage in coverages
        if coverage.status != CoverageStatus.ADDRESSED
    ]

    delta = None
    if prior is not None:
        # No findings are carried any more, and that is a consequence of #293
        # rather than an omission. Findings here are coverage findings, and
        # coverage is now classified for every obligation on every run — so there
        # is no obligation this run failed to re-examine, and nothing whose gap
        # could be silently dropped. The wholesale `merge_carried_forward` that
        # used to do this had nothing left to carry once that narrowing went.
        #
        # Recommendations are the exception, and since #316 they are carried on
        # the DEFECT axis. Every criterion is classified on every run now and
        # every uncovered defect is prescribed for on every run, so the case this
        # used to cover — a criterion keeping a stored rating and therefore never
        # asked about — no longer exists. What is left is a defect the stage
        # asked about and got no answer for (#275); the prior run's prescription
        # for that same defect is still the right instruction, and without this
        # one omitted answer would delete a still-open instruction from the
        # report.
        prescribed_ids = {recommendation.defect_id for recommendation in recommendations}
        recommendations = recommendations + [
            recommendation
            for recommendation in carried_recommendations(prior, prescribed.unobtained)
            if recommendation.defect_id not in prescribed_ids
        ]
    findings.extend(
        finding
        for finding in (unrequested_finding(change) for change in dispositioned)
        if finding is not None
    )
    findings.extend(unusable_answer_finding(answer) for answer in unusable.answers)

    if declaration_text is not None:
        declaration = parse_declaration(declaration_text)
        mismatches = compare_declaration(
            declaration, obligations, change_set, test_evidence, client
        )
        findings.extend(declaration_mismatch_finding(m) for m in mismatches)
    else:
        declaration = None
        findings.append(declaration_absent_finding())

    completion = derive_verdict(
        obligations, findings, open_questions, decomposition.requirement_map
    )
    if prior is not None:
        delta = compute_delta(prior, obligations, completion.verdict.value)

    return Review(
        mode="local",
        reviewed_revision=reviewed_revision,
        task_source=task_source_for(task_text, task_identifier),
        delta=delta,
        # Stamped here, at the end, rather than accepted from the caller: only
        # after the calls have run does the client know which determinism
        # controls the provider honoured (#160).
        provenance=provenance_for(client),
        obligation_map=obligations,
        # Stage 1's output, kept as provenance (#144). No reader sees it; it is
        # what makes a movement in `obligation_map` attributable to derivation or
        # to linking rather than ambiguous between them.
        derived_obligation_map=derived.obligations,
        # Persisted, not re-derived: which requirements produced nothing is a
        # property of review state that every later stage and the report read
        # from one place (M1.2.r1).
        requirement_map=decomposition.requirement_map,
        open_questions=open_questions,
        defect_sets=defect_sets,
        pair_verdicts=pair_mapping.verdicts,
        unjudged_pairs=pair_mapping.unjudged,
        change_set=change_set,
        declaration=declaration,
        findings=findings,
        recommendations=recommendations,
        unobtained_recommendations=prescribed.unobtained,
        completion=completion,
    )
