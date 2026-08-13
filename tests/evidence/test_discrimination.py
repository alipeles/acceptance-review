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
import os
import tempfile

from acceptance.config import DEFAULT_DEFECT_VERDICT_BATCH_SIZE
from acceptance.evidence.discrimination import judge_discrimination
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.supplied_ids import UnusableAnswerLog
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


def test_the_verdict_bound_counts_criteria_and_not_defects():
    """Gate 2 raised this one, and it was right: with one defect per criterion,
    batching by criterion and batching by defect volume are indistinguishable,
    so the test above passes under either.

    Here one criterion carries five defects and the rest carry one. An
    implementation that filled each call up to a defect budget would put the
    four one-defect criteria into a single call; bounding by criteria cannot."""
    obligations = [_obligation(f"ob-{n}", f"criterion {n}") for n in range(1, 6)]
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in range(1, 6)]
    enumerated = [("ob-1", [f"d{i}" for i in range(1, 6)])]
    enumerated += [(f"ob-{n}", ["d"]) for n in range(2, 6)]
    verdicts = [(f"ob-1::d{i}", True, ".") for i in range(1, 6)]
    verdicts += [(f"ob-{n}::d1", True, ".") for n in range(2, 6)]
    calls: list = []

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(_enumeration(*enumerated), _verdicts(*verdicts), calls),
        verdict_batch_size=2,
    )

    verdict_calls = [kwargs for name, kwargs in calls if name == "_DefectVerdicts"]
    for kwargs in verdict_calls:
        sent = json.dumps(kwargs["messages"])
        carried = sum(f"criterion id=ob-{n}" in sent for n in range(1, 6))
        assert carried <= 2, f"a verdict call carried {carried} criteria, over the bound of 2"
    # And the lopsided defect counts did not change how many calls it takes:
    # five criteria at two per call is three, whatever the defects weigh.
    assert len(verdict_calls) == 3


def test_the_number_of_obligations_per_verdict_call_reaches_the_recorded_request():
    """A batch size that is not in the request is not a determinism control: two
    runs at different sizes would share a transcript and replay each other's
    answers. `Batch.request_partition()` is what puts it there."""
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in (1, 2)]

    recorded = {}
    in_force = {}
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
        in_force[size] = client.partition_sizes_in_force

    # Read off the stage, not just off the pile of transcripts: `{"size": 1}`
    # could otherwise be some other stage's partition and the assertion would
    # hold on a verdict call that recorded nothing.
    assert in_force[1]["defect verdict"] == 1
    assert in_force[2]["defect verdict"] == 2
    # And it is in the recorded request itself, which is what makes it a
    # determinism control: two runs at different sizes can never share a
    # transcript, even where the messages coincide.
    assert {"size": 1} in recorded[1]
    assert {"size": 2} in recorded[2]
    assert {"size": 2} not in recorded[1]
    assert client.partition_sizes_in_force["defect verdict"] == 2


def test_the_verdict_batch_size_defaults_to_one_criterion_per_call():
    """Not an arbitrary default: DR-180's finding is that one call carrying many
    criteria's verdicts is where the instability lives."""
    assert DEFAULT_DEFECT_VERDICT_BATCH_SIZE == 1


def test_editing_a_test_leaves_a_different_obligations_enumerated_defects_unchanged():
    """Gate 2 round 2 was right that the first version of this test edited
    nothing: it called the stage twice with identical arguments, which
    demonstrates the request is deterministic and says nothing at all about
    insensitivity to a test edit.

    So ob-1's mapped test really is edited between the two runs — renamed, with
    different inputs and a different assertion, all of them distinctive enough
    to find in the request — and ob-2's enumeration must not move.
    """
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    enumeration = _enumeration(("ob-1", ["d"]), ("ob-2", ["d"]))
    original = [
        _evidence("t.py::test_original_name", ["ob-1"], ["assert f(1) == 'original'"]),
        _evidence("t.py::test_untouched", ["ob-2"], ["assert g() == 2"]),
    ]
    edited = [
        _evidence("t.py::test_renamed_entirely", ["ob-1"], ["assert f(99) == 'rewritten'"]),
        _evidence("t.py::test_untouched", ["ob-2"], ["assert g() == 2"]),
    ]

    requests = []
    for evidence in (original, edited):
        calls: list = []
        judge_discrimination(
            obligations,
            evidence,
            _change_set(),
            _client(
                enumeration, _verdicts(("ob-1::d1", True, "."), ("ob-2::d1", True, ".")), calls
            ),
        )
        requests.append([kwargs["messages"] for name, kwargs in calls if name == "_Enumeration"])

    # Byte-identical, which is stronger than "the answers matched": an identical
    # request replays from its transcript, so the model is never asked again and
    # cannot answer differently.
    assert requests[0] == requests[1]
    # And the edit was real — it reached the stage, just not this request.
    sent = json.dumps(requests[1])
    assert "test_renamed_entirely" not in sent and "rewritten" not in sent


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


def test_the_split_loses_no_defect_that_was_enumerated_and_judged():
    """The governing constraint of the whole change: stability must not be
    bought by blunting the judge (DR-180). Splitting one call into two adds two
    places a defect can be dropped — a batch boundary, and the id join — and
    neither is visible downstream, because a lost defect looks exactly like a
    defect that was never named.

    Gate 2 asked for this and named the loss modes. Batches deliberately
    straddle: three criteria at one per verdict call, with uneven defect counts,
    so a defect surviving is not an artefact of everything fitting in one call.
    """
    obligations = [_obligation(f"ob-{n}", f"criterion {n}") for n in (1, 2, 3)]
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in (1, 2, 3)]
    enumerated = {"ob-1": ["d1", "d2", "d3"], "ob-2": ["d1"], "ob-3": ["d1", "d2"]}
    verdicts = _verdicts(
        *(
            (f"{obligation_id}::d{index}", index % 2 == 1, ".")
            for obligation_id, defects in enumerated.items()
            for index in range(1, len(defects) + 1)
        )
    )

    result = judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(_enumeration(*((oid, ds) for oid, ds in enumerated.items())), verdicts),
        verdict_batch_size=1,
    )

    judged = {j.obligation_id: [d.description for d in j.defects] for j in result}
    assert judged == enumerated, "a defect that was enumerated and judged did not survive"


def test_a_defect_the_verdict_call_never_answered_is_reported_as_indeterminate():
    """The other half of not blunting the judge. An enumerated defect with no
    verdict is a judgement that was not obtained, and must not be absorbed as
    'no defect survives' — that reads as evidence of discrimination the run
    never established."""
    obligations = [_obligation("ob-1", "A")]
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f()"])]
    unusable = UnusableAnswerLog()

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        # Two defects named, one judged — and the answer names an id the call
        # never supplied, which is how the stage detects the shortfall.
        _client(
            _enumeration(("ob-1", ["d1", "d2"])),
            _verdicts(("ob-1::d1", True, "."), ("ob-1::d9", True, "invented")),
        ),
        unusable=unusable,
    )

    assert "ob-1" in unusable.indeterminate_obligations


def test_the_verdict_call_carries_the_changed_code():
    """Whether a test fails under a defect is a question about the code that
    test exercises — what the assertion pins, whether the input even reaches the
    changed branch. It cannot be answered well from the defect sentence and the
    assertion text alone.

    #191's first cut removed the diff from this call so that partitioning would
    be cheap. Nothing caught it: not this suite, and not the tool's own
    unrequested-change detection running over that very diff, across three
    rounds. Measured, it took evidence-class movement across resample runs from
    2 to 16. This is the guard that was missing.
    """
    obligations = [_obligation("ob-1", "A")]
    evidence = [_evidence("t.py::test_a", ["ob-1"], ["assert f() == 1"])]
    calls: list = []

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(_enumeration(("ob-1", ["d"])), _verdicts(("ob-1::d1", True, ".")), calls),
    )

    verdict = next(kwargs for name, kwargs in calls if name == "_DefectVerdicts")
    assert "def prorate" in json.dumps(verdict["messages"]), (
        "the verdict call must see the changed code, not only the defect wording"
    )


def test_the_verdict_calls_share_the_changed_code_as_a_common_prefix():
    """The diff is now repeated in every verdict call, so it has to land in the
    provider's prompt cache rather than on the bill N times. A prompt cache keys
    on a *prefix*, so the invariant block has to come before the part that
    varies per batch — reversed, every call is a miss."""
    obligations = [_obligation("ob-1", "A"), _obligation("ob-2", "B")]
    evidence = [_evidence(f"t.py::test_{n}", [f"ob-{n}"], ["assert f()"]) for n in (1, 2)]
    calls: list = []

    judge_discrimination(
        obligations,
        evidence,
        _change_set(),
        _client(
            _enumeration(("ob-1", ["d"]), ("ob-2", ["d"])),
            _verdicts(("ob-1::d1", True, "."), ("ob-2::d1", True, ".")),
            calls,
        ),
        verdict_batch_size=1,
    )

    prompts = [
        kwargs["messages"][-1]["content"] for name, kwargs in calls if name == "_DefectVerdicts"
    ]
    assert len(prompts) == 2, "one call per criterion at a batch size of 1"

    shared = os.path.commonprefix(prompts)
    assert "def prorate" in shared, (
        "the changed code must fall inside the shared prefix, or it is a cache miss every call"
    )
    # And the part that varies really does vary, so the assertion above is not
    # passing because the two prompts are simply identical.
    assert prompts[0] != prompts[1]
