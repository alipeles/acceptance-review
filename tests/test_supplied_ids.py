"""Holding a model to the ids it was given (#163).

The defect these cover, observed in a real run: the mapping call returned 96
entries naming obligations that belonged to a fixture pasted into its own
prompt, and the foreign ids were filtered out silently — leaving a result
indistinguishable from "no test evidences any obligation". The review told the
reader their change was untested when the reviewer had answered a different
question.

Two guarantees, tested separately because they fail separately: the ids are in
the SCHEMA (so a foreign id is unrepresentable), and an id we still cannot
honour is RECORDED rather than dropped.
"""

import json

from acceptance.evidence.discovery import DiscoveredTest, DiscoveryReason
from acceptance.evidence.mapping import map_tests_to_obligations
from acceptance.llm import StrictResponseModel, inline_schema_refs
from acceptance.review_state import ObligationType
from acceptance.supplied_ids import UnusableAnswerLog, constrain, scan, unsupplied
from tests.support import client_capturing_schemas, client_returning, make_obligation


class _Item(StrictResponseModel):
    obligation_id: str
    obligation_ids: list[str]
    rationale: str


class _Container(StrictResponseModel):
    items: list[_Item]


def _test(test_id: str, source: str = "def t():\n    pass") -> DiscoveredTest:
    return DiscoveredTest(
        test_id=test_id,
        file=test_id.split("::", 1)[0],
        reasons=[DiscoveryReason.CALLS_CHANGED_SYMBOL],
        source=source,
    )


# --- the schema constraint (prevention) ---


def test_supplied_ids_become_an_enum_on_the_field_the_model_sees():
    """The whole point: the constraint lives in the schema, not the prose.

    Asserted on the INLINED schema because that is what actually reaches the
    provider — #158 established that enum values behind a `$ref` measurably
    change the answer, so a constraint the model only sees one indirection away
    is not a constraint.
    """
    constrained = constrain(_Container, {"obligation_id": ["ob-1", "ob-2"]})
    schema = inline_schema_refs(constrained.model_json_schema())

    field = schema["properties"]["items"]["items"]["properties"]["obligation_id"]
    assert field["enum"] == ["ob-1", "ob-2"]
    assert "$defs" not in json.dumps(schema)


def test_a_list_valued_id_field_constrains_its_items():
    constrained = constrain(_Container, {"obligation_ids": ["ob-1"]})
    schema = inline_schema_refs(constrained.model_json_schema())

    field = schema["properties"]["items"]["items"]["properties"]["obligation_ids"]
    assert field["items"]["enum"] == ["ob-1"]


def test_a_foreign_id_does_not_validate_against_the_constrained_schema():
    constrained = constrain(_Container, {"obligation_id": ["ob-1"]})

    ok = constrained.model_validate_json(
        '{"items":[{"obligation_id":"ob-1","obligation_ids":[],"rationale":"r"}]}'
    )
    assert ok.items[0].obligation_id == "ob-1"

    try:
        constrained.model_validate_json(
            '{"items":[{"obligation_id":"show-fields","obligation_ids":[],"rationale":"r"}]}'
        )
    except Exception as exc:
        assert "show-fields" in str(exc)
    else:
        raise AssertionError("a foreign id validated against the constrained schema")


def test_the_schema_name_is_preserved_so_the_request_key_stays_meaningful():
    """`__name__` is the schema name in the hashed request and the key the test
    doubles dispatch on. A generated name would make every recorded transcript
    unreachable and every dispatching double miss."""
    assert constrain(_Container, {"obligation_id": ["ob-1"]}).__name__ == "_Container"


def test_an_empty_supplied_set_leaves_the_field_unconstrained():
    """`Literal[]` is not a type, and a call that supplied nothing has nothing to
    enforce. The guarantee degrades to local detection rather than raising."""
    assert constrain(_Container, {"obligation_id": []}) is _Container


# --- the local check (detection) ---


def test_scan_finds_ids_that_were_never_supplied():
    response = _Container(
        items=[
            _Item(obligation_id="ob-1", obligation_ids=["ob-1", "show-fields"], rationale="r"),
        ]
    )

    found = scan(response, {"obligation_id": ["ob-1"], "obligation_ids": ["ob-1"]}, "mapping")

    assert [(a.field, a.returned_id) for a in found] == [("obligation_ids", "show-fields")]
    assert found[0].stage == "mapping"


def test_scan_reports_each_unusable_id_once():
    """It reaches the report, and two recorded runs over the same input must be
    byte-identical (M0.5) — so no duplicates and a stable order."""
    response = _Container(
        items=[
            _Item(obligation_id="x", obligation_ids=["y"], rationale="r"),
            _Item(obligation_id="x", obligation_ids=["y"], rationale="r"),
        ]
    )

    found = scan(response, {"obligation_id": ["ob-1"], "obligation_ids": ["ob-1"]}, "s")

    assert [(a.field, a.returned_id) for a in found] == [
        ("obligation_id", "x"),
        ("obligation_ids", "y"),
    ]


def test_unsupplied_preserves_first_seen_order_without_duplicates():
    assert unsupplied(["a", "b", "a", "c"], {"b"}) == ["a", "c"]


# --- the mapping stage, where the defect was observed ---


def test_a_foreign_obligation_id_is_recorded_not_silently_dropped():
    """The original defect. `show-fields` belongs to a fixture the prompt
    happened to contain; before #163 it was filtered at mapping.py and the
    result read as 'no test evidences this'."""
    obligations = [make_obligation("ob-1", "Discount reduces total", ObligationType.FUNCTIONAL)]
    tests = [_test("test_cart.py::test_discount")]
    response = {
        "mappings": [
            {
                "test_id": "test_cart.py::test_discount",
                "obligation_ids": ["show-fields"],
                "rationale": "asserts total",
            }
        ]
    }
    log = UnusableAnswerLog()

    result = map_tests_to_obligations(
        obligations, tests, client_returning(response), unusable=log
    )

    assert [a.returned_id for a in log.answers] == ["show-fields"]
    assert result.unusable_answers[0].returned_id == "show-fields"


def test_an_obligation_is_indeterminate_not_unmapped_when_an_answer_was_unusable():
    """The distinction the whole task turns on. 'No test evidences this' is a
    substantive claim; we are not entitled to it when the answer that would have
    mapped the obligation is the one we could not read."""
    obligations = [make_obligation("ob-1", "Discount reduces total", ObligationType.FUNCTIONAL)]
    tests = [_test("test_cart.py::test_discount")]
    response = {
        "mappings": [
            {
                "test_id": "test_cart.py::test_discount",
                "obligation_ids": ["show-fields"],
                "rationale": "r",
            }
        ]
    }
    log = UnusableAnswerLog()

    result = map_tests_to_obligations(
        obligations, tests, client_returning(response), unusable=log
    )

    assert result.indeterminate_obligation_ids == ["ob-1"]
    assert result.unmapped_obligation_ids == []  # NOT a negative answer
    assert log.indeterminate_obligations == {"ob-1"}


def test_a_usable_judgment_survives_an_unusable_one_in_the_same_response():
    """Per-item, not per-response. Parsing strictly would abort the batch and
    discard every judgment that came back alongside the bad id."""
    obligations = [
        make_obligation("ob-1", "Discount reduces total", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "Total is money-formatted", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_a"), _test("t.py::test_b")]
    response = {
        "mappings": [
            {"test_id": "t.py::test_a", "obligation_ids": ["ob-1"], "rationale": "good"},
            {"test_id": "t.py::test_b", "obligation_ids": ["show-fields"], "rationale": "bad"},
        ]
    }
    log = UnusableAnswerLog()

    result = map_tests_to_obligations(
        obligations, tests, client_returning(response), unusable=log
    )

    good = next(m for m in result.mappings if m.test_id == "t.py::test_a")
    assert good.obligation_ids == ["ob-1"]  # retained
    assert [a.returned_id for a in log.answers] == ["show-fields"]


def test_a_clean_mapping_records_nothing_and_keeps_its_negative_answers():
    """The guarantee must not fire spuriously: with every id honoured, an
    unmapped obligation is still a real, reportable negative answer."""
    obligations = [
        make_obligation("ob-1", "Discount reduces total", ObligationType.FUNCTIONAL),
        make_obligation("ob-2", "Total is money-formatted", ObligationType.FUNCTIONAL),
    ]
    tests = [_test("t.py::test_a")]
    response = {
        "mappings": [{"test_id": "t.py::test_a", "obligation_ids": ["ob-1"], "rationale": "r"}]
    }
    log = UnusableAnswerLog()

    result = map_tests_to_obligations(
        obligations, tests, client_returning(response), unusable=log
    )

    assert result.unmapped_obligation_ids == ["ob-2"]
    assert result.indeterminate_obligation_ids == []
    assert not log.answers


def test_each_partition_constrains_test_ids_to_its_own_batch():
    """A partitioned stage constrains each call to its own partition — every
    obligation (each batch judges all of them), but only that batch's tests."""
    obligations = [make_obligation("ob-1", "Discount reduces total", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_a"), _test("t.py::test_b")]
    client, seen = client_capturing_schemas({"mappings": []})

    map_tests_to_obligations(obligations, tests, client, batch_size=1)

    assert len(seen) == 2
    enums = [s["properties"]["mappings"]["items"]["properties"]["test_id"]["enum"] for s in seen]
    assert enums == [["t.py::test_a"], ["t.py::test_b"]]
    # Every batch still judges every obligation.
    for schema in seen:
        obligation_field = schema["properties"]["mappings"]["items"]["properties"][
            "obligation_ids"
        ]
        assert obligation_field["items"]["enum"] == ["ob-1"]


def test_the_schema_asked_for_differs_from_the_shape_parsed():
    """The `parse_as` seam. Without it a provider that ignored the enum would
    raise `SchemaValidationError` and cost the whole batch — which is exactly the
    all-or-nothing failure the per-item recording exists to avoid."""
    obligations = [make_obligation("ob-1", "Discount reduces total", ObligationType.FUNCTIONAL)]
    tests = [_test("t.py::test_a")]
    response = {
        "mappings": [
            {"test_id": "t.py::test_a", "obligation_ids": ["not-supplied"], "rationale": "r"}
        ]
    }

    # Does not raise: parsed permissively, then checked per item.
    result = map_tests_to_obligations(obligations, tests, client_returning(response))

    assert result.unusable_answers[0].returned_id == "not-supplied"


# --- the pipeline actually uses it (the wiring, not just the helper) ---


_TASK = "# Task\n\n- Alpha behaves\n"

_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "alpha",
                "description": "Alpha behaves",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "alpha() == 1",
                "source_quote": "Alpha behaves",
            }
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    },
    # The defect, reproduced: a mapping naming an obligation nobody supplied.
    "_Mappings": {
        "mappings": [
            {
                "test_id": "test_alpha.py::test_alpha",
                "obligation_ids": ["show-fields"],
                "rationale": "from a fixture in the prompt",
            }
        ]
    },
    "_Discrimination": {"obligations": []},
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "alpha",
                "status": "addressed",
                "rationale": "alpha.py implements it.",
                "diff_refs": [],
            }
        ]
    },
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def _repo_with_a_change(tmp_path):
    import subprocess

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "alpha.py").write_text("def alpha():\n    return 0\n")
    (tmp_path / "test_alpha.py").write_text(
        "from alpha import alpha\n\n\ndef test_alpha():\n    assert alpha() is not None\n"
    )
    git("add", "-A")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "alpha.py").write_text("def alpha():\n    return 1\n")
    git("add", "-A")
    git("commit", "-qm", "head")
    return base, git("rev-parse", "HEAD")


def _review(tmp_path):
    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review
    from tests.support import client_dispatching

    base, head = _repo_with_a_change(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching(_JUDGMENTS),
        reviewed_revision=head,
    )


def test_the_pipeline_reports_an_unusable_answer_naming_the_stage_and_the_id(tmp_path):
    """Wiring, not the helper. Defect injection has repeatedly found a
    well-tested helper the pipeline never calls — so assert the review itself
    carries the finding, with enough detail to tell WHICH judgment is missing."""
    review = _review(tmp_path)

    unusable = [f for f in review.findings if f.type == "unusable_answer"]
    assert len(unusable) == 1
    assert "show-fields" in unusable[0].description
    assert "mapping" in unusable[0].description


def test_an_unusable_answer_leaves_the_obligation_indeterminate(tmp_path):
    """Not `unsupported`. The model never answered about `alpha`, so claiming
    its tests are weak asserts something we did not establish."""
    review = _review(tmp_path)

    alpha = next(o for o in review.obligation_map if o.id == "alpha")
    assert alpha.evidence_class == "indeterminate"


def test_a_review_holding_an_unusable_answer_does_not_come_back_clean(tmp_path):
    """The point of gating the verdict: a half-blind review and a clean one look
    identical unless the uncertainty is carried all the way to the headline."""
    review = _review(tmp_path)

    assert review.completion is not None
    assert review.completion.verdict.value != "no_material_gaps"
    assert "alpha" in review.completion.escalation_candidates


def test_a_single_supplied_id_is_still_sent_as_an_enum():
    """Pydantic renders a one-value `Literal` as `const`. Providers honour
    `enum` under strict decoding, so without normalising, a call supplying
    exactly one id — a one-obligation task, or a final partition — would be the
    one case where the constraint silently stopped binding."""
    from acceptance.llm import inline_schema_refs

    schema = inline_schema_refs(constrain(_Container, {"obligation_id": ["only"]}).model_json_schema())

    field = schema["properties"]["items"]["items"]["properties"]["obligation_id"]
    assert field["enum"] == ["only"]
    assert "const" not in field
