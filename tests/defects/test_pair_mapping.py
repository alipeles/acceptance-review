"""Judging (defect, test) pairs: what is asked, what carries, what stays advisory (#314).

Four properties carry this stage and each has its own group below:

- **every offered pair comes back with a verdict**, and one that does not is
  recorded rather than read as *survives* — the silent un-covering DR-314 chose
  this response shape to make visible;
- **a verdict carries** while its defect's content and its test's source are both
  unchanged, and is produced again when either moves;
- **adding one test costs that test's pairs and nothing else**, which is #312's
  headline behaviour and the thing carry exists for;
- **nothing it records moves a rating or the verdict**, because this milestone is
  shadow and an attributable migration depends on the baseline holding still.

The last group is the wiring: the pipeline really calls this, the ledger really
carries it, and the report really shows the comparison.
"""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

from acceptance.change.diff import extract_change_set
from acceptance.defects.pair_mapping import (
    DEFAULT_PAIR_BATCH_SIZE,
    defect_text,
    derive_support,
    judge_pairs,
    source_digest,
)
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.requirement.ledger import LedgerEntry
from acceptance.requirement.obligations import build_ledger_entry
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    DiffHunk,
    FileChange,
    Review,
    UnjudgedCause,
    UnjudgedPair,
)
from tests.support import client_dispatching

_DEFAULT_MODEL = "openai/gpt-5.4-mini"


def _offered(field: str, **kwargs) -> list[str]:
    """The ids this call offered for `field`, read off the schema it sent.

    `constrain` narrows each id field to a Literal of the ids the call actually
    supplied, so the outgoing schema IS the work list. Reading it back lets the
    double answer a call completely without being told the fixture's ids, and
    keeps it honest when they change.
    """
    schema = kwargs["response_format"]["json_schema"]["schema"]
    found: list[str] = []

    def walk(node, key=None):
        if isinstance(node, dict):
            if key == field and isinstance(node.get("enum"), list):
                found.extend(value for value in node["enum"] if value not in found)
            for name, value in node.items():
                walk(value, name if name not in ("properties", "$defs", "items") else key)
        elif isinstance(node, list):
            for item in node:
                walk(item, key)

    walk(schema)
    return found


class _Judge:
    """A double that answers every pair a call offers, and records what it was asked.

    `kills` decides the verdict for a given pair; the default kills nothing, so a
    test that cares about verdicts says so explicitly and one that cares about
    call counts is unaffected by the answer.
    """

    def __init__(self, kills=None, answer_all: bool = True):
        self.requests: list[dict[str, list[str]]] = []
        self._kills = kills or (lambda defect_id, test_id: False)
        self._answer_all = answer_all
        self.client = ModelClient(
            model=_DEFAULT_MODEL,
            mode=Mode.RECORD,
            store=TranscriptStore(_tmp()),
            completion_fn=self._completion_fn,
        )

    @property
    def calls(self) -> int:
        return len(self.requests)

    def pairs_asked(self) -> set[tuple[str, str]]:
        """Every pair offered across every call, as (defect id, test id)."""
        asked: set[tuple[str, str]] = set()
        for request in self.requests:
            for test_id in request["test_id"]:
                for defect_id in request["defect_id"]:
                    asked.add((defect_id, test_id))
        return asked

    def _completion_fn(self, **kwargs):
        tests = _offered("test_id", **kwargs)
        defects = _offered("defect_id", **kwargs)
        self.requests.append(
            {
                "test_id": tests,
                "defect_id": defects,
                "prompt": "\n".join(message["content"] for message in kwargs["messages"]),
                "schema": kwargs["response_format"]["json_schema"]["schema"],
            }
        )
        answered = [
            {
                "test_id": test_id,
                "defects": [
                    {
                        "defect_id": defect_id,
                        "fails": self._kills(defect_id, test_id),
                        "reason": "because",
                    }
                    for defect_id in defects
                ],
            }
            for test_id in tests
        ]
        if not self._answer_all:
            # Shed one judgement per test — the shape that matters, since a
            # request covers one test and an entry omitted from its `defects`
            # list is a pair offered and never answered.
            for entry in answered:
                entry["defects"] = entry["defects"][:-1]
        return _fake(json.dumps({"tests": answered}))


def _tmp() -> str:
    import tempfile

    return tempfile.mkdtemp()


def _fake(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=None,
        model=_DEFAULT_MODEL,
    )


_SOURCE = "def charge(monthly, days):\n    return monthly / 30 * days\n"


def _repo(tmp_path, tests: dict[str, str]):
    (tmp_path / "billing.py").write_text(_SOURCE, encoding="utf-8")
    for path, source in tests.items():
        (tmp_path / path).write_text(source, encoding="utf-8")
    return tmp_path


def _change_set() -> ChangeSet:
    return ChangeSet(
        base_revision="a",
        head_revision="b",
        files=[
            FileChange(
                path="billing.py",
                status="modified",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@ -1,2 +1,2 @@",
                        old_start=1,
                        old_lines=2,
                        new_start=1,
                        new_lines=2,
                        content="+    return monthly / 30 * days\n",
                    )
                ],
            )
        ],
    )


def _defect_set(*descriptions: str) -> DefectSet:
    return DefectSet(
        obligation_id="daily-rate",
        defects=[
            Defect(
                id=f"daily-rate-d{index}",
                obligation_id="daily-rate",
                type="other",
                description=description,
                code_refs=["billing.py#0"],
            )
            for index, description in enumerate(descriptions, start=1)
        ],
    )


def _test(name: str, body: str = "    assert charge(300, 15) > 0\n") -> DiscoveredTest:
    source = f"def {name}():\n{body}"
    return DiscoveredTest(
        test_id=f"test_billing.py::{name}", file="test_billing.py", reasons=[], source=source
    )


# --- every pair is answered, or recorded as unanswered ------------------------


def test_every_offered_pair_comes_back_with_a_verdict(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge(kills=lambda defect_id, test_id: defect_id.endswith("d1"))

    result = judge_pairs(
        [_defect_set("divides by 30", "ignores days")],
        [_test("test_half_month"), _test("test_full_month")],
        _change_set(),
        judge.client,
        repo=repo,
    )

    assert len(result.verdicts) == 4
    assert result.unjudged == []
    assert {(v.defect_id, v.test_id, v.kills) for v in result.verdicts} == {
        ("daily-rate-d1", "test_billing.py::test_full_month", True),
        ("daily-rate-d1", "test_billing.py::test_half_month", True),
        ("daily-rate-d2", "test_billing.py::test_full_month", False),
        ("daily-rate-d2", "test_billing.py::test_half_month", False),
    }


def test_a_pair_the_judge_never_answers_is_recorded_not_read_as_surviving(tmp_path):
    """The failure this response shape was chosen to expose.

    A shed judgement defaulted to `survives` un-covers a defect silently, and the
    review then prescribes a test that already exists (#250, #287). It has to
    come back as an absence of an answer, distinct from a substantive negative.
    """
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge(answer_all=False)  # omits one defect entry per test

    result = judge_pairs(
        [_defect_set("divides by 30", "ignores days")],
        [_test("test_half_month")],
        _change_set(),
        judge.client,
        repo=repo,
    )

    assert len(result.verdicts) == 1
    assert len(result.unjudged) == 1
    unanswered = result.unjudged[0]
    assert unanswered.cause is UnjudgedCause.UNANSWERED
    assert unanswered.defect_id == "daily-rate-d2"
    assert unanswered.reason.strip() != ""
    # Not silently a `survives` verdict: no verdict exists for it at all.
    assert unanswered.defect_id not in {verdict.defect_id for verdict in result.verdicts}


# --- carry --------------------------------------------------------------------


def _judged(judge, defect_sets, tests, repo, prior=None, batch_size=DEFAULT_PAIR_BATCH_SIZE):
    return judge_pairs(
        defect_sets,
        tests,
        _change_set(),
        judge.client,
        repo=repo,
        batch_size=batch_size,
        prior=prior,
    )


def test_a_verdict_is_reused_when_its_defect_and_its_test_are_both_unchanged(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set("divides by 30")]
    tests = [_test("test_half_month")]

    first = _judged(_Judge(), defects, tests, repo)
    second_judge = _Judge()
    second = _judged(second_judge, defects, tests, repo, prior=first.verdicts)

    assert second_judge.calls == 0
    assert [v.kills for v in second.verdicts] == [v.kills for v in first.verdicts]
    assert second.verdicts[0].carried_from == first.verdicts[0].carry_key


def test_a_verdict_is_produced_again_when_the_tests_source_changed(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set("divides by 30")]

    first = _judged(_Judge(), defects, [_test("test_half_month")], repo)
    edited = [_test("test_half_month", body="    assert charge(300, 15) == 150\n")]
    second_judge = _Judge()
    second = _judged(second_judge, defects, edited, repo, prior=first.verdicts)

    assert second_judge.calls == 1
    assert second.verdicts[0].carried_from is None
    assert second.verdicts[0].test_digest != first.verdicts[0].test_digest


def test_a_verdict_is_produced_again_when_its_defect_changed(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    tests = [_test("test_half_month")]

    first = _judged(_Judge(), [_defect_set("divides by 30")], tests, repo)
    second_judge = _Judge()
    second = _judged(
        second_judge, [_defect_set("divides by a hard-coded 30")], tests, repo, prior=first.verdicts
    )

    assert second_judge.calls == 1
    assert second.verdicts[0].carried_from is None


def test_adding_one_test_judges_only_that_tests_pairs(tmp_path):
    """#312's headline behaviour, and the reason carry is per pair.

    A user who adds one test between two continued runs pays for judging that
    test against the open defects — nothing else.
    """
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set("divides by 30", "ignores days")]
    original = [_test("test_half_month"), _test("test_full_month")]

    first = _judged(_Judge(), defects, original, repo)
    second_judge = _Judge()
    second = _judged(
        second_judge, defects, [*original, _test("test_leap_year")], repo, prior=first.verdicts
    )

    # Asserted on what the requests actually offered, not on the result: a stage
    # that re-judged everything and then discarded the answers would pass a
    # count of the verdicts and fail this.
    assert second_judge.pairs_asked() == {
        ("daily-rate-d1", "test_billing.py::test_leap_year"),
        ("daily-rate-d2", "test_billing.py::test_leap_year"),
    }
    assert len(second.verdicts) == 6
    assert sum(1 for verdict in second.verdicts if verdict.carried_from) == 4


def test_which_pairs_share_a_request_does_not_change_what_carries(tmp_path):
    """DR-269's rule: a carry key must not move because a neighbour joined the batch.

    Same pairs, judged one per request and then four per request. If batch
    composition reached the key, the second run would refuse to carry.
    """
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set("divides by 30", "ignores days")]
    tests = [_test("test_half_month"), _test("test_full_month")]

    first = _judged(_Judge(), defects, tests, repo, batch_size=1)
    second_judge = _Judge()
    second = _judged(second_judge, defects, tests, repo, prior=first.verdicts, batch_size=4)

    assert second_judge.calls == 0
    assert all(verdict.carried_from for verdict in second.verdicts)


# --- batching -----------------------------------------------------------------


def test_no_request_carries_more_judgements_than_the_limit(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set(*[f"defect {index}" for index in range(5)])]
    tests = [_test(f"test_case_{index}") for index in range(4)]
    judge = _Judge()

    _judged(judge, defects, tests, repo, batch_size=3)

    # One request per test, so each test's 5 defects split 3 + 2: 8 requests.
    assert judge.calls == 8
    for request in judge.requests:
        # The schema's cross product IS the offered set, because a request never
        # spans two tests. That equality is what makes the limit mean the number
        # of judgements the response is actually asked to carry.
        assert len(request["test_id"]) == 1
        assert len(request["test_id"]) * len(request["defect_id"]) <= 3


# --- the derived comparison ---------------------------------------------------


def test_support_is_derived_with_its_denominator(tmp_path):
    defects = _defect_set("divides by 30", "ignores days")
    verdicts = _judged(
        _Judge(kills=lambda defect_id, test_id: defect_id.endswith("d1")),
        [defects],
        [_test("test_half_month")],
        _repo(tmp_path, {"test_billing.py": "x"}),
    ).verdicts

    derived = derive_support([defects], verdicts, [])

    assert len(derived) == 1
    assert derived[0].evidence_class == "partially_supported"
    assert (derived[0].killed, derived[0].total) == (1, 2)


def test_a_reasoned_empty_enumeration_is_not_strongly_supported():
    """Vacuously killing all zero defects is arithmetic, not evidence.

    Calling it `strongly_supported` would flatter a thin enumeration in exactly
    the direction #252 warns about, so it is `indeterminate` here and gets a
    terminal state of its own in #316.
    """
    empty = DefectSet(obligation_id="true-by-construction", defects=[], reason="cannot fail")

    derived = derive_support([empty], [], [])

    assert derived[0].evidence_class == "indeterminate"
    assert (derived[0].killed, derived[0].total) == (0, 0)


def test_defect_text_ignores_the_defect_id(tmp_path):
    """Carry identity is content, because ids move for reasons the answer does not.

    Defect ids are composed from the obligation id, so rewording a requirement
    renames every defect beneath it. Keying carry on the id would re-judge pairs
    whose defect never changed.
    """
    first = Defect(id="a-1", obligation_id="a", type="other", description="same", code_refs=["x#0"])
    renamed = Defect(
        id="b-9", obligation_id="b", type="other", description="same", code_refs=["x#0"]
    )

    assert defect_text(first) == defect_text(renamed)


def test_the_digest_is_per_test_not_per_file():
    """DR-293: a file-level digest re-judges every test in a module when one moves."""
    unchanged = _test("test_half_month")
    sibling_edited = _test("test_half_month")  # same test, a sibling changed elsewhere

    assert source_digest(unchanged) == source_digest(sibling_edited)
    assert source_digest(unchanged) != source_digest(
        _test("test_half_month", body="    assert 1\n")
    )


# --- the wiring ---------------------------------------------------------------
#
# The pipeline really calls this, the report really shows it, and nothing it
# records moves a verdict. Asserted on a real `run_review` rather than on
# `judge_pairs` alone: defect injection has repeatedly found a helper with a good
# unit test that the pipeline never calls (CLAUDE.md).

_TASK = (
    "# Task\nThe billing export prorates a partial month.\n\n"
    "## Constraints\n- The daily rate is the monthly price divided by the days in that month\n"
)
_QUOTE = "The daily rate is the monthly price divided by the days in that month"

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

_ENUMERATED = {
    "obligation_id": "daily-rate",
    "defects": [
        {
            "slug": "divides-by-thirty",
            "type": "other",
            "description": "The daily rate divides by a hard-coded 30.",
            "code_refs": [],
        }
    ],
    "reason": "",
}

_NO_DEFECTS = {
    "obligation_id": "daily-rate",
    "defects": [],
    "reason": "Nothing plausible.",
}


def _built(tmp_path):
    """A two-commit repo with a source change and a test that touches it."""
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
    (repo / "test_billing.py").write_text(
        "from billing import prorate\n\n\ndef test_prorate():\n    assert prorate(300, 31) > 0\n"
    )
    git("add", "-A")
    git("commit", "-qm", "head")
    return repo, base, git("rev-parse", "HEAD")


def _review_over(built, enumeration: dict | None = None, pairs: dict | None = None):
    """One review over an already-built repo.

    Two reviews that must agree byte for byte have to run over the SAME repo:
    building one each compares reviews whose `reviewed_revision` differs, since
    identical content still gets commits stamped with the time they were made.
    """
    repo, base, head = built
    client = client_dispatching(
        {
            "_Decomposition": _DECOMPOSITION,
            "_Enumeration": enumeration if enumeration is not None else _ENUMERATED,
            **({"_PairVerdicts": pairs} if pairs is not None else {}),
        }
    )
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
    )


def _dispatching(pairs: dict, capture: list):
    return client_dispatching(
        {"_Decomposition": _DECOMPOSITION, "_Enumeration": _ENUMERATED, "_PairVerdicts": pairs},
        capture=capture,
    )


def _pairs_answer(kills: bool, test_id: str = "test_billing.py::test_prorate") -> dict:
    return {
        "tests": [
            {
                "test_id": test_id,
                # Composed by the enumerator as `<obligation id>/<slug>`, not
                # taken from its answer — `_defects_from` prefixes so uniqueness
                # is structural across criteria.
                "defects": [
                    {"defect_id": "daily-rate/divides-by-thirty", "fails": kills, "reason": "r"}
                ],
            }
        ]
    }


def test_the_pipeline_really_judges_pairs(tmp_path):
    review = _review_over(_built(tmp_path), pairs=_pairs_answer(True))

    assert review.pair_verdicts, "the pipeline judged no pairs"
    assert any(verdict.kills for verdict in review.pair_verdicts)


def test_the_report_shows_implied_support_beside_the_current_rating(tmp_path):
    review = _review_over(_built(tmp_path), pairs=_pairs_answer(True))

    rendered = render_report(review)

    assert "Support implied by test-to-defect pairs" in rendered
    assert "implied by pairs:" in rendered
    assert "this review says:" in rendered
    # The denominator, never the class alone (DR-312 resolved question 3).
    assert "kills 1 of 1 enumerated defects" in rendered
    assert "Criteria where the two disagree:" in rendered


def test_judging_pairs_changes_no_verdict_rating_or_recommendation(tmp_path):
    """The advisory guarantee, checked by difference.

    Two reviews over the same input whose pair verdicts are opposite. Everything
    except the pair records must be identical — that is what shadow means, and it
    is what makes a later rating movement attributable (DR-312 decision 5).
    """
    built = _built(tmp_path)
    killing = _review_over(built, pairs=_pairs_answer(True))
    surviving = _review_over(built, pairs=_pairs_answer(False))

    assert any(verdict.kills for verdict in killing.pair_verdicts)
    assert not any(verdict.kills for verdict in surviving.pair_verdicts)

    def apart(review):
        return review.model_copy(
            update={"pair_verdicts": [], "unjudged_pairs": []}
        ).to_canonical_json()

    assert apart(killing) == apart(surviving)


def test_the_verdicts_survive_a_round_trip_through_persisted_state(tmp_path):
    review = _review_over(_built(tmp_path), pairs=_pairs_answer(True))

    reloaded = Review.model_validate_json(review.to_canonical_json())

    assert reloaded.pair_verdicts == review.pair_verdicts
    assert reloaded.to_canonical_json() == review.to_canonical_json()


def test_two_runs_over_the_same_input_agree_byte_for_byte(tmp_path):
    built = _built(tmp_path)

    first = _review_over(built, pairs=_pairs_answer(True))
    second = _review_over(built, pairs=_pairs_answer(True))

    assert first.to_canonical_json() == second.to_canonical_json()
    assert render_report(first) == render_report(second)


def test_a_continued_run_carries_verdicts_through_the_ledger(tmp_path):
    """The ledger really carries this, end to end — not `prior=` handed in by a test.

    #314's headline behaviour is that adding one test between two continued runs
    costs that test's pairs and nothing else, and it is only true if the verdicts
    survive the round trip through the ledger entry. Asserted on the calls the
    second run issued, because a stage that re-judged everything and then threw
    the answers away would satisfy a count of the verdicts.
    """
    repo, base, head = _built(tmp_path)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    first_capture: list = []
    sink: list = []
    run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=_dispatching(_pairs_answer(True), first_capture),
        reviewed_revision=head,
        ledger_sink=sink,
    )
    derived, linked, defect_sets, pair_verdicts = sink[0]
    assert pair_verdicts, "the first run judged no pairs, so there is nothing to carry"

    entry = build_ledger_entry(
        derived,
        run_id="first",
        parent_run_id=None,
        task_digest="digest",
        linked=linked,
        defect_sets=defect_sets,
        pair_verdicts=pair_verdicts,
    )
    # The round trip that matters: through the persisted form, not the object.
    entry = LedgerEntry.model_validate_json(entry.model_dump_json())

    (repo / "test_extra.py").write_text(
        "from billing import prorate\n\n\ndef test_extra():\n    assert prorate(300, 28) > 0\n"
    )
    git("add", "-A")
    git("commit", "-qm", "add one test")
    second_head = git("rev-parse", "HEAD")

    second_capture: list = []
    second = run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, second_head),
        repo=repo,
        client=_dispatching(
            _pairs_answer(True, test_id="test_extra.py::test_extra"), second_capture
        ),
        reviewed_revision=second_head,
        ledger_prior=entry,
    )

    pair_calls = [call for call in second_capture if call["schema"] == "_PairVerdicts"]
    assert len(pair_calls) == 1, "the second run judged more than the one added test"
    assert "test_extra.py::test_extra" in pair_calls[0]["prompt"]
    assert "test_billing.py::test_prorate" not in pair_calls[0]["prompt"]

    carried = [verdict for verdict in second.pair_verdicts if verdict.carried_from]
    assert len(carried) == 1
    assert carried[0].test_id == "test_billing.py::test_prorate"


def test_a_prefiltered_pair_is_named_in_the_report(tmp_path):
    """The recorded exclusion is rendered, not merely stored.

    Exercised on a constructed review rather than on a real run: the prefilter's
    rule is sound and therefore fires almost never, so waiting for real input to
    trigger it would be a test that passes by luck (see `reachability`).
    """
    review = _review_over(_built(tmp_path), pairs=_pairs_answer(True))
    with_exclusion = review.model_copy(
        update={
            "unjudged_pairs": [
                UnjudgedPair(
                    defect_id="daily-rate/divides-by-thirty",
                    test_id="test_far_away.py::test_unrelated",
                    cause=UnjudgedCause.PREFILTERED,
                    reason="no path to the defect exists",
                )
            ]
        }
    )

    rendered = render_report(with_exclusion)

    assert "Pairs left unjudged:" in rendered
    assert "[prefiltered]" in rendered
    assert "daily-rate/divides-by-thirty x test_far_away.py::test_unrelated" in rendered
    assert "no path to the defect exists" in rendered


# --- the question asked, and the answer's shape -------------------------------
#
# Both gaps were found by #314's own Gate 2 run, which rated `constraint-03` and
# `constraint-05` unsupported with no mapped test. It was right: nothing pinned
# either, and the double ignores the prompt, so every other test here would pass
# against a stage that asked something else entirely.


def test_the_question_put_about_a_pair_is_the_failure_question(tmp_path):
    """The pair question is existential, not a relevance judgement.

    This is the whole premise of #312: *would this test fail if the code
    contained this defect?* has an answer, where *does this test purport to
    evidence this obligation?* does not. A stage that drifted back to relevance
    would still return well-formed verdicts, so the question itself needs pinning.
    """
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge()

    _judged(judge, [_defect_set("divides by 30")], [_test("test_half_month")], repo)

    prompt = judge.requests[0]["prompt"]
    assert "would THIS TEST fail" in prompt
    assert "If the delivered code contained THIS DEFECT" in prompt
    # The concrete pair, not a paraphrase: the defect's own description and the
    # test's own source both reach the request.
    assert "divides by 30" in prompt
    assert "assert charge(300, 15) > 0" in prompt
    # And it is not asking the retired question.
    assert "purports to evidence" not in prompt


def test_the_answer_about_a_pair_carries_only_the_pair_the_verdict_and_a_reason(tmp_path):
    """DR-312 decision 3 holds the response to the minimum.

    The caching discount is input-only, so output growth never amortizes — and
    DR-314 measured this shape already costing about twice the output tokens of
    the alternative. A richer per-pair payload belongs to a later per-finding
    call, not to this sweep, and a field added here would be paid on every pair.
    """
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge()

    _judged(judge, [_defect_set("divides by 30")], [_test("test_half_month")], repo)

    # Read off the schema AS SENT, refs already inlined, because that is what
    # bounds the response. Asserting on the model class alone would pass against
    # a stage that sent something else.
    schema = judge.requests[0]["schema"]
    per_test = schema["properties"]["tests"]["items"]["properties"]
    assert set(per_test) == {"test_id", "defects"}
    per_pair = per_test["defects"]["items"]["properties"]
    assert set(per_pair) == {"defect_id", "fails", "reason"}
