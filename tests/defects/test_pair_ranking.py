"""Ranked pair judgement with an early stop (#348).

The pair judge reads each defect's candidate tests in order of similarity to the
defect's description, and stops asking about a defect once enough of its tests
are recorded as catching it. These tests pin the four things that make that
safe: a defect nothing catches is still asked about in full, a pair left unasked
is recorded rather than dropped, such a pair cannot move a rating, and nothing
about the ranking reaches the judge.
"""

from __future__ import annotations

import subprocess

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.defects.pair_mapping import judge_pairs
from acceptance.defects.support import derive_support
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.review_state import (
    Obligation,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)
from tests.defects.test_pair_mapping import (
    _DECOMPOSITION,
    _DEFAULT_MODEL,
    _ENUMERATED,
    _TASK,
    _change_set,
    _defect_set,
    _Judge,
    _repo,
    _test,
    _tmp,
)
from tests.support import client_dispatching, embedding_fn_for

_DEFECT = "daily-rate-d1"
_DESCRIPTION = "divides by 30"


def _name(rank: int) -> str:
    """The test at similarity `rank`, 1 the most similar to the defect.

    The leading letter runs BACKWARDS against the rank — rank 1 is `test_y_r01`,
    rank 2 `test_x_r02` — so sorting by id is the reverse of sorting by
    similarity. The ranking breaks ties on test id, so a ranking that silently
    stopped using similarity would still produce a clean order; this makes it the
    wrong one, and the tests below see it.
    """
    return f"test_{chr(ord('z') - rank)}_r{rank:02d}"


def _id(rank: int) -> str:
    return f"test_billing.py::{_name(rank)}"


def _tests(count: int):
    return [_test(_name(rank)) for rank in range(1, count + 1)]


def _geometry(tests) -> dict[str, list[float]]:
    """The defect along x; each test further from it the higher its number."""
    vectors = {_DESCRIPTION: [1.0, 0.0]}
    for test in tests:
        number = int(test.test_id.rsplit("_r", 1)[1])
        vectors[test.source] = [1.0, 0.1 * number]
    return vectors


class _RankedJudge(_Judge):
    """`_Judge`, with an embedding model the ranking can call."""

    def __init__(self, tests, kills=None):
        super().__init__(kills=kills)
        self.client = ModelClient(
            model=_DEFAULT_MODEL,
            mode=Mode.RECORD,
            store=TranscriptStore(_tmp()),
            completion_fn=self._completion_fn,
            embedding_model="voyage/voyage-3.5-lite",
            embedding_fn=embedding_fn_for(_geometry(tests)),
        )


def _run(tmp_path, count=10, kills=None, stop_after_kills=1, tests_per_batch=2, **kwargs):
    tests = _tests(count)
    judge = _RankedJudge(tests, kills=kills)
    result = judge_pairs(
        [_defect_set(_DESCRIPTION)],
        tests,
        _change_set(),
        judge.client,
        repo=_repo(tmp_path, {"test_billing.py": "x"}),
        tests_per_batch=tests_per_batch,
        stop_after_kills=stop_after_kills,
        **kwargs,
    )
    return result, judge


def _kills_at(*ranks: int):
    wanted = {_id(rank) for rank in ranks}
    return lambda defect_id, test_id: test_id in wanted


def _covered(result) -> list[UnjudgedPair]:
    return [e for e in result.unjudged if e.cause is UnjudgedCause.DEFECT_ALREADY_COVERED]


# --- the walk -----------------------------------------------------------------


def test_tests_are_asked_most_similar_first(tmp_path):
    _, judge = _run(tmp_path, kills=_kills_at(3))

    # The first round is the two most similar; a request lists its tests by id.
    assert set(judge.requests[0]["test_id"]) == {_id(1), _id(2)}


def test_a_covered_defect_is_asked_no_further(tmp_path):
    """Kill at rank 3. Round one asks ranks 1-2, round two asks 3-6 and finds it,
    and nothing below rank 6 is put to the model."""
    result, judge = _run(tmp_path, kills=_kills_at(3))

    asked = {test_id for _, test_id in judge.pairs_asked()}
    assert asked == {_id(rank) for rank in range(1, 7)}
    assert len(result.verdicts) == 6


def test_every_pair_not_asked_is_recorded_with_its_rank_and_what_covered_it(tmp_path):
    """DR-314: a pair nothing records is indistinguishable from a *survives*."""
    result, _ = _run(tmp_path, kills=_kills_at(3))

    skipped = _covered(result)
    assert sorted(entry.rank for entry in skipped) == [7, 8, 9, 10]
    assert {entry.test_id for entry in skipped} == {_id(rank) for rank in range(7, 11)}
    assert all(entry.covered_by == [_id(3)] for entry in skipped)
    # Every pair is accounted for exactly once: judged, or unjudged with a cause.
    accounted = [(v.defect_id, v.test_id) for v in result.verdicts] + [
        (e.defect_id, e.test_id) for e in result.unjudged
    ]
    assert len(accounted) == len(set(accounted)) == 10


def test_a_defect_no_test_catches_is_asked_about_in_full(tmp_path):
    result, judge = _run(tmp_path, kills=None)

    assert len(judge.pairs_asked()) == 10
    assert len(result.verdicts) == 10
    assert _covered(result) == []


def test_rounds_double_so_a_long_sweep_takes_few_of_them(tmp_path):
    """Rounds of 2, 4, 8, ... tests. A kill at rank 7 lands in the third round,
    ranks 7-14, so everything to rank 14 is asked and nothing below it. Rounds of
    a fixed 2 would have stopped at rank 8 — and would walk several hundred tests
    in a hundred sequential rounds rather than about seven."""
    result, judge = _run(tmp_path, count=20, kills=_kills_at(7))

    asked = sorted(int(test_id.rsplit("_r", 1)[1]) for _, test_id in judge.pairs_asked())
    assert asked == list(range(1, 15))
    assert sorted(entry.rank for entry in _covered(result)) == list(range(15, 21))


def test_the_stop_number_is_how_many_kills_it_takes(tmp_path):
    """With two, one kill does not stop the walk; the second does."""
    result, judge = _run(tmp_path, kills=_kills_at(1, 5), stop_after_kills=2)

    asked = {test_id for _, test_id in judge.pairs_asked()}
    assert _id(5) in asked
    assert {entry.rank for entry in _covered(result)} == {7, 8, 9, 10}
    assert all(set(entry.covered_by) == {_id(1), _id(5)} for entry in _covered(result))


def test_a_defect_short_of_the_stop_number_is_asked_about_in_full(tmp_path):
    """The two-kill case measured in `rank-prefilter/FINDINGS.md`: one kill and a
    stop number of two leaves the defect uncovered by the stop rule, so it pays
    for every test — never skips on a kill count it did not reach."""
    result, judge = _run(tmp_path, kills=_kills_at(2), stop_after_kills=2)

    assert len(judge.pairs_asked()) == 10
    assert _covered(result) == []


def test_turned_off_it_asks_every_pair_in_one_pass_and_embeds_nothing(tmp_path):
    """`None` is how the stage ran before #348. The ordinary `_Judge` has no
    embedding model at all, so any attempt to rank would raise."""
    judge = _Judge(kills=_kills_at(3))
    tests = _tests(10)
    result = judge_pairs(
        [_defect_set(_DESCRIPTION)],
        tests,
        _change_set(),
        judge.client,
        repo=_repo(tmp_path, {"test_billing.py": "x"}),
        tests_per_batch=2,
        stop_after_kills=None,
    )

    assert len(judge.pairs_asked()) == 10
    assert _covered(result) == []


def test_it_works_on_what_routing_leaves(tmp_path):
    """#340's held-back pairs keep their own cause when the defect is covered;
    the walk orders and stops only what reaches the judge."""
    held = _id(2)
    result, judge = _run(tmp_path, kills=_kills_at(1), skipped={(_DEFECT, held): "not asked"})

    assert (_DEFECT, held) not in judge.pairs_asked()
    (routed,) = [e for e in result.unjudged if e.cause is UnjudgedCause.PASSED_UNDER_EDIT]
    assert routed.test_id == held


def test_nothing_about_the_ranking_reaches_the_judge(tmp_path):
    """The question does not change. A request for ranks 3-6 must read exactly as
    the unranked stage would write a request for the same pairs."""
    _, ranked = _run(tmp_path, kills=_kills_at(3))

    for request in ranked.requests:
        text = request["prompt"].lower()
        assert "rank" not in text
        assert "similar" not in text
        assert "already" not in text
        assert "covered" not in text


def test_no_embedding_request_overruns_either_limit():
    """Long test sources split by estimated tokens, not only by count — 128 long
    sources in one request would overrun a provider's per-request token cap."""
    from acceptance.defects.pair_ranking import EMBED_CHUNK, EMBED_TOKEN_BUDGET, _chunks

    texts = ["x" * 8_000] * 100 + ["y"] * 300 + ["z" * 400_000]
    chunks = _chunks(texts)

    assert [text for chunk in chunks for text in chunk] == texts
    for chunk in chunks:
        assert len(chunk) <= EMBED_CHUNK
        assert len(chunk) == 1 or sum(len(t) // 4 for t in chunk) <= EMBED_TOKEN_BUDGET


# --- the rating ---------------------------------------------------------------


def _obligation() -> Obligation:
    return Obligation(
        id="daily-rate",
        description="d",
        type="functional",
        importance="normal",
        explicit=True,
        observable_behavior="o",
    )


def _verdict(test_id: str, kills: bool) -> PairVerdict:
    return PairVerdict(defect_id=_DEFECT, test_id=test_id, kills=kills, reason="r" if kills else "")


def _skip(test_id: str, rank: int) -> UnjudgedPair:
    return UnjudgedPair(
        defect_id=_DEFECT,
        test_id=test_id,
        cause=UnjudgedCause.DEFECT_ALREADY_COVERED,
        reason="not asked",
        rank=rank,
        covered_by=["t1"],
    )


def _rating(verdicts, unjudged):
    (result,) = derive_support(
        [_obligation()], [_defect_set(_DESCRIPTION, "ignores days")], verdicts, unjudged
    )
    return result.evidence_class, result.covered, result.unknown


@pytest.mark.parametrize("answer", [True, False])
def test_a_skipped_pair_cannot_move_the_rating_whatever_it_would_have_said(answer):
    """Both directions: had the skipped pair been asked and answered either way,
    the class, the covered count and the unknown count are all unchanged."""
    killed = [_verdict("t1", True)]
    skipped = _rating(killed, [_skip("t2", 2)])
    answered = _rating(killed + [_verdict("t2", answer)], [])

    assert skipped == answered


def test_a_skipped_pair_derives_no_verdict_and_is_not_unknown():
    """Not `indeterminate`'s raw material: a skip on a covered defect is not an
    admission that the defect's status is unknown."""
    evidence_class, covered, unknown = _rating([_verdict("t1", True)], [_skip("t2", 2)])

    assert (covered, unknown) == (1, 0)
    assert evidence_class == "partially_supported"


def test_the_cause_is_refused_on_a_defect_its_named_tests_do_not_cover():
    """The exclusion from `unknown` is sound only on a covered defect, so a skip
    naming kills the verdicts do not hold is refused rather than believed."""
    with pytest.raises(ValueError, match="carry no killing verdict"):
        _rating([_verdict("t1", False)], [_skip("t2", 2)])


def test_the_cause_cannot_be_recorded_without_its_rank_and_covering_tests():
    with pytest.raises(ValueError, match="must name its rank"):
        UnjudgedPair(
            defect_id=_DEFECT,
            test_id="t2",
            cause=UnjudgedCause.DEFECT_ALREADY_COVERED,
            reason="not asked",
        )


def test_no_other_cause_carries_a_rank():
    with pytest.raises(ValueError, match="belong only to"):
        UnjudgedPair(
            defect_id=_DEFECT, test_id="t2", cause=UnjudgedCause.UNANSWERED, reason="x", rank=3
        )


def test_the_judge_produces_the_cause_only_once_the_stop_number_is_reached(tmp_path):
    """Checked on what the stage actually returns, across every stop number and
    kill position here: each skip names at least `stop_after_kills` kills, and
    every one of them is a killing verdict the stage also returned."""
    for stop in (1, 2, 3):
        for kills in ((), (1,), (1, 4), (2, 3, 9)):
            result, _ = _run(tmp_path, kills=_kills_at(*kills), stop_after_kills=stop)
            killing = {v.test_id for v in result.verdicts if v.kills}
            for entry in _covered(result):
                assert len(entry.covered_by) >= stop
                assert set(entry.covered_by) <= killing


# --- the pipeline -------------------------------------------------------------


def _built_with_tests(tmp_path, count: int):
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
    body = "".join(
        f"\n\ndef test_prorate_{n}():\n    assert prorate(300, {n + 28}) > 0\n"
        for n in range(count)
    )
    (repo / "test_billing.py").write_text("from billing import prorate\n" + body)
    git("add", "-A")
    git("commit", "-qm", "head")
    return repo, base, git("rev-parse", "HEAD")


def _every_test_kills(count: int) -> dict:
    return {
        "tests": [
            {
                "test_id": f"test_billing.py::test_prorate_{n}",
                "defects": [
                    {"defect_id": "daily-rate/divides-by-thirty", "fails": True, "reason": "r"}
                ],
            }
            for n in range(count)
        ]
    }


def _pipeline_review(tmp_path, **kwargs):
    repo, base, head = _built_with_tests(tmp_path, 6)
    client = client_dispatching(
        {
            "_Decomposition": _DECOMPOSITION,
            "_Enumeration": _ENUMERATED,
            "_PairVerdicts": _every_test_kills(6),
        }
    )
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
        **kwargs,
    )


def test_the_pipeline_ranks_and_stops_by_default(tmp_path):
    """Wiring, not the helper: `run_review` with no argument really stops early.
    Six tests, four in the first round, every one a kill — so two are skipped."""
    review = _pipeline_review(tmp_path)

    skipped = [e for e in review.unjudged_pairs if e.cause is UnjudgedCause.DEFECT_ALREADY_COVERED]
    assert len(review.pair_verdicts) == 4
    assert len(skipped) == 2


def test_the_pipeline_can_still_run_the_full_sweep(tmp_path):
    review = _pipeline_review(tmp_path, stop_after_kills=None)

    assert len(review.pair_verdicts) == 6
    assert review.unjudged_pairs == []


def test_the_report_counts_each_defects_asked_and_skipped_pairs(tmp_path):
    report = render_report(_pipeline_review(tmp_path))

    assert "pairs: 4 put to the model, 2 skipped once the defect was covered" in report
    assert "[defect_already_covered] daily-rate/divides-by-thirty x 2 candidate test(s)" in report
