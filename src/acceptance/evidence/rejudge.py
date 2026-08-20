"""Which criteria are judged again, and which keep the rating already stored (#293).

The rule this replaces asked one question for both review axes: *was any file this
obligation cites touched?* File-level, and the docstring on it was honest that the
coarseness was deliberate — over-invalidating costs a re-derivation, under-
invalidating reports a stale judgement as current.

What it did not anticipate is that **re-deriving is not free of consequence**.
Appending a test to a module leaves every existing test in it byte-identical, and
made every criterion citing that module stale anyway: 33 came back a tier lower in
#269's Gate 2, and #291's Gate 2 reproduced it on a nine-line append. A rating
that falls because the judge was asked twice is not a rating.

So a criterion's test-evidence rating depends on **its own** three inputs — its
requirement text, the set of tests mapped to it, and the *contents* of those
tests — and it is judged again exactly when one of those moved.

**Why the contents have to be stored rather than recomputed.** `test_evidence`
holds pytest node ids. The source those ids named during the previous run is gone
by the time the next one asks, so there is nothing to compare a stored rating
against unless the previous run wrote down what it saw. That is
`Obligation.evidence_carry_key`, and it is why this needed a review-state field
rather than only a function.

**This decides the test-evidence axis and nothing else.** Implementation coverage
is a separate question with a separate answer, and after #293 that answer is
"always re-derive" — see `pipeline.py`. The two used to share a predicate and the
sharing was the defect: #167's Gate 2 produced a byte-identical mapped set with a
flipped judgement over it, so the axes demonstrably fail independently.
"""

from __future__ import annotations

import hashlib

from acceptance.carry import Decision, carry_key, decide
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.evidence.strength import EvidenceStrength
from acceptance.llm import ModelClient, inline_schema_refs
from acceptance.review_state import Obligation, Review

# Evidence-judgement behaviour that changes the rating without changing the
# request. Bump by hand, exactly as `DECOMPOSE_STAGE_LOGIC_VERSION` is bumped:
# the request key already covers the prompt, the schema, the model and the seed,
# and cannot see a change to what we do with an unchanged response — how a
# discrimination answer becomes a strength class, or when a rating is held.
# Deliberately an integer rather than a hash of the module, so a comment edit
# does not discard every stored rating.
EVIDENCE_STAGE_LOGIC_VERSION = 1


def test_source_digest(source: str) -> str:
    """Content address for one test's source text."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def mapped_test_digests(obligation: Obligation, sources: dict[str, str]) -> dict[str, str]:
    """Each mapped test's content digest, keyed by node id.

    A test that is mapped but was not discovered this run gets the digest of the
    empty string rather than being dropped. Dropping it would make a criterion
    that *lost* a test look unchanged — under-invalidation, the one failure the
    rule this replaces was never guilty of.
    """
    return {test: test_source_digest(sources.get(test, "")) for test in obligation.test_evidence}


def evidence_inputs(obligation: Obligation, digests: dict[str, str]) -> dict[str, object]:
    """The three inputs a criterion's rating depends on, and nothing else.

    Sorted, so two runs over the same review build the same key regardless of the
    order mapping happened to return tests in. The digest list is parallel to the
    id list, so a test whose id stays put but whose body was edited moves the key
    — the distinction the file-level rule could not draw.

    Takes digests rather than sources so that the key and
    `Obligation.mapped_test_digests` are computed from one value. If it recomputed
    from sources it could disagree with what was stored, and a carry decision that
    disagrees with the evidence recorded for it is worse than no carry at all.
    """
    mapped = sorted(digests)
    return {
        "requirement_text": obligation.description,
        "mapped_tests": mapped,
        "mapped_test_digests": [digests[test] for test in mapped],
    }


def rating_carry_key(obligation: Obligation, digests: dict[str, str], client: ModelClient) -> str:
    """This criterion's rating key: `carry.carry_key` with the evidence inputs.

    The response schema here is the UNCONSTRAINED `_Discrimination`, and the
    system prompt is the unanchored one, both deliberately — the same choice
    decomposition makes and for the same reason. The real request constrains
    `obligation_id` to the criteria in the batch and appends the anchor
    instructions when any criterion is anchored, so the request key depends on
    which *other* criteria are being judged. A rating discarded because a
    neighbour changed is precisely the churn this exists to remove
    (`docs/DR-269-carry-key-excludes-registry-context.md`).
    """
    # Imported here rather than at module scope: `discrimination` imports
    # `anchoring`, which imports this module's siblings, and a top-level import
    # closes that loop.
    from acceptance.evidence.discrimination import _SYSTEM_PROMPT, _Discrimination

    schema = {
        "name": _Discrimination.__name__,
        "schema": inline_schema_refs(_Discrimination.model_json_schema()),
    }
    return carry_key(
        system_prompt=_SYSTEM_PROMPT,
        response_schema=schema,
        model=client.model,
        temperature=client.temperature,
        seed=client.seed,
        stage_logic_version=EVIDENCE_STAGE_LOGIC_VERSION,
        inputs=evidence_inputs(obligation, digests),
    )


def sources_by_test_id(tests: list[DiscoveredTest]) -> dict[str, str]:
    """Each discovered test's own source, keyed by node id.

    Per test, never per file. The whole point of #293 is that a module holding a
    mapped test is not the unit of change; the test is.
    """
    return {test.test_id: test.source for test in tests}


def digests_by_test_id(tests: list[DiscoveredTest]) -> dict[str, str]:
    """Every discovered test's content digest, keyed by node id.

    What `anchoring.build_anchors` compares against the digests a prior review
    stored. Computed here, so the anchor and the carry decision are answering the
    same question with the same arithmetic rather than two implementations that
    agree until one is edited.
    """
    return {test.test_id: test_source_digest(test.source) for test in tests}


def decide_rating_carry(
    prior: Review | None,
    obligations: list[Obligation],
    tests: list[DiscoveredTest],
    client: ModelClient,
) -> dict[str, Decision]:
    """Per criterion, whether its stored rating still stands.

    Reached through `carry.decide` rather than by re-implementing the four checks
    (#286): the unit must still be present, re-deriving it must issue the same
    request, the stage logic must not have moved, and the stored result must still
    fit. `carry_key` folds the first three of those into one comparison; the
    fourth is `still_applies` below.

    A criterion the prior review never rated refuses with `NO_PRIOR`, which is a
    refusal and not a failure: a first review has nothing to carry, and every
    criterion is judged.
    """
    sources = sources_by_test_id(tests)
    prior_by_id = (
        {obligation.id: obligation for obligation in prior.obligation_map} if prior else {}
    )
    decisions: dict[str, Decision] = {}
    for obligation in obligations:
        previous = prior_by_id.get(obligation.id)
        digests = mapped_test_digests(obligation, sources)
        decisions[obligation.id] = decide(
            obligation.id,
            prior=previous,
            prior_key=previous.evidence_carry_key if previous else None,
            current_key=rating_carry_key(obligation, digests, client),
            # A stored rating only fits a criterion that HAS one. An obligation
            # the prior review knew but never rated — held out of the evidence
            # stages that run, or judged and never answered — has nothing to
            # carry, and reusing its empty rating would present "not judged" as a
            # judgement.
            still_applies=previous is not None and previous.evidence_class is not None,
        )
    return decisions


def carried_ids(decisions: dict[str, Decision]) -> set[str]:
    """The criteria keeping a stored rating, so they can be left out of the
    judgement request."""
    return {oid for oid, decision in decisions.items() if decision.carried}


def carried_strengths(
    decisions: dict[str, Decision], obligations: list[Obligation]
) -> list[EvidenceStrength]:
    """The stored rating for each carried criterion, as this stage's own result.

    Written as an `EvidenceStrength` rather than by copying the prior obligation
    wholesale, because only the rating carried. Everything else about the
    obligation — its coverage verdict, its citations — is this run's, and splicing
    a whole prior obligation in would present findings about an older head as
    current.

    `test_links` are this run's mapped tests, which is not a compromise: the
    criterion only carried because its mapped set and those tests' contents are
    byte-identical to what the stored rating was made about, so the two lists have
    the same members.
    """
    by_id = {obligation.id: obligation for obligation in obligations}
    results = []
    for obligation_id in sorted(carried_ids(decisions)):
        prior_obligation = decisions[obligation_id].prior
        fresh = by_id.get(obligation_id)
        if prior_obligation is None or fresh is None:
            continue
        results.append(
            EvidenceStrength(
                obligation_id=obligation_id,
                evidence_class=prior_obligation.evidence_class,
                explanation=(
                    "Rating kept from the previous review: this criterion's "
                    "requirement text, mapped tests and those tests' contents are "
                    "all unchanged, so it was not judged again."
                ),
                test_links=sorted(fresh.test_evidence),
            )
        )
    return results


def label_carried_ratings(
    obligations: list[Obligation],
    decisions: dict[str, Decision],
    prior: Review | None,
) -> list[Obligation]:
    """Mark the criteria whose rating this run reused rather than re-derived.

    `carried_forward_from` used to mean "this obligation's whole judgement is from
    an older head", because a re-run carried an obligation wholesale or not at
    all. After #293 the axes are decided separately and only the test-evidence
    rating can carry, so the field means that and only that. Implementation
    coverage is always this run's.

    Kept, rather than dropped along with the wholesale carry, because it is the
    disclosure: a reader has to be able to tell which parts of a review were
    actually re-examined, and a rating nobody asked about this run is exactly the
    part that would otherwise read as fresh. The original revision is preserved
    when a carried rating carries again, so the label names where the rating was
    established rather than the last run that happened to keep it.
    """
    if prior is None:
        return obligations
    carried = carried_ids(decisions)
    updated = []
    for obligation in obligations:
        if obligation.id not in carried:
            updated.append(obligation)
            continue
        previous = decisions[obligation.id].prior
        established = getattr(previous, "carried_forward_from", None) or prior.reviewed_revision
        updated.append(obligation.model_copy(update={"carried_forward_from": established}))
    return updated


def apply_carry_keys(
    obligations: list[Obligation], tests: list[DiscoveredTest], client: ModelClient
) -> list[Obligation]:
    """Record what each criterion's rating was derived from, for the next run.

    Written for every criterion, carried or judged. A carried one recomputes to
    the same key by construction — that is why it carried — so writing it is free
    and keeps the field's meaning uniform: it always describes the inputs behind
    the rating this review is reporting.
    """
    sources = sources_by_test_id(tests)
    updated = []
    for obligation in obligations:
        digests = mapped_test_digests(obligation, sources)
        updated.append(
            obligation.model_copy(
                update={
                    "evidence_carry_key": rating_carry_key(obligation, digests, client),
                    "mapped_test_digests": digests,
                }
            )
        )
    return updated
