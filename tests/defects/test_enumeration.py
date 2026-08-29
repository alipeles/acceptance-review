"""Defect enumeration: what is recorded, what is never shown, what carries (#313).

The stage records — per criterion, before any test is looked at — the concrete
ways the delivered code could plausibly fail that criterion. Three properties
carry the design and each has its own test below:

- **the stage is never shown a test**, which is the #252 mitigation and the
  reason the whole thing is worth building;
- **an empty set is a real answer**, carrying its reason, rather than an
  invitation to invent a defect (#270);
- **a set carries** while its criterion's text and the contents of the regions
  it implicates are both unchanged, and re-derives wholesale when either moves.

The last group is the wiring: the pipeline really calls this, the ledger really
carries it, and nothing it records moves a verdict or a rating.
"""

from __future__ import annotations

from acceptance.change.diff import extract_change_set
from acceptance.defects.enumeration import (
    enumerate_defects,
    non_test_changes,
    obligation_text,
)
from acceptance.defects.taxonomy import CHECKLIST, CORE, checklist_for, enumerable
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.review_state import (
    ChangeSet,
    DefectType,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
)
from tests.support import client_dispatching

_PRORATE = "+def prorate(monthly, days):\n+    return monthly / 30\n"
_TEST_SOURCE = "+def test_prorate():\n+    assert prorate(300, 31) > 0\n"


def _hunk(content: str) -> DiffHunk:
    return DiffHunk(
        header="@@ -1 +1 @@", old_start=1, old_lines=1, new_start=1, new_lines=2, content=content
    )


def _change_set(source: str = _PRORATE, with_test: bool = True) -> ChangeSet:
    files = [
        FileChange(path="billing.py", status="modified", category="source", hunks=[_hunk(source)])
    ]
    if with_test:
        files.append(
            FileChange(
                path="test_billing.py",
                status="added",
                category="test",
                hunks=[_hunk(_TEST_SOURCE)],
            )
        )
    return ChangeSet(base_revision="base", head_revision="head", files=files)


def _obligation(
    obligation_id: str = "daily-rate",
    description: str = "The daily rate is the monthly price divided by the days in that month.",
    obligation_type: ObligationType = ObligationType.FUNCTIONAL,
) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=obligation_type,
        importance="normal",
        explicit=True,
        observable_behavior="prorate(300, 31) uses 31 as the divisor",
    )


def _answer(defects: list[dict], reason: str = "") -> dict:
    return {"_Enumeration": {"obligation_id": "", "defects": defects, "reason": reason}}


def _defect(
    slug: str = "thirty-day-month",
    defect_type: str = DefectType.QUALIFIER_IGNORED.value,
    code_refs: list[str] | None = None,
) -> dict:
    return {
        "slug": slug,
        "type": defect_type,
        "description": "The divisor is hard-coded to 30, so February is wrong.",
        "code_refs": ["billing.py#0"] if code_refs is None else code_refs,
    }


# --- the stage is never shown a test ---------------------------------------


def test_the_enumerator_is_given_no_test():
    """The #252 mitigation, asserted on the request as sent.

    A denominator chosen by something that can see what is already covered
    drifts toward it, and a thin enumeration then earns a strong rating. So this
    checks the prompt the stage actually built, not that a filter function
    exists: a correct filter the stage forgets to call reads identically from
    the outside.
    """
    capture: list = []
    client = client_dispatching(_answer([_defect()]), capture=capture)

    enumerate_defects([_obligation()], _change_set(with_test=True), client)

    assert capture, "the stage issued no call, so there is no request to inspect"
    prompt = capture[0]["prompt"]
    assert "billing.py" in prompt, "the production change was not shown either"
    assert "test_billing.py" not in prompt
    assert "test_prorate" not in prompt


def test_the_filter_removes_test_files_and_keeps_everything_else():
    """`non_test_changes` on its own, so a failure says which half broke."""
    filtered = non_test_changes(_change_set(with_test=True))

    assert [file.path for file in filtered.files] == ["billing.py"]


# --- an empty set is a real answer -----------------------------------------


def test_a_criterion_with_no_plausible_defect_yields_an_empty_set_with_its_reason():
    """#270's shape: an obligation true by construction earns no defect.

    The failure this guards against is an invented defect — one that would be
    counted in a denominator and make the criterion look better tested than it
    is. So it asserts both halves: nothing invented, and a reason present.
    """
    client = client_dispatching(
        _answer([], reason="The type system makes this true by construction.")
    )

    sets = enumerate_defects([_obligation()], _change_set(), client)

    assert len(sets) == 1
    assert sets[0].defects == []
    assert sets[0].reason == "The type system makes this true by construction."


def test_an_empty_set_with_no_reason_is_recorded_as_one_rather_than_left_blank():
    """ "Found nothing, here is why" and "answered nothing" must stay apart.

    An empty set with a blank reason is indistinguishable from a stage that did
    not run, which is the failure #275 names on the recommendation stage.
    """
    client = client_dispatching(_answer([], reason="   "))

    sets = enumerate_defects([_obligation()], _change_set(), client)

    assert sets[0].defects == []
    assert sets[0].reason, "an empty set was recorded with no reason at all"


def test_a_set_that_found_defects_carries_no_empty_set_reason():
    """The reason field belongs to the empty case alone; carrying one alongside
    defects would read as a caveat on findings that have none."""
    client = client_dispatching(_answer([_defect()], reason="left over"))

    sets = enumerate_defects([_obligation()], _change_set(), client)

    assert sets[0].defects
    assert sets[0].reason == ""


# --- the records themselves -------------------------------------------------


def test_every_defect_id_is_unique_within_the_review():
    """Uniqueness is composed in code, not taken from the answer.

    Two criteria about the same code invite the same model-chosen slug, and a
    duplicate id would let a later consumer that refers to defects by id join
    one criterion's defect onto another's.
    """
    client = client_dispatching(_answer([_defect(slug="same"), _defect(slug="same")]))

    sets = enumerate_defects(
        [_obligation("first"), _obligation("second", description="A different criterion.")],
        _change_set(),
        client,
    )

    ids = [defect.id for entry in sets for defect in entry.defects]
    assert len(ids) == 4
    assert len(set(ids)) == 4, f"ids collided: {ids}"


def test_each_defect_carries_its_criterion_a_type_a_description_and_its_code_regions():
    client = client_dispatching(_answer([_defect()]))

    defect = enumerate_defects([_obligation()], _change_set(), client)[0].defects[0]

    assert defect.obligation_id == "daily-rate"
    assert defect.type is DefectType.QUALIFIER_IGNORED
    assert defect.description
    assert defect.code_refs == ["billing.py#0"]


def test_a_code_reference_the_change_set_does_not_contain_is_dropped():
    """A defect may cite only regions it was actually shown, so a link is a link
    to something (§13.6)."""
    client = client_dispatching(_answer([_defect(code_refs=["billing.py#0", "invented.py#9"])]))

    defect = enumerate_defects([_obligation()], _change_set(), client)[0].defects[0]

    assert defect.code_refs == ["billing.py#0"]


# --- the checklist ----------------------------------------------------------


def test_the_checklist_walked_is_the_one_for_that_criterion_s_type():
    capture: list = []
    client = client_dispatching(_answer([_defect()]), capture=capture)

    enumerate_defects([_obligation(obligation_type=ObligationType.BOUNDARY)], _change_set(), client)

    prompt = capture[0]["prompt"]
    assert DefectType.BOUNDARY_WRONG_SIDE.value in prompt
    assert DefectType.ERROR_SWALLOWED.value not in prompt, (
        "another obligation type's checklist reached this call"
    )


def test_the_core_checklist_is_walked_for_every_enumerable_type():
    for obligation_type in CHECKLIST:
        assert set(CORE) <= set(checklist_for(obligation_type)), obligation_type


def test_the_escape_is_offered_alongside_the_checklist():
    """DR-312 decision 4: a defect that fits no entry is recorded as `other`
    rather than forced into the nearest slot."""
    capture: list = []
    client = client_dispatching(_answer([_defect()]), capture=capture)

    enumerate_defects([_obligation()], _change_set(), client)

    assert DefectType.OTHER.value in capture[0]["prompt"]


def test_a_defect_typed_other_is_recorded_as_such():
    client = client_dispatching(_answer([_defect(defect_type=DefectType.OTHER.value)]))

    defect = enumerate_defects([_obligation()], _change_set(), client)[0].defects[0]

    assert defect.type is DefectType.OTHER


def test_a_test_demand_criterion_gets_no_set_at_all_rather_than_an_empty_one():
    """DR-313 decision 2, and the distinction it turns on.

    The enumerator may never see a test, and a `test_demand` obligation is about
    a test — so it is excluded. Excluded is not the same as empty: an empty set
    claims "looked, found no plausible static defect", which would be a false
    negative wearing a reason.
    """
    client = client_dispatching(_answer([_defect()]))

    sets = enumerate_defects(
        [
            _obligation("behaviour"),
            _obligation("demand", obligation_type=ObligationType.TEST_DEMAND),
            _obligation("judgement", obligation_type=ObligationType.HUMAN_REVIEW),
        ],
        _change_set(),
        client,
    )

    assert [entry.obligation_id for entry in sets] == ["behaviour"]
    assert not enumerable(ObligationType.TEST_DEMAND)
    assert not enumerable(ObligationType.HUMAN_REVIEW)


# --- carry ------------------------------------------------------------------


def _enumerated(client, obligations, change_set, prior=None):
    return enumerate_defects(obligations, change_set, client, prior=prior)


class _Counting:
    """A client that answers as `client_dispatching` does and counts the calls."""

    def __init__(self, answer: dict):
        self.calls = 0
        capture: list = []
        self._capture = capture
        self.client = client_dispatching(answer, capture=capture)
        original = self.client.complete

        def counted(*args, **kwargs):
            if kwargs.get("stage") == "defect enumeration":
                self.calls += 1
            return original(*args, **kwargs)

        self.client.complete = counted  # type: ignore[method-assign]


def test_a_set_is_reused_when_the_criterion_and_its_implicated_regions_are_unchanged():
    """The mandate's carry rule, exercised as two continued runs.

    Asserted on the call count, not only on the result: a set that came back
    identical because the stage re-asked and got the same answer is not a
    carried set, and the whole point of the carry is the call not being made.
    """
    counting = _Counting(_answer([_defect()]))
    obligations = [_obligation()]
    change_set = _change_set()

    first = _enumerated(counting.client, obligations, change_set)
    assert counting.calls == 1

    second = _enumerated(counting.client, obligations, change_set, prior=first)

    assert counting.calls == 1, "the set was produced again although nothing moved"
    assert second[0].carried_from, "a reused set does not say it was reused"
    assert [d.description for d in second[0].defects] == [d.description for d in first[0].defects]


def test_a_criterion_whose_text_changed_keeps_no_part_of_its_earlier_set():
    counting = _Counting(_answer([_defect()]))
    change_set = _change_set()

    first = _enumerated(counting.client, [_obligation()], change_set)
    reworded = [_obligation(description="The daily rate uses the calendar month's real length.")]
    second = _enumerated(counting.client, reworded, change_set, prior=first)

    assert counting.calls == 2, "a reworded criterion was not re-enumerated"
    assert second[0].carried_from is None
    assert second[0].carry_key != first[0].carry_key


def test_changing_one_criterion_leaves_every_other_criterion_s_set_reused():
    """The carry is per criterion, so one rewording costs one call.

    This is the property that makes `--continue` worth having: without it a
    single edited bullet re-enumerates the whole mandate, and the figures either
    side of the edit stop being comparable.
    """
    counting = _Counting(_answer([_defect()]))
    change_set = _change_set()
    first_run = [_obligation("a"), _obligation("b", description="A second criterion entirely.")]

    first = _enumerated(counting.client, first_run, change_set)
    assert counting.calls == 2

    second_run = [_obligation("a"), _obligation("b", description="A second criterion, reworded.")]
    second = _enumerated(counting.client, second_run, change_set, prior=first)

    assert counting.calls == 3, "an untouched criterion was re-enumerated"
    by_id = {entry.obligation_id: entry for entry in second}
    assert by_id["a"].carried_from
    assert by_id["b"].carried_from is None


def test_a_set_is_produced_again_when_the_contents_of_its_implicated_region_change():
    """The other half of the rule, and the half a file-touch comparison misses.

    #293 deleted the touched-file test because it fires when a byte-identical
    region moves within a file. This is keyed on the region's CONTENTS, so it
    fires when — and only when — the implicated code really changed.
    """
    counting = _Counting(_answer([_defect()]))

    first = _enumerated(counting.client, [_obligation()], _change_set())
    moved = _change_set(source="+def prorate(monthly, days):\n+    return monthly / days\n")
    second = _enumerated(counting.client, [_obligation()], moved, prior=first)

    assert counting.calls == 2
    assert second[0].carried_from is None


def test_a_carried_set_is_re_identified_onto_this_run_s_criterion_id():
    """Ids are model-chosen and move; the carry matches on text.

    Without the re-identification a carried set would keep the previous run's
    obligation id and every consumer that joins by id would silently lose it.
    """
    counting = _Counting(_answer([_defect()]))
    change_set = _change_set()

    first = _enumerated(counting.client, [_obligation("old-id")], change_set)
    second = _enumerated(counting.client, [_obligation("new-id")], change_set, prior=first)

    assert counting.calls == 1
    assert second[0].obligation_id == "new-id"
    assert {defect.obligation_id for defect in second[0].defects} == {"new-id"}


def test_the_carry_identity_is_the_text_the_enumerator_was_shown():
    """Neither more nor less: a field the prompt never renders would
    re-enumerate on a change that could not have altered the answer."""
    same = obligation_text(_obligation("one"))
    renamed = obligation_text(_obligation("two"))
    reworded = obligation_text(_obligation("one", description="Something else."))

    assert same == renamed
    assert same != reworded


# --- wiring -----------------------------------------------------------------


_TASK = (
    "# Task\nThe billing export prorates a partial month.\n\n"
    "## Constraints\n- The daily rate is the monthly price divided by the days in that month\n"
)

_QUOTE = "The daily rate is the monthly price divided by the days in that month"

# The decomposition the wiring tests run over. Supplied rather than left to the
# double's empty default: with no obligations the pipeline has nothing to
# enumerate against, and every assertion below would pass vacuously on a review
# that never reached this stage.
_DECOMPOSITION = {
    "obligations": [
        {
            "id": "daily-rate",
            "description": f"{_QUOTE}.",
            "type": "functional",
            "importance": "normal",
            "explicit": True,
            "observable_behavior": "prorate(300, 31) divides by 31",
            "source_quote": _QUOTE,
        }
    ],
    "open_questions": [],
    "requirement_dispositions": [],
}


def _repo(tmp_path):
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir(parents=True)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (repo / "billing.py").write_text("def prorate(monthly, days):\n    return monthly\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (repo / "billing.py").write_text("def prorate(monthly, days):\n    return monthly / 30\n")
    git("add", "-A")
    git("commit", "-qm", "head")
    return repo, base, git("rev-parse", "HEAD")


def _reviewed(tmp_path, answer: dict | None = None):
    repo, base, head = _repo(tmp_path)
    client = client_dispatching(
        {"_Decomposition": _DECOMPOSITION, **(answer or _answer([_defect(code_refs=[])]))}
    )
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
    )


def test_the_pipeline_really_calls_the_enumerator(tmp_path):
    """The wiring, not the function.

    Defect injection has repeatedly found a helper with a good unit test that
    the pipeline never calls (CLAUDE.md), so the acceptance is asserted on a
    real `run_review` rather than on `enumerate_defects` alone.
    """
    review = _reviewed(tmp_path)

    assert review.defect_sets, "the pipeline produced no defect sets"
    assert any(entry.defects for entry in review.defect_sets)


def test_the_review_reports_the_recorded_ways_of_failing(tmp_path):
    review = _reviewed(tmp_path)

    rendered = render_report(review)

    assert "Ways the change could fail a criterion" in rendered
    for entry in review.defect_sets:
        for defect in entry.defects:
            assert defect.id in rendered, "a defect is not named by its identifier in the report"
            assert defect.type.value in rendered


def test_the_report_says_when_a_set_was_reused_rather_than_produced_again(tmp_path):
    review = _reviewed(tmp_path)
    carried = review.model_copy(
        update={
            "defect_sets": [
                entry.model_copy(update={"carried_from": "an-earlier-key"})
                for entry in review.defect_sets
            ]
        }
    )

    assert "reused from an earlier run" in render_report(carried)
    assert "reused from an earlier run" not in render_report(review)


def test_recording_ways_of_failing_changes_no_verdict_and_no_rating(tmp_path):
    """The advisory guarantee, checked by difference.

    Two reviews over the same input, one whose enumerator found defects and one
    whose found none. Every part of the review except `defect_sets` must be
    identical — that is what "advisory" means, and it is what makes a later
    rating movement attributable to the stage that caused it (DR-312 decision 5).
    """
    with_defects = _reviewed(tmp_path / "a", _answer([_defect(code_refs=[])]))
    without = _reviewed(tmp_path / "b", _answer([], reason="Nothing plausible."))

    assert any(entry.defects for entry in with_defects.defect_sets)
    assert not any(entry.defects for entry in without.defect_sets)

    def apart(review):
        return review.model_copy(update={"defect_sets": []}).to_canonical_json()

    assert apart(with_defects) == apart(without)


def test_the_enumerated_sets_survive_a_round_trip_through_persisted_state(tmp_path):
    """Defects persist with the rest of the review, unchanged."""
    from acceptance.review_state import Review

    review = _reviewed(tmp_path)

    reloaded = Review.model_validate_json(review.to_canonical_json())

    assert reloaded.defect_sets == review.defect_sets
    assert reloaded.to_canonical_json() == review.to_canonical_json()


def test_two_runs_over_the_same_input_agree_byte_for_byte(tmp_path):
    """M0.5, over the stage this issue adds."""
    first = _reviewed(tmp_path / "one")
    second = _reviewed(tmp_path / "two")

    assert first.to_canonical_json() == second.to_canonical_json()
    assert render_report(first) == render_report(second)
