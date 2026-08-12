"""M5.2 acceptance: per criterion, judge whether the mapped tests would fail
under a named plausible defect — a non-discriminating input is judged
non-discriminating with the specific reason; a genuinely strong test is judged
discriminating.

Since #191 that is two calls, not one: what could plausibly go wrong, and then
whether the tests would catch it. The tests below that are about the split —
which call carries what, and what an unrelated test edit may not move — live at
the bottom.

Discrimination is a schema-constrained model call; per the replay-first
invariant these tests inject the recorded response — no live calls. Prompt
quality (that the *model* judges archetype #4's /30 input non-discriminating)
is verified by a live RECORD run, shown in the PR, not here.
"""

import json
import tempfile

from acceptance.config import DEFAULT_DEFECT_VERDICT_BATCH_SIZE
from acceptance.evidence.discrimination import enumerate_defects, judge_discrimination
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import (
    ChangeSet,
    DiffHunk,
    FileChange,
    Obligation,
    ObligationType,
    TestEvidence,
)
from tests.support import client_dispatching


def _obligation(obligation_id: str, description: str) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
    )


def _evidence(identifier: str, obligation_ids: list[str], assertions: list[str]) -> TestEvidence:
    return TestEvidence(
        identifier=identifier,
        location=identifier.split("::", 1)[0],
        assertions=assertions,
        mapped_obligations=obligation_ids,
    )


def _change_set() -> ChangeSet:
    hunk = DiffHunk(
        header="@@ -1 +1 @@",
        old_start=1,
        old_lines=1,
        new_start=1,
        new_lines=1,
        content="+def prorate(...): ...",
    )
    return ChangeSet(
        base_revision="b",
        head_revision="h",
        files=[FileChange(path="billing.py", status="modified", category="source", hunks=[hunk])],
    )


def _enumeration(*by_obligation: tuple[str, list[str]]) -> dict:
    """An enumeration response: per criterion, the defects it names, in order.

    Order is what the ids are minted from, so a fixture that cares which verdict
    lands on which defect states them in the order it means.
    """
    return {
        "obligations": [
            {
                "obligation_id": obligation_id,
                "defects": [{"description": description} for description in descriptions],
            }
            for obligation_id, descriptions in by_obligation
        ]
    }


def _verdicts(*by_defect: tuple[str, bool, str]) -> dict:
    return {
        "verdicts": [
            {"defect_id": defect_id, "would_be_caught": caught, "reason": reason}
            for defect_id, caught, reason in by_defect
        ]
    }


def _client(enumeration: dict, verdicts: dict, calls: list | None = None) -> ModelClient:
    dispatch = {"_Enumeration": enumeration, "_DefectVerdicts": verdicts}
    if calls is None:
        return client_dispatching(dispatch)

    def completion_fn(**kwargs):
        from types import SimpleNamespace

        name = kwargs["response_format"]["json_schema"]["name"]
        calls.append((name, kwargs))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(dispatch[name])))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    return ModelClient(
        model="x",
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
    )


def _exploding_client():
    def boom(**kwargs):
        raise AssertionError("no criterion had a mapped test; no model call should be made")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


def test_non_discriminating_input_is_judged_non_discriminating_with_a_reason():
    obligations = [_obligation("daily-rate", "Daily rate is price / days_in_month")]
    evidence = [
        _evidence(
            "test_billing.py::test_half", ["daily-rate"], ["assert prorate(30.0, 15, 30) == 15.0"]
        )
    ]
    client = _client(
        _enumeration(("daily-rate", ["hard-code the divisor as / 30 instead of / days_in_month"])),
        _verdicts(
            (
                "daily-rate::d1",
                False,
                "the test uses a 30-day month, so /30 and /days_in_month coincide (both give 15.0)",
            )
        ),
    )

    result = judge_discrimination(obligations, evidence, _change_set(), client)

    assert len(result) == 1
    assert result[0].obligation_id == "daily-rate"
    assert result[0].discriminating is False
    assert result[0].defects[0].would_be_caught is False
    assert "coincide" in result[0].defects[0].reason


def test_a_caught_defect_makes_the_criterion_discriminating():
    obligations = [_obligation("daily-rate", "Daily rate is price / days_in_month")]
    evidence = [
        _evidence(
            "test_billing.py::test_strong", ["daily-rate"], ["assert prorate(31.0, 10, 31) == 10.0"]
        )
    ]
    client = _client(
        _enumeration(("daily-rate", ["hard-code the divisor as / 30"])),
        _verdicts(
            (
                "daily-rate::d1",
                True,
                "for a 31-day month /30 gives 10.33, not 10.0, so the test fails under the defect",
            )
        ),
    )

    result = judge_discrimination(obligations, evidence, _change_set(), client)

    assert result[0].discriminating is True


def test_discriminating_is_true_if_any_defect_is_caught():
    obligations = [_obligation("ob-1", "A")]
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"])]
    client = _client(
        _enumeration(("ob-1", ["d1", "d2"])),
        _verdicts(("ob-1::d1", False, "."), ("ob-1::d2", True, ".")),
    )

    result = judge_discrimination(obligations, evidence, _change_set(), client)

    assert result[0].discriminating is True


def test_criteria_without_mapped_tests_are_not_judged():
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    # Only ob-1 has a mapped test. ob-2's defects are still enumerated — that is
    # what keeps the enumeration request independent of the mapping — but no
    # verdict is reached on them, so it produces no discrimination.
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"])]
    client = _client(
        _enumeration(("ob-1", ["d"]), ("ob-2", ["d"])),
        _verdicts(("ob-1::d1", True, ".")),
    )

    result = judge_discrimination(obligations, evidence, _change_set(), client)

    assert {r.obligation_id for r in result} == {"ob-1"}


def test_no_mapped_tests_makes_no_model_call():
    """Not even the enumeration call. Enumeration covers every criterion, but
    only while some criterion is going to be judged — with nothing mapped there
    is no verdict to reach and the defects would be bought for nothing."""
    obligations = [_obligation("ob-1", "A")]

    result = judge_discrimination(obligations, [], _change_set(), _exploding_client())

    assert result == []


def test_an_obligation_the_model_omits_is_conservatively_non_discriminating():
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    evidence = [
        _evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"]),
        _evidence("t.py::test_b", ["ob-2"], ["assert g() == 2"]),
    ]
    # The enumeration only addressed ob-1.
    client = _client(_enumeration(("ob-1", ["d"])), _verdicts(("ob-1::d1", True, ".")))

    result = judge_discrimination(obligations, evidence, _change_set(), client)

    by_id = {r.obligation_id: r for r in result}
    assert by_id["ob-1"].discriminating is True
    # ob-2 was omitted -> no defects -> not shown to discriminate.
    assert by_id["ob-2"].discriminating is False
    assert by_id["ob-2"].defects == []


# ---------------------------------------------------------------------------
# The split itself (#191)
# ---------------------------------------------------------------------------


def test_enumeration_and_verdict_are_separate_calls():
    obligations = [_obligation("ob-1", "A")]
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"])]
    calls: list = []

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(_enumeration(("ob-1", ["d"])), _verdicts(("ob-1::d1", True, ".")), calls),
    )

    assert [name for name, _ in calls] == ["_Enumeration", "_DefectVerdicts"]


def test_the_enumeration_call_carries_no_test_evidence():
    """The property the whole split rests on. If a test's name, inputs or
    assertions reach the enumeration request, then editing that test re-rolls
    which defects are considered, and no amount of care downstream recovers it."""
    obligations = [_obligation("ob-1", "A")]
    evidence = [
        _evidence(
            "tests/test_billing.py::test_distinctive_name",
            ["ob-1"],
            ["assert prorate(31.0, 10, 31) == 10.0"],
        )
    ]
    calls: list = []

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(_enumeration(("ob-1", ["d"])), _verdicts(("ob-1::d1", True, ".")), calls),
    )

    enumeration = next(kwargs for name, kwargs in calls if name == "_Enumeration")
    sent = json.dumps(enumeration["messages"])
    assert "test_distinctive_name" not in sent
    assert "prorate(31.0, 10, 31)" not in sent
    # The two things it IS determined by.
    assert "ob-1" in sent
    assert "def prorate" in sent


def test_a_verdict_call_carries_no_more_than_the_configured_number_of_obligations():
    obligations = [_obligation(f"ob-{n}", f"criterion {n}") for n in range(1, 6)]
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in range(1, 6)]
    calls: list = []

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(
            _enumeration(*((f"ob-{n}", ["d"]) for n in range(1, 6))),
            _verdicts(*((f"ob-{n}::d1", True, ".") for n in range(1, 6))),
            calls,
        ),
        verdict_batch_size=2,
    )

    verdict_calls = [kwargs for name, kwargs in calls if name == "_DefectVerdicts"]
    assert len(verdict_calls) == 3  # 5 criteria at 2 per call
    for kwargs in verdict_calls:
        sent = json.dumps(kwargs["messages"])
        assert sum(f"criterion id=ob-{n}" in sent for n in range(1, 6)) <= 2


def test_the_number_of_obligations_per_verdict_call_reaches_the_recorded_request():
    """A batch size that is not in the request is not a determinism control: two
    runs at different sizes would share a transcript and replay each other's
    answers. `Batch.request_partition()` is what puts it there."""
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in (1, 2)]

    recorded = {}
    for size in (1, 2):
        client = _client(
            _enumeration(("ob-1", ["d"]), ("ob-2", ["d"])),
            _verdicts(("ob-1::d1", True, "."), ("ob-2::d1", True, ".")),
        )
        judge_discrimination(obligations, evidence, _change_set(), client, verdict_batch_size=size)
        recorded[size] = [
            record["request"]["partition"]
            for record in (json.loads(path.read_text()) for path in client.store.root.iterdir())
            if "partition" in record.get("request", {})
        ]

    # Size 2 puts both criteria in one call, so the two runs differ in how many
    # verdict calls they make as well — but the point being pinned is narrower:
    # the size itself is in the recorded request, so the two can never share a
    # transcript even where the messages coincide.
    assert {"size": 1} in recorded[1]
    assert {"size": 2} in recorded[2]
    assert client.partition_sizes_in_force["defect verdict"] == 2


def test_the_verdict_batch_size_defaults_to_one_criterion_per_call():
    """Not an arbitrary default: DR-180's finding is that one call carrying many
    criteria's verdicts is where the instability lives."""
    assert DEFAULT_DEFECT_VERDICT_BATCH_SIZE == 1


def test_editing_a_test_leaves_a_different_obligations_enumerated_defects_unchanged():
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    enumeration = _enumeration(("ob-1", ["d"]), ("ob-2", ["d"]))

    before: list = []
    enumerate_defects(
        obligations,
        _change_set(),
        _client(enumeration, _verdicts(), before),
    )
    after: list = []
    enumerate_defects(
        obligations,
        _change_set(),
        _client(enumeration, _verdicts(), after),
    )

    # The requests are byte-identical, which is stronger than "the answers
    # matched": an identical request replays from its transcript, so the model
    # is never asked again and cannot answer differently.
    assert [kwargs["messages"] for _, kwargs in before] == [
        kwargs["messages"] for _, kwargs in after
    ]


def test_two_runs_over_the_same_obligations_and_code_enumerate_the_same_defects():
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    enumeration = _enumeration(("ob-1", ["d1", "d2"]), ("ob-2", ["d"]))
    verdicts = _verdicts(("ob-1::d1", True, "."), ("ob-1::d2", False, "."), ("ob-2::d1", True, "."))
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in (1, 2)]

    first = judge_discrimination(
        obligations, evidence, _change_set(), _client(enumeration, verdicts)
    )
    second = judge_discrimination(
        obligations, evidence, _change_set(), _client(enumeration, verdicts)
    )

    assert [j.to_dict() for j in first] == [j.to_dict() for j in second]
