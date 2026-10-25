"""Judging (defect, test) pairs: who answers, what carries, what is recorded (#314, #385).

Four properties carry this stage and each has its own group below:

- **Jev decides first, and the model only between the cut-offs** — DR-379's
  rule, with Jev's probability deciding at 0.5 when the model gives no usable
  answer, and every verdict saying who decided it;
- **a verdict carries** while its defect's content, its test's source, its
  requirement and the code Jev is shown are all unchanged, and is produced again
  when any of them moves;
- **adding one test costs that test's pairs and nothing else**, which is #312's
  headline behaviour and the thing carry exists for;
- **a recorded run replays** with no live call, to the same bytes.

The last group is the wiring: the pipeline really calls this, the ledger really
carries it, and the verdicts really reach the rating.
"""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

from acceptance.change.diff import extract_change_set
from acceptance.defects.pair_mapping import (
    JEV_FAILS_AT,
    JEV_STAGE,
    JEV_SURVIVES_AT,
    defect_text,
    judge_pairs,
    source_digest,
)
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.evidence_tier import EvidenceTier
from acceptance.jev import JevProvider
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
    PairJudge,
    Review,
    UnjudgedCause,
    UnjudgedPair,
)
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_dispatching

_DEFAULT_MODEL = "anthropic/claude-sonnet-5-5"

_ENUMERATED_DESCRIPTION = "The daily rate divides by a hard-coded 30."

# The request Jev is sent carries no ids — it is shown a defect and a test, as
# the experiment showed it — so the double recovers them from what it is shown.
# `_defect_set` registers each description it builds here.
_ID_BY_DESCRIPTION: dict[str, str] = {_ENUMERATED_DESCRIPTION: "daily-rate/divides-by-thirty"}
_FILE_BY_TEST_NAME = {"test_extra": "test_extra.py"}


def _test_id(name: str) -> str:
    return f"{_FILE_BY_TEST_NAME.get(name, 'test_billing.py')}::{name}"


def _tmp() -> str:
    import tempfile

    return tempfile.mkdtemp()


def _fake(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=None,
        model=_DEFAULT_MODEL,
    )


class _Judge:
    """Both judges, answered by rules, recording what each was asked.

    `kills(defect_id, test_id)` is the truth. Jev answers 0.9 where it holds and
    0.1 where it does not — both outside the cut-offs, so Jev decides — except on
    a pair `unsure` names, where it answers 0.3 and the model is asked. The model
    answers `model_says(defect_id, test_id)` if given, else the truth.

    `requests` holds one entry per Jev call, shaped as the batched judge's were
    (`test_id` and `defect_id` lists, `prompt` text) so the ranking tests read
    them unchanged; `model_requests` holds the model's.
    """

    def __init__(self, kills=None, unsure=None, model_says=None):
        self._kills = kills or (lambda defect_id, test_id: False)
        self._unsure = unsure or (lambda defect_id, test_id: False)
        self._model_says = model_says
        self.requests: list[dict] = []
        self.model_requests: list[dict] = []
        self.jev = JevProvider(post_fn=self._post)
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
        """Every pair Jev was asked about, as (defect id, test id)."""
        return {(r["defect_id"][0], r["test_id"][0]) for r in self.requests}

    def _post(self, url, body, headers):
        state = body["state"]
        defect_id = _ID_BY_DESCRIPTION[state["defect"].splitlines()[0]]
        test_id = _test_id(state["test_name"])
        self.requests.append(
            {
                "defect_id": [defect_id],
                "test_id": [test_id],
                "prompt": "\n".join(str(value) for value in state.values()),
                "state": state,
                "questions": body["questions"],
            }
        )
        if self._unsure(defect_id, test_id):
            probability = 0.3
        else:
            probability = 0.9 if self._kills(defect_id, test_id) else 0.1
        return 200, {
            "answers": {"fails": {"noul": probability}},
            "usage": {"input_tokens": 100, "output_tokens": 1},
        }

    def _completion_fn(self, **kwargs):
        prompt = "\n".join(message["content"] for message in kwargs["messages"])
        defect_line = prompt.split("## Defect\n\n", 1)[1].splitlines()[0]
        test_id = prompt.split("## Test ", 1)[1].splitlines()[0].strip()
        defect_id = _ID_BY_DESCRIPTION[defect_line]
        self.model_requests.append(
            {
                "pair": (defect_id, test_id),
                "prompt": prompt,
                "schema": kwargs["response_format"]["json_schema"],
            }
        )
        if self._model_says is not None:
            answer = self._model_says(defect_id, test_id)
        else:
            answer = {"fails": self._kills(defect_id, test_id)}
        return _fake(json.dumps(answer))


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
    defects = [
        Defect(
            id=f"daily-rate-d{index}",
            obligation_id="daily-rate",
            type="other",
            description=description,
            code_refs=["billing.py#0"],
        )
        for index, description in enumerate(descriptions, start=1)
    ]
    for defect in defects:
        _ID_BY_DESCRIPTION[defect.description] = defect.id
    return DefectSet(obligation_id="daily-rate", defects=defects)


def _test(name: str, body: str = "    assert charge(300, 15) > 0\n") -> DiscoveredTest:
    source = f"def {name}():\n{body}"
    return DiscoveredTest(test_id=_test_id(name), file="test_billing.py", reasons=[], source=source)


def _judged(judge, defect_sets, tests, repo, prior=None, requirements=None, **kwargs):
    return judge_pairs(
        defect_sets,
        tests,
        _change_set(),
        judge.client,
        repo=repo,
        prior=prior,
        requirements=requirements,
        jev=judge.jev,
        **kwargs,
    )


# --- who answers --------------------------------------------------------------


def test_every_offered_pair_comes_back_with_a_verdict(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge(kills=lambda defect_id, test_id: defect_id.endswith("d1"))

    result = _judged(
        judge,
        [_defect_set("divides by 30", "ignores days")],
        [_test("test_half_month"), _test("test_full_month")],
        repo,
    )

    assert result.unjudged == []
    assert {(v.defect_id, v.test_id, v.kills) for v in result.verdicts} == {
        ("daily-rate-d1", "test_billing.py::test_full_month", True),
        ("daily-rate-d1", "test_billing.py::test_half_month", True),
        ("daily-rate-d2", "test_billing.py::test_full_month", False),
        ("daily-rate-d2", "test_billing.py::test_half_month", False),
    }


def test_jev_is_asked_about_one_pair_per_call(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge()

    _judged(
        judge,
        [_defect_set("divides by 30", "ignores days")],
        [_test("test_half_month"), _test("test_full_month")],
        repo,
    )

    assert judge.calls == 4
    assert all(len(r["defect_id"]) == len(r["test_id"]) == 1 for r in judge.requests)


def _jev_at(probability: float, model_says=None):
    """A judge whose Jev answers `probability` on every pair."""
    judge = _Judge(model_says=model_says)

    def post(url, body, headers):
        judge._post(url, body, headers)
        return 200, {"answers": {"fails": {"noul": probability}}, "usage": {}}

    judge.jev = JevProvider(post_fn=post)
    return judge


def test_jev_decides_alone_at_and_beyond_the_cut_offs(tmp_path):
    """0.34 or more is "fails", 0.24 or less is "survives", and neither asks the
    model. The boundaries themselves are pinned, since an off-by-one on either
    would move pairs between Jev and the model with nothing else changing."""
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    cases = [(JEV_FAILS_AT, True), (0.95, True), (JEV_SURVIVES_AT, False), (0.02, False)]
    for probability, expected in cases:
        judge = _jev_at(probability)
        result = _judged(judge, [_defect_set("divides by 30")], [_test("test_half_month")], repo)

        (verdict,) = result.verdicts
        assert verdict.kills is expected, probability
        assert verdict.judged_by is PairJudge.JEV
        assert verdict.jev_probability == probability
        assert judge.model_requests == [], f"the model was asked at {probability}"


def test_between_the_cut_offs_the_model_decides(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    for model_answer in (True, False):
        judge = _jev_at(0.3, model_says=lambda d, t, answer=model_answer: {"fails": answer})
        result = _judged(judge, [_defect_set("divides by 30")], [_test("test_half_month")], repo)

        (verdict,) = result.verdicts
        assert verdict.kills is model_answer
        assert verdict.judged_by is PairJudge.MODEL
        assert verdict.jev_probability == 0.3
        assert len(judge.model_requests) == 1


def test_just_inside_each_cut_off_the_model_is_asked(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    for probability in (JEV_FAILS_AT - 0.001, JEV_SURVIVES_AT + 0.001):
        judge = _jev_at(probability)
        _judged(judge, [_defect_set("divides by 30")], [_test("test_half_month")], repo)
        assert len(judge.model_requests) == 1, probability


def test_with_no_usable_answer_from_the_model_jev_decides_at_one_half(tmp_path):
    """DR-379's last resort. Recorded as an unusable answer, never as silence."""
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    for answer in ({}, {"fails": "maybe"}, {"fails": None}):
        judge = _jev_at(0.3, model_says=lambda d, t, a=answer: a)
        log = UnusableAnswerLog()
        result = _judged(
            judge, [_defect_set("divides by 30")], [_test("test_half_month")], repo, unusable=log
        )

        (verdict,) = result.verdicts
        assert verdict.kills is False, answer  # 0.3 < 0.5
        assert verdict.judged_by is PairJudge.JEV
        (entry,) = log.answers
        assert entry.field == "fails"
        assert entry.returned_id == "daily-rate-d1/test_billing.py::test_half_month"
        assert "decided the pair at 0.5" in entry.reason


def test_a_verdict_carries_no_reasoning_and_says_who_decided(tmp_path):
    """#385: neither judge reasons, and a verdict must say so rather than leave
    an empty `reason` to look like one that was lost."""
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge(
        kills=lambda defect_id, test_id: True,
        unsure=lambda defect_id, test_id: test_id.endswith("full_month"),
    )

    result = _judged(
        judge,
        [_defect_set("divides by 30")],
        [_test("test_half_month"), _test("test_full_month")],
        repo,
    )

    by_test = {verdict.test_id.split("::")[1]: verdict for verdict in result.verdicts}
    assert by_test["test_half_month"].judged_by is PairJudge.JEV
    assert by_test["test_full_month"].judged_by is PairJudge.MODEL
    assert all(verdict.reason == "" for verdict in result.verdicts)
    assert all(verdict.tier is EvidenceTier.STATIC for verdict in result.verdicts)


# --- what each judge is shown ---------------------------------------------------


def test_jev_is_asked_the_failure_question_about_the_concrete_pair(tmp_path):
    """The pair question is existential, not a relevance judgement (#312), and
    Jev gets DR-379's targeted context: the requirement, the defect, the test
    with its source, and the delivered code with the defect's lines marked."""
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _Judge()

    _judged(
        judge,
        [_defect_set("divides by 30")],
        [_test("test_half_month")],
        repo,
        requirements={"daily-rate": "The daily rate is the monthly price over the month's days."},
    )

    (request,) = judge.requests
    question = request["questions"]["fails"]
    assert question["type"] == "noul"
    assert (
        "If the delivered code had this defect, would this test fail?" in question["instructions"]
    )
    state = request["state"]
    assert state["change_request"] == "The daily rate is the monthly price over the month's days."
    assert state["defect"].startswith("divides by 30")
    assert state["test_name"] == "test_half_month"
    assert "assert charge(300, 15) > 0" in state["test"]
    assert "return monthly / 30 * days  # <-- marked line" in state["code"]


def test_the_model_is_shown_the_requirement_the_code_and_the_defect(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = _jev_at(0.3)

    _judged(
        judge,
        [_defect_set("divides by 30")],
        [_test("test_half_month")],
        repo,
        requirements={"daily-rate": "The daily rate is the monthly price over the month's days."},
    )

    (request,) = judge.model_requests
    prompt = request["prompt"]
    assert "If the delivered code contained THIS DEFECT, would THIS TEST fail?" in prompt
    assert "The daily rate is the monthly price over the month's days." in prompt
    assert "divides by 30" in prompt
    assert "return monthly / 30 * days  # <-- marked line" in prompt
    assert "assert charge(300, 15) > 0" in prompt
    # Yes or no, and nothing else: no field for a reason, no token probability.
    assert set(request["schema"]["schema"]["properties"]) == {"fails"}


# --- carry --------------------------------------------------------------------


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
    assert second.verdicts[0].judged_by is first.verdicts[0].judged_by


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


def test_a_verdict_is_produced_again_when_the_code_jev_is_shown_changed(tmp_path):
    """Jev reads past the test and the defect, so the key must too: the same
    defect and test over different delivered code is a different question."""
    defects = [_defect_set("divides by 30")]
    tests = [_test("test_half_month")]

    first = _judged(_Judge(), defects, tests, _repo(tmp_path, {"test_billing.py": "x"}))
    (tmp_path / "billing.py").write_text("def charge(monthly, days):\n    return monthly * days\n")
    second_judge = _Judge()
    _judged(second_judge, defects, tests, tmp_path, prior=first.verdicts)

    assert second_judge.calls == 1


def test_a_verdict_is_produced_again_when_its_requirement_changed(tmp_path):
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set("divides by 30")]
    tests = [_test("test_half_month")]

    first = _judged(_Judge(), defects, tests, repo, requirements={"daily-rate": "one"})
    second_judge = _Judge()
    _judged(
        second_judge, defects, tests, repo, prior=first.verdicts, requirements={"daily-rate": "two"}
    )

    assert second_judge.calls == 1


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

    # Asserted on what was actually asked, not on the result: a stage that
    # re-judged everything and then discarded the answers would pass a count of
    # the verdicts and fail this.
    assert second_judge.pairs_asked() == {
        ("daily-rate-d1", "test_billing.py::test_leap_year"),
        ("daily-rate-d2", "test_billing.py::test_leap_year"),
    }
    assert len(second.verdicts) == 6
    assert sum(1 for verdict in second.verdicts if verdict.carried_from) == 4


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


# --- replay -------------------------------------------------------------------


def test_a_recorded_judgement_replays_with_no_live_call_to_the_same_bytes(tmp_path):
    """Both judges' answers, Jev's probability among them, come back from the
    recording: a REPLAY client over the same store reaches the same verdicts,
    byte for byte, and neither judge is called."""
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = [_defect_set("divides by 30", "ignores days")]
    tests = [_test("test_half_month"), _test("test_full_month")]
    recording = _Judge(
        kills=lambda defect_id, test_id: defect_id.endswith("d1"),
        unsure=lambda defect_id, test_id: test_id.endswith("full_month"),
    )
    recorded = _judged(recording, defects, tests, repo)
    assert recording.model_requests, "the fixture must exercise the model too"

    def refuse(**kwargs):
        raise AssertionError("a replayed judgement called the model")

    replayer = ModelClient(
        model=_DEFAULT_MODEL,
        mode=Mode.REPLAY,
        store=recording.client.store,
        completion_fn=refuse,
    )
    silent = _Judge()
    replayed = judge_pairs(defects, tests, _change_set(), replayer, repo=repo, jev=silent.jev)

    assert silent.calls == 0
    assert replayed.model_dump_json() == recorded.model_dump_json()


def test_the_stage_is_byte_identical_when_its_calls_finish_out_of_order(tmp_path):
    """Calls are issued concurrently, so the order they FINISH is whatever the
    provider decides. Two runs over one input must still agree byte for byte
    (M0.5). The double delays earlier calls more than later ones, so completion
    order is reliably the reverse of issue order."""
    import threading
    import time

    class _Reordering(_Judge):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._issued = 0
            self._lock = threading.Lock()

        def _post(self, url, body, headers):
            with self._lock:
                self._issued += 1
                issued = self._issued
            time.sleep(max(0.0, 0.06 - 0.01 * issued))
            with self._lock:
                return super()._post(url, body, headers)

    tests = [_test(f"test_{index}") for index in range(6)]
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    defects = _defect_set("divides by 30", "ignores days")

    def run(judge_cls):
        judge = judge_cls(
            kills=lambda defect_id, test_id: defect_id.endswith("d1"),
            model_says=lambda defect_id, test_id: {},
            unsure=lambda defect_id, test_id: test_id.endswith(("_1", "_4")),
        )
        log = UnusableAnswerLog()
        result = _judged(judge, [defects], tests, repo, unusable=log)
        return result.model_dump_json(), [entry.returned_id for entry in log.answers]

    assert run(_Reordering) == run(_Judge)


# --- the injection run decides which pairs are worth asking (#340) -------------


_D1 = "daily-rate-d1"
_D2 = "daily-rate-d2"
_T1 = "test_billing.py::test_half_month"
_T2 = "test_billing.py::test_full_month"


def _routed(tmp_path, skipped, kills=None, judge=None):
    """One `judge_pairs` run over two defects and two tests, with `skipped` set."""
    repo = _repo(tmp_path, {"test_billing.py": "x"})
    judge = judge or _Judge(kills=kills or (lambda defect_id, test_id: False))
    result = _judged(
        judge,
        [_defect_set("divides by 30", "ignores days")],
        [_test("test_half_month"), _test("test_full_month")],
        repo,
        skipped=skipped,
    )
    return result, judge


def test_a_skipped_pair_is_never_offered_to_the_judge(tmp_path):
    """The saving itself. A pair the run answered costs no call."""
    _, judge = _routed(
        tmp_path,
        skipped={(_D1, _T2): "not asked: the test still passed"},
        kills=lambda defect_id, test_id: defect_id == _D1,
    )

    assert (_D1, _T2) not in judge.pairs_asked()
    assert (_D1, _T1) in judge.pairs_asked(), "the failing test is still asked about"
    assert (_D2, _T2) in judge.pairs_asked(), "another defect's pairs are untouched"


def test_a_skipped_pair_comes_back_unjudged_with_its_reason(tmp_path):
    """Recorded, not dropped. A pair nobody records is indistinguishable from one
    judged `survives`, which is the whole reason `UnjudgedPair` exists."""
    result, _ = _routed(
        tmp_path,
        skipped={(_D1, _T2): "not asked: the test still passed"},
        kills=lambda defect_id, test_id: defect_id == _D1,
    )

    (entry,) = [e for e in result.unjudged if e.cause is UnjudgedCause.PASSED_UNDER_EDIT]
    assert (entry.defect_id, entry.test_id) == (_D1, _T2)
    assert entry.reason == "not asked: the test still passed"
    # No verdict for it, at any tier.
    assert (_D1, _T2) not in {(v.defect_id, v.test_id) for v in result.verdicts}


def test_a_defect_whose_asked_pairs_yield_no_kill_has_its_skipped_pairs_judged(tmp_path):
    """#340's rule 6, and the reason this stage runs in two passes.

    The run held back `_T2` because `_T1` failed under the edit. The judge then
    says `_T1` does not catch the defect after all — so the run demonstrated
    nothing usable about it, and the saving bought nothing.
    """
    result, judge = _routed(
        tmp_path,
        skipped={(_D1, _T2): "not asked: the test still passed"},
        kills=lambda defect_id, test_id: False,  # nothing kills anything
    )

    assert (_D1, _T2) in judge.pairs_asked(), "the held-back pair must be asked after all"
    assert (_D1, _T2) in {(v.defect_id, v.test_id) for v in result.verdicts}
    assert [e for e in result.unjudged if e.cause is UnjudgedCause.PASSED_UNDER_EDIT] == []


def test_the_second_pass_happens_before_the_result_is_returned(tmp_path):
    """The rating is derived from what this returns, so the intermediate state —
    where the pair is skipped and the defect has no kill — must never escape."""
    result, _ = _routed(
        tmp_path,
        skipped={(_D1, _T1): "not asked", (_D1, _T2): "not asked"},
        kills=lambda defect_id, test_id: False,
    )

    judged = {(v.defect_id, v.test_id) for v in result.verdicts}
    assert (_D1, _T1) in judged and (_D1, _T2) in judged


def test_a_kill_on_an_asked_pair_keeps_the_saving(tmp_path):
    """The control for the test above. Rule 6 must fire only where the run gave
    nothing usable, or it would undo the whole feature."""
    result, judge = _routed(
        tmp_path,
        skipped={(_D1, _T2): "not asked"},
        kills=lambda defect_id, test_id: (defect_id, test_id) == (_D1, _T1),
    )

    assert (_D1, _T2) not in judge.pairs_asked()
    (entry,) = [e for e in result.unjudged if e.cause is UnjudgedCause.PASSED_UNDER_EDIT]
    assert (entry.defect_id, entry.test_id) == (_D1, _T2)


def test_routing_off_asks_about_everything(tmp_path):
    """`ExecutionSettings.route_pairs` off reaches here as an empty mapping, and
    the stage behaves exactly as it did before #340."""
    result, judge = _routed(tmp_path, skipped=None)

    assert judge.pairs_asked() == {(_D1, _T1), (_D1, _T2), (_D2, _T1), (_D2, _T2)}
    assert len(result.verdicts) == 4


# --- the wiring ---------------------------------------------------------------
#
# The pipeline really calls this, the report really shows it, and the verdicts
# really reach the rating. Asserted on a real `run_review` rather than on
# `judge_pairs` alone: defect injection has repeatedly found a helper with a
# good unit test that the pipeline never calls (CLAUDE.md).

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
            "expected_behavior": "the code behaves as the criterion requires",
            "defective_behavior": "the code behaves as this defect describes",
            "type": "other",
            "description": _ENUMERATED_DESCRIPTION,
            "code_refs": [],
        }
    ],
    "reason": "",
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


def _review_over(built, judge: _Judge, capture: list | None = None, **kwargs):
    """One review over an already-built repo.

    Two reviews that must agree byte for byte have to run over the SAME repo:
    building one each compares reviews whose `reviewed_revision` differs, since
    identical content still gets commits stamped with the time they were made.
    """
    repo, base, head = built
    model_answers = {}
    if judge._model_says is not None:
        model_answers["_Fails"] = judge._model_says(None, None)
    client = client_dispatching(
        {"_Decomposition": _DECOMPOSITION, "_Enumeration": _ENUMERATED, **model_answers},
        capture=capture,
    )
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
        jev=judge.jev,
        **kwargs,
    )


def _killing(kills: bool) -> _Judge:
    return _Judge(kills=lambda defect_id, test_id: kills)


def test_the_pipeline_really_judges_pairs_through_jev(tmp_path):
    judge = _killing(True)
    review = _review_over(_built(tmp_path), judge)

    assert judge.pairs_asked() == {
        ("daily-rate/divides-by-thirty", "test_billing.py::test_prorate")
    }
    assert [v.judged_by for v in review.pair_verdicts] == [PairJudge.JEV]
    assert any(verdict.kills for verdict in review.pair_verdicts)


def test_the_pipeline_routes_an_uncertain_pair_from_jev_to_the_model(tmp_path):
    """#385's acceptance: the pipeline's defect judgement routes through Jev,
    then the model. Pinned on a real review, on both calls, in that order, and
    on the requirement text reaching both."""
    judge = _Judge(unsure=lambda defect_id, test_id: True, model_says=lambda d, t: {"fails": True})
    capture: list = []
    review = _review_over(_built(tmp_path), judge, capture=capture)

    assert len(judge.requests) == 1, "Jev was not asked first"
    assert judge.requests[0]["state"]["change_request"] == _QUOTE
    fallback = [call for call in capture if call["schema"] == "_Fails"]
    assert len(fallback) == 1, "the model was not asked about the pair Jev was unsure of"
    assert _QUOTE in fallback[0]["prompt"]
    (verdict,) = review.pair_verdicts
    assert (verdict.kills, verdict.judged_by, verdict.jev_probability) == (
        True,
        PairJudge.MODEL,
        0.3,
    )


def test_the_report_shows_every_rating_with_its_denominator(tmp_path):
    """DR-312 resolved question 3: never the class alone."""
    review = _review_over(_built(tmp_path), _killing(True))

    rendered = render_report(review)

    assert "kills 1 of 1 enumerated defects (static prediction)" in rendered


def test_a_surviving_pair_stops_the_criterion_reaching_strongly_supported(tmp_path):
    """#316's headline behaviour, and archetype #4's acceptance: a criterion whose
    on-point defect no test would fail on cannot be strongly supported."""
    built = _built(tmp_path)
    killing = _review_over(built, _killing(True))
    surviving = _review_over(built, _killing(False))

    def rating(review):
        return next(o.evidence_class for o in review.obligation_map if o.id == "daily-rate")

    assert rating(killing) == "strongly_supported"
    assert rating(surviving) == "unsupported"


def test_a_surviving_pair_earns_a_recommendation_and_a_killing_one_does_not(tmp_path):
    """The other half of the flip, on the recommendation axis (#250, #287)."""
    built = _built(tmp_path)
    killing = _review_over(built, _killing(True))
    surviving = _review_over(built, _killing(False))

    assert killing.recommendations == []
    assert [r.defect_id for r in surviving.recommendations] == ["daily-rate/divides-by-thirty"]


def test_the_verdicts_survive_a_round_trip_through_persisted_state(tmp_path):
    review = _review_over(_built(tmp_path), _Judge(unsure=lambda d, t: True))

    reloaded = Review.model_validate_json(review.to_canonical_json())

    assert reloaded.pair_verdicts == review.pair_verdicts
    assert reloaded.pair_verdicts[0].jev_probability == 0.3
    assert reloaded.to_canonical_json() == review.to_canonical_json()


def test_two_runs_over_the_same_input_agree_byte_for_byte(tmp_path):
    built = _built(tmp_path)

    first = _review_over(built, _killing(True))
    second = _review_over(built, _killing(True))

    assert first.to_canonical_json() == second.to_canonical_json()
    assert render_report(first) == render_report(second)


def test_jev_spend_is_reported_under_its_own_stage(tmp_path):
    """A priced review has to tell Jev's cost apart from the model's, and the
    model's share of the judgements from Jev's (#385's acceptance)."""
    built = _built(tmp_path)
    repo, base, head = built
    judge = _Judge(unsure=lambda d, t: True)
    client = client_dispatching({"_Decomposition": _DECOMPOSITION, "_Enumeration": _ENUMERATED})
    run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client,
        reviewed_revision=head,
        jev=judge.jev,
    )

    stages = [call["stage"] for call in client.observed_calls]
    assert stages.count(JEV_STAGE) == 1
    (jev_call,) = [call for call in client.observed_calls if call["stage"] == JEV_STAGE]
    assert jev_call["usage"]["cost_usd"] > 0
    assert "defect-to-test pair mapping" in stages


def test_a_continued_run_carries_verdicts_through_the_ledger(tmp_path):
    """The ledger really carries this, end to end — not `prior=` handed in by a test.

    Asserted on the calls the second run issued, because a stage that re-judged
    everything and then threw the answers away would satisfy a count of the
    verdicts.
    """
    repo, base, head = _built(tmp_path)

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    sink: list = []
    run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching({"_Decomposition": _DECOMPOSITION, "_Enumeration": _ENUMERATED}),
        reviewed_revision=head,
        ledger_sink=sink,
        jev=_killing(True).jev,
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

    judge = _killing(True)
    second = run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, second_head),
        repo=repo,
        client=client_dispatching({"_Decomposition": _DECOMPOSITION, "_Enumeration": _ENUMERATED}),
        reviewed_revision=second_head,
        ledger_prior=entry,
        jev=judge.jev,
    )

    assert judge.pairs_asked() == {("daily-rate/divides-by-thirty", "test_extra.py::test_extra")}
    carried = [verdict for verdict in second.pair_verdicts if verdict.carried_from]
    assert len(carried) == 1
    assert carried[0].test_id == "test_billing.py::test_prorate"


def test_a_prefiltered_pair_is_named_in_the_report(tmp_path):
    """The recorded exclusion is rendered, not merely stored.

    Exercised on a constructed review rather than on a real run: the prefilter's
    rule is sound and therefore fires almost never, so waiting for real input to
    trigger it would be a test that passes by luck (see `reachability`).
    """
    review = _review_over(_built(tmp_path), _killing(True))
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

    assert "Pairs left unjudged" in rendered
    assert "a criterion's rating cannot account for these" in rendered
    assert "[prefiltered]" in rendered
    assert "daily-rate/divides-by-thirty x test_far_away.py::test_unrelated" in rendered
    assert "no path to the defect exists" in rendered
