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
from typing import Literal

import pytest
from pydantic import ValidationError

from acceptance.evidence.discovery import DiscoveredTest, DiscoveryReason
from acceptance.llm import StrictResponseModel, inline_schema_refs
from acceptance.supplied_ids import constrain, scan, unsupplied


class _Item(StrictResponseModel):
    obligation_id: str
    obligation_ids: list[str]
    rationale: str


class _Container(StrictResponseModel):
    items: list[_Item]


class _FirstShape(StrictResponseModel):
    kind: Literal["first"]
    obligation_id: str
    rationale: str


class _SecondShape(StrictResponseModel):
    kind: Literal["second"]
    obligation_id: str
    note: str


class _UnionContainer(StrictResponseModel):
    items: list[_FirstShape | _SecondShape]


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


def test_a_union_of_item_shapes_constrains_every_member():
    """The walk must descend through a union, not stop at it.

    `_Decomposition` returns a union of per-disposition shapes (M1.2.r2), and
    every member carries the same `requirement_id`. Before this, the walk found
    no `BaseModel` to descend into, returned None, and the constraint vanished
    with nothing failing — the guarantee would have been silently gone while
    every existing test still passed, which is the shape of defect the walk
    exists to prevent.
    """
    constrained = constrain(_UnionContainer, {"obligation_id": ["ob-1", "ob-2"]})
    schema = inline_schema_refs(constrained.model_json_schema())

    members = schema["properties"]["items"]["items"]["anyOf"]
    assert len(members) == 2
    for member in members:
        assert member["properties"]["obligation_id"]["enum"] == ["ob-1", "ob-2"]

    # And it still refuses an id outside the supplied set, through the union.
    with pytest.raises(ValidationError):
        constrained.model_validate(
            {"items": [{"kind": "first", "obligation_id": "ob-9", "rationale": "."}]}
        )


def test_a_foreign_id_does_not_validate_against_the_constrained_schema():
    constrained = constrain(_Container, {"obligation_id": ["ob-1"]})

    ok = constrained.model_validate_json(
        '{"items":[{"obligation_id":"ob-1","obligation_ids":[],"rationale":"r"}]}'
    )
    assert ok.items[0].obligation_id == "ob-1"

    # ValidationError specifically: catching bare Exception here would also pass
    # on a typo in the schema name or a JSON syntax error, neither of which is
    # the rejection this test claims to demonstrate.
    with pytest.raises(ValidationError) as rejection:
        constrained.model_validate_json(
            '{"items":[{"obligation_id":"show-fields","obligation_ids":[],"rationale":"r"}]}'
        )

    assert "show-fields" in str(rejection.value)


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


# --- the pair stage no longer echoes ids ---
#
# Three tests used to sit here, exercising this machinery at the batched
# (defect, test) judge: a foreign defect id recorded rather than dropped, a
# clean answer recording nothing, and the asked-for schema differing from the
# parsed one. #385 replaced that judge with Jev and then a yes/no model call
# about ONE pair, whose answer names no id at all, so there is nothing at that
# stage for the guarantee to hold over. They were deleted, not rewritten into a
# passing shape. The wiring tests below reproduce an unobtained judgement at
# the new pair stage instead.


# --- the pipeline actually uses it (the wiring, not just the helper) ---


_TASK = "# Task\nAlpha behaves.\n\n## Constraints\n- Alpha behaves\n"

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
    "_Enumeration": {
        "obligation_id": "",
        "defects": [
            {
                "slug": "d1",
                "expected_behavior": "the code behaves as the criterion requires",
                "defective_behavior": "the code behaves as this defect describes",
                "type": "other",
                "description": "alpha returns a constant",
                "code_refs": [],
            }
        ],
        "reason": "",
    },
    # The defect, reproduced at the stage that inherits it. It was reproduced
    # through the test-to-criterion mapping stage until #316 deleted it, then as
    # a foreign defect id in the batched pair judge until #385 replaced that
    # with Jev and a yes/no model call that names no id. Jev is unsure about the
    # one pair (see `_review`), so the model is asked, and its answer carries no
    # yes or no: a judgement asked for and not obtained, which is the shape the
    # foreign id stood for.
    "_Fails": {},
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
    from tests.support import FakeJev, client_dispatching

    base, head = _repo_with_a_change(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching(_JUDGMENTS),
        reviewed_revision=head,
        # Between the cut-offs, so the model is asked about the pair.
        jev=FakeJev(lambda defect, test_name: 0.3),
    )


def test_the_pipeline_reports_an_unusable_answer_naming_the_stage_and_the_id(tmp_path):
    """Wiring, not the helper. Defect injection has repeatedly found a
    well-tested helper the pipeline never calls — so assert the review itself
    carries the finding, with enough detail to tell WHICH judgment is missing."""
    review = _review(tmp_path)

    unusable = [f for f in review.findings if f.type == "unusable_answer"]
    assert len(unusable) == 1
    assert "alpha/d1/test_alpha.py::test_alpha" in unusable[0].description
    assert "defect-to-test pair mapping" in unusable[0].description


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

    schema = inline_schema_refs(
        constrain(_Container, {"obligation_id": ["only"]}).model_json_schema()
    )

    field = schema["properties"]["items"]["items"]["properties"]["obligation_id"]
    assert field["enum"] == ["only"]
    assert "const" not in field
