"""A defect injection never attempted still has its pair counts stated (#350).

`not_mutable` and `not_attempted` are the common case, not the corner: on #340's
own Gate 2, 58 of 68 attempts were one or the other. No edit was built for such
a defect, so the run settled none of its pairs and held none back, and every
pair it has went to the judge — including one the judge was offered and never
answered, which still cost the call. Counting only the answered ones made the
injection section say "0 put to the model" for a defect the defect section, two
screens up, said had one.
"""

from __future__ import annotations

from acceptance.mutation.attempt import MutationAttempt, MutationOutcomeKind
from acceptance.report import render_report
from acceptance.review_state import (
    Defect,
    DefectSet,
    DefectType,
    Obligation,
    ObligationType,
    PairVerdict,
    Review,
    UnjudgedCause,
    UnjudgedPair,
)

_NOT_MUTABLE = "o1/no-span"
_NOT_ATTEMPTED = "o1/nothing-ran"


def _review() -> Review:
    return Review(
        mode="check",
        reviewed_revision="head",
        obligation_map=[
            Obligation(
                id="o1",
                description="d",
                type=ObligationType.FUNCTIONAL,
                importance="normal",
                explicit=True,
                observable_behavior="b",
            )
        ],
        defect_sets=[
            DefectSet(
                obligation_id="o1",
                defects=[
                    Defect(
                        id=defect_id,
                        obligation_id="o1",
                        type=DefectType.OTHER,
                        description=f"description of {defect_id}",
                    )
                    for defect_id in (_NOT_MUTABLE, _NOT_ATTEMPTED)
                ],
            )
        ],
        pair_verdicts=[
            PairVerdict(defect_id=_NOT_MUTABLE, test_id="t::a", kills=True, reason="r"),
            PairVerdict(defect_id=_NOT_MUTABLE, test_id="t::b", kills=False, reason="r"),
            PairVerdict(defect_id=_NOT_ATTEMPTED, test_id="t::a", kills=False, reason="r"),
        ],
        unjudged_pairs=[
            UnjudgedPair(
                defect_id=_NOT_MUTABLE,
                test_id="t::c",
                cause=UnjudgedCause.UNANSWERED,
                reason="offered to the judge and not answered",
            ),
            UnjudgedPair(
                defect_id=_NOT_ATTEMPTED,
                test_id="t::b",
                cause=UnjudgedCause.UNANSWERED,
                reason="offered to the judge and not answered",
            ),
        ],
        mutation_attempts=[
            MutationAttempt(
                defect_id=_NOT_MUTABLE,
                outcome=MutationOutcomeKind.NOT_MUTABLE,
                reason="the behaviour is absent, so there is no span to replace",
            ),
            MutationAttempt(
                defect_id=_NOT_ATTEMPTED,
                outcome=MutationOutcomeKind.NOT_ATTEMPTED,
                reason="no candidate test survived the control run",
            ),
        ],
    )


def _injection_entry(report: str, defect_id: str) -> list[str]:
    """The lines under one defect's heading in the injection section."""
    section = report.split("Defects injected, and which tests caught them:", 1)[1]
    lines = section.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().endswith(f"] {defect_id}"))
    entry = []
    for line in lines[start + 1 :]:
        if not line.startswith("    "):
            break
        entry.append(line.strip())
    return entry


def _pair_lines(entry: list[str]) -> list[str]:
    return [line for line in entry if line.startswith("pairs:")]


def test_a_not_mutable_defect_counts_every_pair_as_put_to_the_judge():
    entry = _injection_entry(render_report(_review()), _NOT_MUTABLE)
    assert _pair_lines(entry) == [
        (
            "pairs: 0 settled by the run, 3 put to the model, 0 dropped as not worth "
            "asking, 0 skipped once the defect was covered"
        )
    ]


def test_a_not_attempted_defect_counts_every_pair_as_put_to_the_judge():
    entry = _injection_entry(render_report(_review()), _NOT_ATTEMPTED)
    assert _pair_lines(entry) == [
        (
            "pairs: 0 settled by the run, 2 put to the model, 0 dropped as not worth "
            "asking, 0 skipped once the defect was covered"
        )
    ]


def test_the_two_sections_agree_on_how_many_pairs_went_to_the_judge():
    """The defect section states the asked count too. Two numbers for one fact
    is the inconsistency this file exists to prevent."""
    report = render_report(_review())
    defect_section = report.split("Defects injected", 1)[0]
    assert "pairs: 3 put to the model, 0 skipped" in defect_section
    assert "pairs: 2 put to the model, 0 skipped" in defect_section
