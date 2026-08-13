"""M4.2 acceptance: each obligation is either mapped to a candidate test or
flagged unmapped, and the §11.1 mapping-accuracy metric reports a real number
against archetype labels.

Mapping is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
A client that raises proves the no-candidate-tests path takes no model call.
"""

import json
import tempfile
from pathlib import Path

from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.benchmark.scoring import score_case
from acceptance.change.diff import extract_change_set
from acceptance.evidence.discovery import DiscoveredTest, DiscoveryReason, discover_tests
from acceptance.evidence.mapping import apply_test_mapping, map_tests_to_obligations
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import Obligation, ObligationType, Review
from tests.support import client_answering_per_call, client_returning, make_obligation

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _test(test_id: str, source: str = "def t():\n    pass") -> DiscoveredTest:
    return DiscoveredTest(
        test_id=test_id,
        file=test_id.split("::", 1)[0],
        reasons=[DiscoveryReason.CALLS_CHANGED_SYMBOL],
        source=source,
    )


def _exploding_client() -> ModelClient:
    def boom(**kwargs):
        raise AssertionError("a model call was issued when there were no candidate tests")

    return ModelClient(
        model="x", mode=Mode.RECORD, store=TranscriptStore(tempfile.mkdtemp()), completion_fn=boom
    )


# --- unit: map_tests_to_obligations ---


def test_a_test_maps_to_the_obligation_it_evidences():
    obligations = [
        make_obligation("ob-1", "Discount reduces the total", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "Result is money-formatted", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("test_cart.py::test_discount")]
    response = {
        "mappings": [
            {
                "test_id": "test_cart.py::test_discount",
                "obligation_ids": ["ob-1"],
                "rationale": "asserts total",
            },
        ]
    }

    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    assert len(result.mappings) == 1
    assert result.mappings[0].obligation_ids == ["ob-1"]
    # ob-2 has no mapped test.
    assert result.unmapped_obligation_ids == ["ob-2"]


def test_a_test_can_map_to_multiple_obligations():
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_both")]
    response = {
        "mappings": [
            {"test_id": "t.py::test_both", "obligation_ids": ["ob-1", "ob-2"], "rationale": "both"},
        ]
    }

    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    assert result.mappings[0].obligation_ids == ["ob-1", "ob-2"]
    assert result.unmapped_obligation_ids == []


def test_the_instruction_requires_every_overlapping_obligation_not_the_closest():
    """#266's Gate 2: the mechanism above was never the problem — the stage
    already records whatever ids come back. The instruction was.

    Mapping saw a test's full source, described its behavior accurately in the
    rationale, and then returned ONE id from a pair of obligations that restate
    each other, leaving the other rated `unsupported` with its evidence sitting
    in the same response. Nothing told it overlapping obligations are not
    alternatives.

    What this test demonstrates is narrow and worth stating plainly: it fails if
    the instruction is dropped, so it guards against silent regression. It does
    NOT demonstrate that the model obeys it — that is a judgement, and the
    evidence for it is a recorded run, not an assertion here.

    The wording is also deliberately not tied to any one mandate shape. A
    requirement-and-its-test-demand pair is how overlap shows up in this repo's
    own task files, but it must stay an illustration: nothing constrains how a
    user writes a mandate, and an instruction naming two fixed kinds of
    obligation would be wrong for the first mandate that overlaps differently.
    """
    from acceptance.evidence.mapping import _SYSTEM_PROMPT

    # Normalised: the prompt is hard-wrapped, so every phrase below spans a line
    # break in the source and would not match literally.
    instruction = " ".join(_SYSTEM_PROMPT.split())

    assert "return EVERY id its assertions are aimed at, not the single best one" in instruction
    assert "Do not choose between overlapping obligations; return them all." in instruction
    # Framed as an example, not as a taxonomy of obligation kinds.
    assert "illustration only" in instruction
    assert "never assume the mandate is shaped this way" in instruction
    # The empty answer stays available — "return them all" must not read as
    # pressure to map a test that is aimed at nothing.
    assert "a test aimed at nothing still maps to nothing" in instruction


def test_a_test_evidencing_nothing_leaves_obligations_unmapped():
    # Discovery is recall-forward; mapping is the precision filter. A test that
    # touches changed code but asserts nothing about an obligation maps to none.
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_incidental")]
    response = {
        "mappings": [
            {"test_id": "t.py::test_incidental", "obligation_ids": [], "rationale": "setup only"},
        ]
    }

    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    assert result.mappings[0].obligation_ids == []
    assert result.unmapped_obligation_ids == ["ob-1"]


def test_unknown_ids_are_dropped():
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_real")]
    response = {
        "mappings": [
            {
                "test_id": "t.py::test_ghost",
                "obligation_ids": ["ob-1"],
                "rationale": "not a real test",
            },
            {
                "test_id": "t.py::test_real",
                "obligation_ids": ["ob-nope", "ob-1"],
                "rationale": "one bad id",
            },
        ]
    }

    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    # The ghost test id is dropped entirely; the bogus obligation id is filtered.
    assert len(result.mappings) == 1
    assert result.mappings[0].test_id == "t.py::test_real"
    assert result.mappings[0].obligation_ids == ["ob-1"]


def test_no_candidate_tests_makes_no_model_call_and_flags_all_unmapped():
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
    ]

    result = map_tests_to_obligations(obligations, [], _exploding_client())

    assert result.mappings == []
    assert result.unmapped_obligation_ids == ["ob-1", "ob-2"]


# --- partitioning the mapping request (DR-164, #164) ---


def _mapped(prompt: str, obligation_id: str) -> dict:
    """Map every test named in `prompt` to `obligation_id` — a stand-in for a
    model that answers only about the tests it was actually given."""
    return {
        "mappings": [
            {"test_id": test_id, "obligation_ids": [obligation_id], "rationale": "."}
            for test_id in _test_ids_in(prompt)
        ]
    }


def _test_ids_in(prompt: str) -> list[str]:
    return [
        line.removeprefix("### ").strip() for line in prompt.splitlines() if line.startswith("### ")
    ]


def test_the_tests_are_split_across_several_calls():
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test(f"t.py::test_{n:02d}") for n in range(10)]
    client, calls = client_answering_per_call(lambda p: _mapped(p, "ob-1"))

    map_tests_to_obligations(obligations, tests, client, batch_size=4)

    assert len(calls) == 3
    assert [len(_test_ids_in(call["prompt"])) for call in calls] == [4, 4, 2]


def test_every_test_is_judged_against_every_obligation_across_the_calls():
    """Partitioning changes how the question is asked, never which pairs are
    considered: each call repeats all obligations, and the calls together cover
    all tests."""
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
        make_obligation("ob-3", "C", ObligationType.FUNCTIONAL),
    ]
    tests = [_test(f"t.py::test_{n:02d}") for n in range(7)]
    client, calls = client_answering_per_call(lambda p: _mapped(p, "ob-1"))

    map_tests_to_obligations(obligations, tests, client, batch_size=3)

    judged = [test_id for call in calls for test_id in _test_ids_in(call["prompt"])]
    assert sorted(judged) == sorted(t.test_id for t in tests)
    assert len(judged) == len(set(judged))  # no test judged twice
    for call in calls:
        for obligation in obligations:
            assert f"id={obligation.id}" in call["prompt"]


def test_the_per_call_results_are_merged():
    """A judgment made in any batch reaches the final mapping — the merge is
    what makes partitioning invisible downstream."""
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_a"), _test("t.py::test_b")]

    def responder(prompt: str) -> dict:
        # Each batch holds one test; they map to different obligations, so a
        # result that kept only one call's answer would lose an obligation.
        test_id = _test_ids_in(prompt)[0]
        target = "ob-1" if test_id.endswith("_a") else "ob-2"
        return {
            "mappings": [
                {"test_id": test_id, "obligation_ids": [target], "rationale": "."},
            ]
        }

    client, calls = client_answering_per_call(responder)
    result = map_tests_to_obligations(obligations, tests, client, batch_size=1)

    assert len(calls) == 2
    assert {m.test_id: m.obligation_ids for m in result.mappings} == {
        "t.py::test_a": ["ob-1"],
        "t.py::test_b": ["ob-2"],
    }
    assert result.unmapped_obligation_ids == []


def test_a_batch_may_not_answer_for_a_test_outside_it():
    """A model that echoes a neighbouring batch's test would otherwise have its
    duplicate judgment merged alongside the real one, making the result depend
    on which batch answered last."""
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_a"), _test("t.py::test_b")]

    def responder(prompt: str) -> dict:
        # Every batch claims to have judged BOTH tests, mapping each to whatever
        # its own batch is about.
        target = "ob-1" if _test_ids_in(prompt)[0].endswith("_a") else "ob-2"
        return {
            "mappings": [
                {"test_id": "t.py::test_a", "obligation_ids": [target], "rationale": "."},
                {"test_id": "t.py::test_b", "obligation_ids": [target], "rationale": "."},
            ]
        }

    client, _ = client_answering_per_call(responder)
    result = map_tests_to_obligations(obligations, tests, client, batch_size=1)

    # One entry per test, each carrying its own batch's answer.
    assert [m.test_id for m in result.mappings] == ["t.py::test_a", "t.py::test_b"]
    assert result.mappings[0].obligation_ids == ["ob-1"]
    assert result.mappings[1].obligation_ids == ["ob-2"]


def test_the_merged_mapping_does_not_depend_on_the_order_the_tests_arrive_in():
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test(f"t.py::test_{n:02d}") for n in range(6)]

    forward, _ = client_answering_per_call(lambda p: _mapped(p, "ob-1"))
    reverse, _ = client_answering_per_call(lambda p: _mapped(p, "ob-1"))

    first = map_tests_to_obligations(obligations, tests, forward, batch_size=2)
    second = map_tests_to_obligations(obligations, list(reversed(tests)), reverse, batch_size=2)

    assert first.model_dump() == second.model_dump()


def test_each_batch_is_recorded_as_its_own_request():
    """Replay depends on it: one transcript per batch, keyed distinctly, and
    carrying the partition size so changing the control invalidates them."""
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test(f"t.py::test_{n:02d}") for n in range(4)]
    client, _ = client_answering_per_call(lambda p: _mapped(p, "ob-1"))

    map_tests_to_obligations(obligations, tests, client, batch_size=2)

    keys = list(Path(client.store.root).glob("*.json"))
    assert len(keys) == 2  # two batches, two distinct transcripts
    recorded = [json.loads(path.read_text())["request"] for path in keys]
    assert all(request["partition"] == {"size": 2} for request in recorded)


def test_changing_the_batch_size_changes_every_request_key():
    """The control is hashed like the seed. These inputs make one batch either
    way, so only the descriptor distinguishes them — without it, a run under a
    changed control would silently replay the old recordings."""
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_a")]

    first, _ = client_answering_per_call(lambda p: _mapped(p, "ob-1"))
    second, _ = client_answering_per_call(lambda p: _mapped(p, "ob-1"))
    map_tests_to_obligations(obligations, tests, first, batch_size=4)
    map_tests_to_obligations(obligations, tests, second, batch_size=8)

    def keys(client):
        return {path.name for path in Path(client.store.root).glob("*.json")}

    assert len(keys(first)) == len(keys(second)) == 1
    assert keys(first) != keys(second)


def test_repeating_a_run_reuses_the_recorded_batches():
    """The other half of determinism: unchanged input under an unchanged
    control must hit the same keys, or every re-run would re-record."""
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test(f"t.py::test_{n:02d}") for n in range(4)]
    client, calls = client_answering_per_call(lambda p: _mapped(p, "ob-1"))

    first = map_tests_to_obligations(obligations, tests, client, batch_size=2)
    second = map_tests_to_obligations(obligations, tests, client, batch_size=2)

    assert len(calls) == 2  # the second run made no live call: all four batches hit cache
    assert first.model_dump() == second.model_dump()


# --- unit: apply_test_mapping ---


def test_apply_test_mapping_populates_test_evidence():
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_a"), _test("t.py::test_ab")]
    response = {
        "mappings": [
            {"test_id": "t.py::test_a", "obligation_ids": ["ob-1"], "rationale": "."},
            {"test_id": "t.py::test_ab", "obligation_ids": ["ob-1", "ob-2"], "rationale": "."},
        ]
    }
    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    mapped = {o.id: o for o in apply_test_mapping(obligations, result)}

    assert mapped["ob-1"].test_evidence == ["t.py::test_a", "t.py::test_ab"]
    assert mapped["ob-2"].test_evidence == ["t.py::test_ab"]


def test_apply_test_mapping_does_not_mutate_the_inputs():
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_a")]
    response = {
        "mappings": [{"test_id": "t.py::test_a", "obligation_ids": ["ob-1"], "rationale": "."}]
    }
    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    apply_test_mapping(obligations, result)

    assert obligations[0].test_evidence == []  # original untouched


# --- acceptance: mapping-accuracy metric vs archetype #1 labels ---


def test_archetype_1_mapping_accuracy_reports_a_real_number(tmp_path):
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    repo = Path(case.inputs.repo)
    change_set = extract_change_set(repo, case.inputs.base_revision, case.inputs.head_revision)

    discovered = discover_tests(repo, change_set)
    test_ids = {t.test_id for t in discovered.tests}
    pos = "test_receipt.py::test_positive_line"
    two = "test_receipt.py::test_two_decimal_formatting"
    assert {pos, two} <= test_ids  # both real tests are discovered

    # Reviewer obligations mirror ground truth (description is the scoring join
    # key today; ids reused so the injected mapping can target them).
    obligations = [
        Obligation(
            id=o.id,
            description=o.description,
            type=ObligationType.FUNCTIONAL,
            importance="critical",
            explicit=True,
            observable_behavior="...",
        )
        for o in case.ground_truth.obligations
    ]

    # Map both tests to show-fields and line-total, but NOT money-format:
    # 4 of the 6 ground-truth (obligation, test) pairs -> mapping recall 4/6.
    response = {
        "mappings": [
            {"test_id": pos, "obligation_ids": ["show-fields", "line-total"], "rationale": "."},
            {"test_id": two, "obligation_ids": ["show-fields", "line-total"], "rationale": "."},
        ]
    }
    result = map_tests_to_obligations(obligations, discovered.tests, client_returning(response))
    mapped = apply_test_mapping(obligations, result)

    review = Review(
        mode="local", reviewed_revision=case.inputs.head_revision, obligation_map=mapped
    )
    scored = score_case(case.model_copy(update={"reviewer_output": review}))

    assert scored.mapping_accuracy == 4 / 6


def test_archetype_1_unmapped_obligations_are_flagged(tmp_path):
    """The other half of the acceptance: an obligation with no mapped test is
    flagged unmapped. returns-in-parens (ground truth: no candidate tests) has
    nothing evidencing it, so a faithful mapping leaves it unmapped."""
    case = build_benchmark_case(ARCHETYPES_DIR / "01-missed-obligation", tmp_path / "repo")
    repo = Path(case.inputs.repo)
    change_set = extract_change_set(repo, case.inputs.base_revision, case.inputs.head_revision)
    discovered = discover_tests(repo, change_set)

    obligations = [
        Obligation(
            id=o.id,
            description=o.description,
            type=ObligationType.FUNCTIONAL,
            importance="critical",
            explicit=True,
            observable_behavior="...",
        )
        for o in case.ground_truth.obligations
    ]
    pos = "test_receipt.py::test_positive_line"
    two = "test_receipt.py::test_two_decimal_formatting"
    response = {
        "mappings": [
            {
                "test_id": pos,
                "obligation_ids": ["show-fields", "line-total", "money-format"],
                "rationale": ".",
            },
            {
                "test_id": two,
                "obligation_ids": ["show-fields", "line-total", "money-format"],
                "rationale": ".",
            },
        ]
    }
    result = map_tests_to_obligations(obligations, discovered.tests, client_returning(response))

    assert "returns-in-parens" in result.unmapped_obligation_ids
