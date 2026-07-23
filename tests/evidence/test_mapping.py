"""M4.2 acceptance: each obligation is either mapped to a candidate test or
flagged unmapped, and the §11.1 mapping-accuracy metric reports a real number
against archetype labels.

Mapping is a schema-constrained model call; per the replay-first invariant
these tests inject the recorded response via completion_fn — no live calls.
A client that raises proves the no-candidate-tests path takes no model call.
"""

import tempfile
from pathlib import Path

from acceptance.benchmark.fixtures import build_benchmark_case
from acceptance.benchmark.scoring import score_case
from acceptance.change.diff import extract_change_set
from acceptance.evidence.discovery import DiscoveredTest, DiscoveryReason, discover_tests
from acceptance.evidence.mapping import apply_test_mapping, map_tests_to_obligations
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import Obligation, ObligationType, Review
from tests.support import client_returning, make_obligation

ARCHETYPES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _test(test_id: str, source: str = "def t():\n    pass") -> DiscoveredTest:
    return DiscoveredTest(
        test_id=test_id, file=test_id.split("::", 1)[0],
        reasons=[DiscoveryReason.CALLS_CHANGED_SYMBOL], source=source,
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
    response = {"mappings": [
        {"test_id": "test_cart.py::test_discount", "obligation_ids": ["ob-1"], "rationale": "asserts total"},
    ]}

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
    response = {"mappings": [
        {"test_id": "t.py::test_both", "obligation_ids": ["ob-1", "ob-2"], "rationale": "both"},
    ]}

    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    assert result.mappings[0].obligation_ids == ["ob-1", "ob-2"]
    assert result.unmapped_obligation_ids == []


def test_a_test_evidencing_nothing_leaves_obligations_unmapped():
    # Discovery is recall-forward; mapping is the precision filter. A test that
    # touches changed code but asserts nothing about an obligation maps to none.
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_incidental")]
    response = {"mappings": [
        {"test_id": "t.py::test_incidental", "obligation_ids": [], "rationale": "setup only"},
    ]}

    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    assert result.mappings[0].obligation_ids == []
    assert result.unmapped_obligation_ids == ["ob-1"]


def test_unknown_ids_are_dropped():
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_real")]
    response = {"mappings": [
        {"test_id": "t.py::test_ghost", "obligation_ids": ["ob-1"], "rationale": "not a real test"},
        {"test_id": "t.py::test_real", "obligation_ids": ["ob-nope", "ob-1"], "rationale": "one bad id"},
    ]}

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


# --- unit: apply_test_mapping ---


def test_apply_test_mapping_populates_test_evidence():
    obligations = [
        make_obligation("ob-1", "A", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "B", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_a"), _test("t.py::test_ab")]
    response = {"mappings": [
        {"test_id": "t.py::test_a", "obligation_ids": ["ob-1"], "rationale": "."},
        {"test_id": "t.py::test_ab", "obligation_ids": ["ob-1", "ob-2"], "rationale": "."},
    ]}
    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    mapped = {o.id: o for o in apply_test_mapping(obligations, result)}

    assert mapped["ob-1"].test_evidence == ["t.py::test_a", "t.py::test_ab"]
    assert mapped["ob-2"].test_evidence == ["t.py::test_ab"]


def test_apply_test_mapping_does_not_mutate_the_inputs():
    obligations = [make_obligation("ob-1", "A", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_a")]
    response = {"mappings": [{"test_id": "t.py::test_a", "obligation_ids": ["ob-1"], "rationale": "."}]}
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
            id=o.id, description=o.description, type=ObligationType.FUNCTIONAL,
            importance="critical", explicit=True, observable_behavior="...",
        )
        for o in case.ground_truth.obligations
    ]

    # Map both tests to show-fields and line-total, but NOT money-format:
    # 4 of the 6 ground-truth (obligation, test) pairs -> mapping recall 4/6.
    response = {"mappings": [
        {"test_id": pos, "obligation_ids": ["show-fields", "line-total"], "rationale": "."},
        {"test_id": two, "obligation_ids": ["show-fields", "line-total"], "rationale": "."},
    ]}
    result = map_tests_to_obligations(obligations, discovered.tests, client_returning(response))
    mapped = apply_test_mapping(obligations, result)

    review = Review(mode="local", reviewed_revision=case.inputs.head_revision, obligation_map=mapped)
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
            id=o.id, description=o.description, type=ObligationType.FUNCTIONAL,
            importance="critical", explicit=True, observable_behavior="...",
        )
        for o in case.ground_truth.obligations
    ]
    pos = "test_receipt.py::test_positive_line"
    two = "test_receipt.py::test_two_decimal_formatting"
    response = {"mappings": [
        {"test_id": pos, "obligation_ids": ["show-fields", "line-total", "money-format"], "rationale": "."},
        {"test_id": two, "obligation_ids": ["show-fields", "line-total", "money-format"], "rationale": "."},
    ]}
    result = map_tests_to_obligations(obligations, discovered.tests, client_returning(response))

    assert "returns-in-parens" in result.unmapped_obligation_ids
