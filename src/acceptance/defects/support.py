"""A criterion's §9.3 evidence class, derived from pair verdicts (#316).

This is the join DR-312 decision 4 describes, and it replaces a model call with
arithmetic. The old chain asked a judge *"do these tests discriminate for this
obligation?"* and took the answer; this reduces over facts already recorded —
which ways a change could fail the criterion (`DefectSet`, #313), and which
candidate tests would fail on each (`PairVerdict`, #314).

Three properties follow from deriving rather than judging, and each is the fix
for a named defect:

- **The denominator is disclosed.** A class is meaningless without the count it
  reduced over, so `DerivedSupport` carries the counts and every rendering is
  bound to them (DR-312 resolved question 3). No minimum-enumeration floor: any
  threshold is arbitrary and invites gaming from the other side, and a reader
  given "1 of 1" can weigh a thin enumeration themselves.
- **It is deterministic.** No model call, no seed, no transcript. Two runs over
  the same verdicts produce the same classes, so a rating that moves has a moved
  input behind it rather than a redrawn sample (#150).
- **An unjudged pair cannot read as a covered one, or as an uncovered one.**
  DR-164's trap is a shed judgement that looks like a verdict; here a defect
  with no verdict at all is neither covered nor survived but *unknown*, and
  `_class_for` refuses to claim anything an unknown could overturn.

## What each defect is, before any criterion is classified

    covered    some verdict says a test would fail on it
    uncovered  no verdict says a test would fail on it — either every pair
               survived, or the prefilter PROVED no path, or it was never
               paired with a test at all
    unknown    it has a pair that was offered to the judge and never answered

## The rules

    all defects covered                  -> strongly_supported
    some covered, none unknown           -> partially_supported
    some covered, some unknown           -> partially_supported
    none covered, none unknown           -> unsupported
    none covered, some unknown           -> indeterminate

**`nominally_supported` is not produced here, deliberately.** §9.3 defines it as
a present, *relevant-looking* test that catches nothing — a criterion where some
test appears to cover the behaviour but would not fail if it broke. Telling that
apart from "no test goes near this at all" needs the judge to say which of two
things it meant by *no*: the test exercises the code but asserts nothing that
would catch the defect, or it does not exercise it. The pair judge answers one
yes/no question, so both come back identical and the review records nothing that
separates them.

The class is not worth a third answer. It would change the response shape, which
re-judges every stored verdict once and reopens the shape DR-314 measured; and
when M8.4's defect injection replaces the static prediction, the distinction
becomes unmeasurable in principle — an injected defect either fails a test or it
does not, and a test that runs but does not notice is indistinguishable from one
that never ran. A criterion no test would fail on is reported `unsupported`,
which is the true and useful half of what the pair says.

The name stays in the §9.3 vocabulary; nothing in the review produces it now.

## Why an unknown defect does not count as uncovered

Counting it as uncovered would understate the rating and prescribe a test for a
defect that may already be killed — #250 and #287, the prescribe-what-exists
failure #312 exists to remove. Counting it as covered would overstate it and
hide a real gap.

The third line above is the interesting one. With one defect killed and one
unjudged, *"some are covered"* is true whatever the unjudged pair turns out to
be, so `partially_supported` is a claim the evidence carries; `strongly` is not,
because an unknown could overturn it. That is §3.7's bounded-positive rule
applied to one criterion.

## Why every input is something a stored review keeps

This function used to take the discovered tests, to decide the no-test case.
That made the class depend on something a `Review` does not store, so no
consumer could recompute a rating from the review it was rendered in — and a
rating nobody can recompute is one nobody can check.
"""

from __future__ import annotations

from pydantic import Field

from acceptance.evidence_tier import EvidenceTier
from acceptance.model_base import PersistableModel
from acceptance.review_state import (
    DefectSet,
    EvidenceClassification,
    Obligation,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)


class DerivedSupport(PersistableModel):
    """One criterion's evidence class and the counts it was reduced over.

    The counts are stored rather than recomputed at render time because the
    rendering must not be able to disagree with the class — a report that says
    `strongly_supported` beside "2 of 3" is worse than either alone. One
    computation, one record, every consumer reading the same numbers.
    """

    obligation_id: str
    evidence_class: EvidenceClassification
    explanation: str
    # pytest nodeids of the tests judged to fail on at least one of this
    # criterion's defects. This is DR-312 decision 4's derived edge — test →
    # defect → obligation — and it is what `Obligation.test_evidence` is
    # populated from now that no stage maps tests to obligations directly.
    test_links: list[str] = Field(default_factory=list)
    # The disclosed denominator. `enumerated` is the size of the criterion's
    # defect set; `covered` is how many of those some test would fail on;
    # `unknown` is how many carry no verdict at all.
    enumerated: int = 0
    covered: int = 0
    unknown: int = 0


def _class_for(covered: int, enumerated: int, unknown: int) -> EvidenceClassification:
    """The class the counts support, refusing anything an unknown could overturn.

    Written out rather than delegated to `evidence/classification.py`, which
    reduces the same shape but returns `nominally_supported` where this returns
    `unsupported`. The two are different vocabularies over the same numbers and
    sharing one function would hide that; the module docstring says why this one
    does not produce `nominally_supported`.
    """
    if covered == enumerated:
        return "strongly_supported"
    if covered:
        # True whatever an unknown turns out to be, so it holds either way.
        return "partially_supported"
    if unknown:
        return "indeterminate"
    return "unsupported"


def _explain(support_class: EvidenceClassification, covered: int, enumerated: int) -> str:
    if support_class == "no_plausible_defect":
        return (
            "No plausible static defect enumerated; test evidence is not obtainable at this tier."
        )
    if support_class == "unsupported":
        return (
            f"No candidate test would fail on any of the {enumerated} enumerated "
            "ways this change could fail the criterion."
        )
    if support_class == "indeterminate":
        return (
            f"Of {enumerated} enumerated ways this change could fail the criterion, none "
            "is known to be caught and at least one was never judged, so the criterion's "
            "test evidence cannot be classified."
        )
    return (
        f"Some candidate test would fail on {covered} of {enumerated} enumerated ways "
        "this change could fail the criterion (static prediction)."
    )


def derive_support(
    obligations: list[Obligation],
    defect_sets: list[DefectSet],
    verdicts: list[PairVerdict],
    unjudged: list[UnjudgedPair],
) -> list[DerivedSupport]:
    """Reduce pair verdicts to one evidence class per criterion.

    Every argument is a record a stored `Review` keeps, so any consumer holding
    a review can recompute what it was rendered with. See the module docstring
    for why that matters more than it sounds.
    """
    kills_by_defect: dict[str, list[str]] = {}
    unanswered_defects: set[str] = set()
    for verdict in verdicts:
        if verdict.kills:
            kills_by_defect.setdefault(verdict.defect_id, []).append(verdict.test_id)
    for entry in unjudged:
        # A pair the prefilter PROVED unreachable is not counted here. It is a
        # *survives* established statically, not a missing judgement — the
        # filter's whole contract is that it excludes only what it can prove
        # (#314). Counting it as unknown would make a filter doing its job
        # indistinguishable from a judge shedding work, and those have opposite
        # remedies.
        if entry.cause is not UnjudgedCause.PREFILTERED:
            unanswered_defects.add(entry.defect_id)

    sets_by_obligation = {defect_set.obligation_id: defect_set for defect_set in defect_sets}

    results: list[DerivedSupport] = []
    for obligation in obligations:
        defect_set = sets_by_obligation.get(obligation.id)
        if defect_set is None:
            # Not the same as an empty set with a reason: nothing looked at this
            # criterion, which is an absence of a judgement rather than one.
            results.append(
                DerivedSupport(
                    obligation_id=obligation.id,
                    evidence_class="indeterminate",
                    explanation=(
                        "No way this change could fail the criterion was enumerated for it, "
                        "so its test evidence cannot be classified."
                    ),
                )
            )
            continue

        if not defect_set.defects:
            # `DefectSet` already requires a reason on an empty set and forbids
            # one otherwise, so reaching here means the enumeration considered
            # the criterion and stands behind finding nothing.
            results.append(
                DerivedSupport(
                    obligation_id=obligation.id,
                    evidence_class="no_plausible_defect",
                    explanation=_explain("no_plausible_defect", 0, 0),
                )
            )
            continue

        covered_ids = [d.id for d in defect_set.defects if kills_by_defect.get(d.id)]
        # An unpaired defect is uncovered, not unknown. No test was offered
        # against it, so none can be claimed to catch it — and unlike a shed
        # judgement, there is no answer outstanding that could change that.
        unknown = sum(
            1
            for d in defect_set.defects
            if d.id in unanswered_defects and d.id not in kills_by_defect
        )
        enumerated = len(defect_set.defects)
        covered = len(covered_ids)
        support_class = _class_for(covered, enumerated, unknown)

        results.append(
            DerivedSupport(
                obligation_id=obligation.id,
                evidence_class=support_class,
                explanation=_explain(support_class, covered, enumerated),
                test_links=sorted({t for did in covered_ids for t in kills_by_defect[did]}),
                enumerated=enumerated,
                covered=covered,
                unknown=unknown,
            )
        )
    return results


def tests_to_obligations(results: list[DerivedSupport]) -> dict[str, list[str]]:
    """The derived edge, inverted: which criteria each test bears on.

    DR-312 decision 4 keeps test-to-obligation linkage as a *derived* edge —
    test → defect → obligation — rather than as a judgement of its own, and this
    is the only shape of it any consumer needs. `evidence/extraction.py` takes
    it in place of the retired mapping stage's result.
    """
    by_test: dict[str, list[str]] = {}
    for result in results:
        for test_id in result.test_links:
            by_test.setdefault(test_id, []).append(result.obligation_id)
    return {test_id: sorted(set(ids)) for test_id, ids in by_test.items()}


def apply_derived_support(
    obligations: list[Obligation], results: list[DerivedSupport]
) -> list[Obligation]:
    """Return copies of `obligations` carrying the derived class and its links.

    One write-back for both, deliberately. `evidence_class` and `test_evidence`
    used to be set by two stages that could disagree about the same criterion —
    a rating derived from tests the mapping stage had not linked. Derived
    together from one reduction, they cannot.
    """
    by_id = {result.obligation_id: result for result in results}
    updated = []
    for obligation in obligations:
        result = by_id.get(obligation.id)
        if result is None:
            updated.append(obligation)
            continue
        updated.append(
            obligation.model_copy(
                update={
                    "evidence_class": result.evidence_class,
                    "test_evidence": list(result.test_links),
                    "achieved_evidence_tier": EvidenceTier.STATIC,
                    # The class never travels without its denominator.
                    "enumerated_defects": result.enumerated,
                    "covered_defects": result.covered,
                }
            )
        )
    return updated


def uncovered_defects(
    defect_sets: list[DefectSet], verdicts: list[PairVerdict]
) -> list[tuple[str, str]]:
    """`(obligation_id, defect_id)` for every defect no test was judged to fail on.

    The recommendation stage's whole input, and the reason #250 and #287 cannot
    recur: a defect some test kills never appears here, so no prescription can
    ask for evidence the review already holds.

    A defect with no verdict at all IS included. It is not known to be covered,
    and prescribing a test for it is the conservative error — the alternative is
    silence about a defect nobody judged, which is the invisible gap #312 exists
    to remove.
    """
    killed = {verdict.defect_id for verdict in verdicts if verdict.kills}
    return [
        (defect_set.obligation_id, defect.id)
        for defect_set in defect_sets
        for defect in defect_set.defects
        if defect.id not in killed
    ]
