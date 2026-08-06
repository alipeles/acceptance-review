"""M1.2.r1 acceptance: decomposition returns a requirement -> obligation mapping.

The defect these pin is *absence*. A flat obligation list made a response
covering 20 of 29 requirements exactly as well-formed as one covering all 29, so
nothing downstream could notice; #195's Gate 1 lost 4 of 15 Completion
expectations and 5 of 8 Scope exclusions and the review reported no gap
(DR-202).

The assertions therefore concentrate on what happens when the model says LESS
than it was asked for, because that is the case the old shape could not
represent. A test that only checks a complete response would pass against the
old code too.

Responses are injected via the harness's completion_fn per the replay-first
invariant — no live calls.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from acceptance.llm import SchemaValidationError, inline_schema_refs
from acceptance.requirement.obligations import _Decomposition, _user_prompt, decompose
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import Disposition, RequirementSection
from tests.support import client_returning as _client_returning

# Three requirements in three sections, deliberately: the section a requirement
# sits in is part of its id, and a single-section file could not catch a scheme
# that ignored the section.
TASK = """# Task
Render each invoice line.

## Constraints
- Format money as USD with two decimals.
- Keep the existing CSV export unchanged.

## Scope exclusions
- Changing the PDF renderer.

## Completion expectations
- Money is formatted as USD with two decimals.
"""


def _obligation(oid: str, description: str, quote: str) -> dict:
    return {
        "id": oid,
        "description": description,
        "type": "functional",
        "importance": "normal",
        "explicit": True,
        "observable_behavior": "...",
        "source_quote": quote,
    }


def _disposition(rid: str, disposition: str, **kwargs) -> dict:
    """Build one disposition in the shape the response schema now defines.

    Each shape carries only its own payload (M1.2.r2), so this cannot express a
    `yielded` disposition with no obligations — which is the point, and why the
    tests that used to construct that case now assert on the raw dict instead.
    """
    if disposition == "yielded":
        ids = kwargs["obligation_ids"]
        return {
            "requirement_id": rid,
            "disposition": "yielded",
            "obligation_id": ids[0],
            "more_obligation_ids": list(ids[1:]),
        }
    if disposition == "open_question":
        ids = kwargs["open_question_ids"]
        return {
            "requirement_id": rid,
            "disposition": "open_question",
            "open_question_id": ids[0],
            "more_open_question_ids": list(ids[1:]),
        }
    return {
        "requirement_id": rid,
        "disposition": "no_obligation",
        "reason": kwargs["reason"],
    }


# --- the registry -----------------------------------------------------------


def test_every_requirement_in_the_file_is_identified():
    registry = build_registry(parse_task_file(TASK))

    assert [r.id for r in registry] == [
        "task-01",
        "constraint-01",
        "constraint-02",
        "exclusion-01",
        "completion-01",
    ]
    assert registry[1].section is RequirementSection.CONSTRAINT
    assert registry[3].section is RequirementSection.EXCLUSION


def test_requirement_ids_are_identical_across_two_runs_over_identical_text():
    """The acceptance criterion, and the whole of what the interim scheme
    promises. Cross-VERSION stability is semantic and is #209."""
    first = build_registry(parse_task_file(TASK))
    second = build_registry(parse_task_file(TASK))

    assert [r.id for r in first] == [r.id for r in second]
    assert [r.span for r in first] == [r.span for r in second]


def test_each_registry_entry_carries_the_span_of_its_requirement():
    parsed = parse_task_file(TASK)

    for requirement in build_registry(parsed):
        span = requirement.span
        assert parsed.source[span.start : span.end] == span.text


# --- the mapping ------------------------------------------------------------


def test_a_fully_accounted_response_disposes_every_requirement():
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd-format", "Format money as USD.", "Format money as USD"),
            _obligation("csv-unchanged", "Keep the CSV export unchanged.", "existing CSV export"),
            _obligation("pdf-untouched", "Preserve the PDF renderer.", "Changing the PDF renderer"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["usd-format"]),
            _disposition("constraint-02", "yielded", obligation_ids=["csv-unchanged"]),
            _disposition("exclusion-01", "yielded", obligation_ids=["pdf-untouched"]),
            _disposition("completion-01", "yielded", obligation_ids=["usd-format"]),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    assert [entry.requirement_id for entry in result.requirement_map.dispositions] == [
        "task-01",
        "constraint-01",
        "constraint-02",
        "exclusion-01",
        "completion-01",
    ]
    assert result.requirement_map.unyielding() == []


def test_a_response_that_never_mentions_a_requirement_is_rejected():
    """The load-bearing case, and the one M1.2.r1 got wrong. The response is
    well-formed and internally consistent; it simply says nothing about two of
    the five requirements.

    M1.2.r1 recorded those two as a fourth disposition and carried on to a
    verdict. They are not a gap in the review — they mean there is no review,
    because the mandate was never read. The registry is derived from the parse
    and the reconciliation walks it, so the code cannot drop a requirement; only
    a malformed response can, and a malformed response is refused.
    """
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd-format", "Format money as USD.", "Format money as USD"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["usd-format"]),
            _disposition("completion-01", "yielded", obligation_ids=["usd-format"]),
        ],
    }

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, _client_returning(response))

    message = str(raised.value)
    assert "constraint-02" in message and "exclusion-01" in message
    assert "2 of 5" in message


def test_a_requirement_deliberately_yielding_nothing_carries_its_reason():
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason="A section marker, not a requirement."),
            _disposition("constraint-02", "no_obligation", reason="Restates constraint-01."),
            _disposition("exclusion-01", "no_obligation", reason="Out of scope by construction."),
            _disposition("completion-01", "no_obligation", reason="Duplicate of constraint-01."),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    declined = result.requirement_map.disposition_for("constraint-01")
    assert declined.disposition is Disposition.NO_OBLIGATION
    assert declined.reason == "A section marker, not a requirement."
    assert len(result.requirement_map.unyielding()) == 4


def test_a_yielded_claim_naming_no_real_obligation_is_rejected():
    """A disposition may not launder a requirement into 'handled' by naming an
    obligation the same response never produced.

    The shape guarantees at least one id is NAMED; it cannot guarantee the id
    refers to something. So the one hole the schema leaves — every named id
    dropped as invented — closes here, and closes by raising rather than by
    recording a requirement as unaddressed.
    """
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["never-emitted"]),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, _client_returning(response))

    assert "constraint-01" in str(raised.value)


def test_the_schema_cannot_express_a_yielded_disposition_with_no_obligations():
    """The guarantee is structural, not a validation rule applied afterwards.

    `yielded` requires `obligation_id`, so the empty case has no encoding — in
    the schema sent to the model as much as in the parse. A minimum on a list
    would not do: OpenAI strict mode rejects `minItems`, so it would either be
    stripped from the wire schema or make the call fail.
    """
    with pytest.raises(ValidationError):
        _Decomposition.model_validate(
            {
                "obligations": [],
                "open_questions": [],
                "requirement_dispositions": [
                    {
                        "requirement_id": "task-01",
                        "disposition": "yielded",
                        "more_obligation_ids": [],
                    }
                ],
            }
        )

    # The schema as it actually goes out, refs inlined the way `complete` sends
    # it — the wire form is what constrains the model, not the pydantic form.
    schema = inline_schema_refs(_Decomposition.model_json_schema())
    members = schema["properties"]["requirement_dispositions"]["items"]["anyOf"]
    yielded = next(
        member for member in members if "obligation_id" in member.get("properties", {})
    )
    assert "obligation_id" in yielded["required"]
    # Strict mode rejects both, and a tagged union would emit them.
    assert "oneOf" not in schema["properties"]["requirement_dispositions"]["items"]
    assert "discriminator" not in schema["properties"]["requirement_dispositions"]["items"]


def test_the_literal_tag_alone_decides_which_shape_a_disposition_is():
    """The union is plain, so the `disposition` literal is the only thing that
    picks a member. Two entries sharing every other field must still land on
    different shapes, or a `no_obligation` could be read as a `yielded` whose
    ids happened to be absent — the contradiction rebuilt inside the parser.
    """
    parsed = _Decomposition.model_validate(
        {
            "obligations": [],
            "open_questions": [],
            "requirement_dispositions": [
                {
                    "requirement_id": "task-01",
                    "disposition": "yielded",
                    "obligation_id": "ob-1",
                    "more_obligation_ids": [],
                },
                {
                    "requirement_id": "constraint-01",
                    "disposition": "no_obligation",
                    "reason": "Declined.",
                },
            ],
        }
    )

    first, second = parsed.requirement_dispositions
    assert type(first).__name__ != type(second).__name__
    assert first.ids() == ["ob-1"]
    assert second.reason == "Declined."

    # An unknown tag matches no member at all, rather than falling back to one.
    with pytest.raises(ValidationError):
        _Decomposition.model_validate(
            {
                "obligations": [],
                "open_questions": [],
                "requirement_dispositions": [
                    {"requirement_id": "task-01", "disposition": "undisposed", "reason": "x"}
                ],
            }
        )


def test_a_disposition_cannot_carry_another_disposition_s_payload():
    """Exclusivity is what stops the contradiction returning in a new costume.

    A `yielded` entry that also carries `reason` is a response claiming both
    dispositions at once — M1.2.r1's defect wearing different clothes. If it
    parsed, it would bind to `_Yielded`, which has no `reason` field, so the
    reason would be dropped on the floor exactly as it was before.

    It rejects today only because `StrictResponseModel` sets `extra="forbid"`,
    and that exists for an unrelated reason: OpenAI strict mode requires every
    object in the schema to forbid extra properties. Nothing else records that
    this union depends on it, so relaxing `extra` elsewhere would reopen the gap
    with every other test still green. Hence this guard.
    """
    def parse(entry: dict):
        return _Decomposition.model_validate(
            {"obligations": [], "open_questions": [], "requirement_dispositions": [entry]}
        )

    # Claims `yielded` and supplies a decline reason alongside it.
    with pytest.raises(ValidationError):
        parse(
            {
                "requirement_id": "task-01",
                "disposition": "yielded",
                "obligation_id": "ob-1",
                "more_obligation_ids": [],
                "reason": "declined because it adds no checkable behavior",
            }
        )

    # The mirror: were members selected by which fields are present rather than
    # by the literal tag, this would match `_Yielded` and turn a decline into a
    # yield.
    with pytest.raises(ValidationError):
        parse(
            {
                "requirement_id": "task-01",
                "disposition": "no_obligation",
                "reason": "Not applicable.",
                "obligation_id": "ob-1",
                "more_obligation_ids": [],
            }
        )

    # The control, so neither assertion above can pass vacuously.
    clean = parse(
        {
            "requirement_id": "task-01",
            "disposition": "yielded",
            "obligation_id": "ob-1",
            "more_obligation_ids": [],
        }
    )
    assert clean.requirement_dispositions[0].ids() == ["ob-1"]


def test_the_schema_cannot_express_an_open_question_disposition_with_no_questions():
    """The twin of the yielded case, at the schema boundary rather than at
    reconciliation: `open_question_id` is required, so the empty payload has no
    encoding to send."""
    with pytest.raises(ValidationError):
        _Decomposition.model_validate(
            {
                "obligations": [],
                "open_questions": [],
                "requirement_dispositions": [
                    {
                        "requirement_id": "task-01",
                        "disposition": "open_question",
                        "more_open_question_ids": [],
                    }
                ],
            }
        )

    schema = inline_schema_refs(_Decomposition.model_json_schema())
    members = schema["properties"]["requirement_dispositions"]["items"]["anyOf"]
    questioned = next(
        member for member in members if "open_question_id" in member.get("properties", {})
    )
    assert "open_question_id" in questioned["required"]


def test_a_no_obligation_disposition_with_an_empty_reason_is_rejected():
    """`no_obligation` carries nothing BUT the reason, so an empty one is a
    requirement declined without saying why — the state whose reason M1.2.r1
    discarded and replaced with a diagnostic of its own."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason=""),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    with pytest.raises((SchemaValidationError, ValidationError, ValueError)):
        decompose(parsed, _client_returning(response))


def test_the_disposition_set_is_exactly_the_three_of_decision_3():
    """No fourth value, and no path that could assign one.

    Asserted on the enum rather than on behaviour because that is the whole
    claim: `UNDISPOSED` encoded a state no correct run produces, and leaving the
    value in place while removing its call sites would invite it back.
    """
    assert [d.value for d in Disposition] == ["yielded", "no_obligation", "open_question"]
    assert not hasattr(Disposition, "UNDISPOSED")

    # Executable references only. The docstrings that explain why the value is
    # gone are the record of a decision that cost a Gate 1 run to find, and a
    # text search would forbid exactly the prose worth keeping.
    source = Path(inspect.getfile(decompose)).parent.parent
    offenders: list[str] = []
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            named = (
                isinstance(node, ast.Attribute) and node.attr == "UNDISPOSED"
            ) or (isinstance(node, ast.Name) and node.id == "UNDISPOSED")
            if named:
                offenders.append(f"{path.relative_to(source).as_posix()}:{node.lineno}")
    assert offenders == [], f"the removed disposition is still referenced at {offenders}"


def test_an_open_question_disposition_naming_no_real_question_is_rejected():
    """The `yielded` hole has a twin on the open-question side, and closing one
    without the other leaves the same contradiction reachable by another name."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "open_question", open_question_ids=["never-asked"]),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, _client_returning(response))

    assert "constraint-01" in str(raised.value)


def test_a_response_naming_a_requirement_outside_the_registry_is_rejected():
    """Constrained decoding makes a foreign id unrepresentable, but the
    guarantee degrades when a provider ignores the constraint (#163), so the
    local check has to exist and has to raise rather than drop."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason="Not applicable."),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
            _disposition("constraint-99", "no_obligation", reason="No such requirement."),
        ],
    }

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, _client_returning(response))

    assert "constraint-99" in str(raised.value)


def test_a_requirement_disposed_twice_is_rejected():
    """Two dispositions for one requirement is a response contradicting itself,
    and picking either one silently would be the reader's problem, not the
    model's."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("task-01", "no_obligation", reason="Also declined."),
            _disposition("constraint-01", "no_obligation", reason="Not applicable."),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, _client_returning(response))

    assert "more than once" in str(raised.value)


def test_a_supplied_reason_is_preserved_rather_than_replaced():
    """M1.2.r1 discarded the model's reason whenever it disagreed with the
    label, substituting a diagnostic string — so eight reasoned declines in
    #216's Gate 1 were reported as requirements nothing had been said about."""
    parsed = parse_task_file(TASK)
    reason = "A scope exclusion pointing at a separate issue; it adds no checkable behavior."
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason="Not applicable."),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason=reason),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    assert result.requirement_map.disposition_for("exclusion-01").reason == reason


def test_one_obligation_serves_two_requirements_rather_than_being_duplicated():
    """DR-202 decision 2. The same requirement stated under Constraints and
    under Completion expectations is ONE obligation with two links, which is
    what reframes #144 from 'are these obligations the same?' to 'does this
    requirement restate one already covered?'."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd-format", "Format money as USD.", "Format money as USD"),
            _obligation("csv-unchanged", "Keep the CSV export unchanged.", "existing CSV export"),
            _obligation("pdf-untouched", "Preserve the PDF renderer.", "Changing the PDF renderer"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["usd-format"]),
            _disposition("constraint-02", "yielded", obligation_ids=["csv-unchanged"]),
            _disposition("exclusion-01", "yielded", obligation_ids=["pdf-untouched"]),
            # The same obligation, not a second copy of it.
            _disposition("completion-01", "yielded", obligation_ids=["usd-format"]),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    assert result.requirement_map.requirements_for_obligation("usd-format") == [
        "constraint-01",
        "completion-01",
    ]
    # One obligation, not two near-identical ones.
    assert [o.id for o in result.obligations].count("usd-format") == 1
    assert len(result.obligations) == 4


def test_a_disposition_naming_a_renamed_obligation_still_links():
    """`_unique` renames a colliding id, and a disposition naming the original
    would otherwise dangle — silently converting a mapped requirement into an
    unmapped one, which is the defect wearing a different hat."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("dup", "First.", "Render each invoice line."),
            _obligation("dup", "Second.", "Format money as USD"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["dup"]),
            _disposition("constraint-01", "yielded", obligation_ids=["dup"]),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    assert [o.id for o in result.obligations] == ["dup", "dup-2"]
    assert result.requirement_map.disposition_for("task-01").obligation_ids == ["dup"]


# --- the decomposer stays code-blind (DR-202 decision 8) --------------------


def test_decompose_cannot_reach_a_diff_or_a_head_revision():
    """Pinned by signature rather than by behaviour, deliberately: the guarantee
    is that the information is not AVAILABLE to the stage, and a behavioural test
    could only show that one particular prompt did not use it.

    Decomposing the mandate in light of the delivered implementation makes a
    missing obligation and a missing implementation correlated errors, which
    destroys the one thing the review exists to detect.
    """
    parameters = inspect.signature(decompose).parameters

    assert list(parameters) == ["parsed", "client", "unusable_answers"]
    annotations = {name: str(p.annotation) for name, p in parameters.items()}
    forbidden = ("ChangeSet", "Path", "revision", "repo", "head")
    for name, annotation in annotations.items():
        assert not any(term.lower() in annotation.lower() for term in forbidden), (
            f"decompose's `{name}` parameter exposes change or repository context"
        )


def test_the_prompt_carries_identified_requirements_not_raw_markdown():
    """The CLAUDE.md structured-interchange invariant. `parse_task_file` has
    already computed the structure; pasting `parsed.source` back discards it and
    asks the model to re-derive what the code knows."""
    parsed = parse_task_file(TASK)
    prompt = _user_prompt(build_registry(parsed))

    assert "[constraint-01]" in prompt
    assert "[exclusion-01]" in prompt
    # The markdown scaffolding the parse consumed does not reappear.
    assert "## Constraints" not in prompt
    assert "## Scope exclusions" not in prompt


# --- the CLI renders the mapping as a mapping -------------------------------


def _decomposition_with_a_shared_and_a_declined_requirement():
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd-format", "Format money as USD.", "Format money as USD"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["usd-format"]),
            _disposition("constraint-02", "no_obligation", reason="Covered by the CSV suite."),
            _disposition("exclusion-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("completion-01", "yielded", obligation_ids=["usd-format"]),
        ],
    }
    return decompose(parsed, _client_returning(response))


def test_the_cli_lists_every_requirement_including_the_ones_yielding_nothing():
    from acceptance.cli import render_decomposition

    output = render_decomposition(_decomposition_with_a_shared_and_a_declined_requirement())

    for requirement_id in ("[task-01]", "[constraint-01]", "[constraint-02]", "[exclusion-01]"):
        assert requirement_id in output, f"{requirement_id} is missing from the rendered mapping"
    assert "no obligation, deliberately" in output
    assert "Covered by the CSV suite." in output
    assert "deliberately none: 1" in output


def test_the_cli_says_when_an_obligation_serves_other_requirements():
    """Without this the same obligation appearing under three requirements reads
    as three duplicates rather than as one obligation with three links, which is
    the distinction DR-202 decision 2 turns on."""
    from acceptance.cli import render_decomposition

    output = render_decomposition(_decomposition_with_a_shared_and_a_declined_requirement())

    assert "also serves exclusion-01" in output
    assert "also serves completion-01" in output
    # An obligation is never told it serves the requirement it is listed under.
    assert "also serves task-01, exclusion-01" not in output


def test_an_obligation_no_requirement_claims_is_still_shown():
    """An unmapped obligation is an invention or a mapping failure — both are
    findings. Dropping it would recreate the same invisibility on the other
    axis."""
    from acceptance.cli import render_decomposition

    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("orphan", "An obligation no requirement claims.", "Render each invoice line."),
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        # Every requirement is accounted for, and one obligation is still
        # claimed by none of them — the response must be complete for the
        # orphan to be the only thing under test.
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason="Not applicable."),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    output = render_decomposition(decompose(parsed, _client_returning(response)))

    assert "Obligations mapped to no requirement:" in output
    assert "orphan" in output


def test_the_header_counts_declines_without_claiming_a_check_it_no_longer_makes():
    """M1.2.r1's header carried `unaccounted for: N`, printed even at zero
    because zero was the assurance a reader wanted.

    The assurance is now structural — a response leaving a requirement
    unaccounted for does not parse — so the line would report a constant. A
    permanent zero reads as a check being performed and passing, which is
    exactly the false comfort #216 recorded when the guard printed it over
    three lost requirements.
    """
    from acceptance.cli import render_decomposition

    output = render_decomposition(_decomposition_with_a_shared_and_a_declined_requirement())

    assert "with obligations: 4" in output
    assert "deliberately none: 1" in output
    assert "unaccounted" not in output.lower()


# --- unread source reaches the reader (M1.2.r1) -----------------------------

TASK_WITH_AN_UNRECOGNISED_SECTION = """# Task
Render each invoice line.

## Background
Invoices are currently rendered by a legacy template nobody owns.

## Constraints
- Format money as USD.
"""


def test_text_the_parse_never_read_is_carried_into_the_mapping():
    """The structured-interchange invariant has a precondition: the parse must
    be complete before it can be authoritative. While the decomposer got
    `parsed.source`, a gap in the parse cost nothing. Once the registry became
    the only thing it sees, unparsed text stopped reaching the model at all — so
    the mapping has to carry what the parse did not read."""
    parsed = parse_task_file(TASK_WITH_AN_UNRECOGNISED_SECTION)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason="Covered elsewhere."),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    unread = [span.text for span in result.requirement_map.unread_source]
    assert unread == ["Invoices are currently rendered by a legacy template nobody owns."]


def test_the_cli_shouts_about_text_that_was_never_read():
    """Nothing else in the output hints that this text exists: it produced no
    requirement, so no disposition, no obligation and no question. Silence here
    is indistinguishable from the file not containing it."""
    from acceptance.cli import render_decomposition

    parsed = parse_task_file(TASK_WITH_AN_UNRECOGNISED_SECTION)
    response = {
        "obligations": [],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task-01", "no_obligation", reason="Nothing checkable."),
            _disposition("constraint-01", "no_obligation", reason="Nothing checkable."),
        ],
    }

    output = render_decomposition(decompose(parsed, _client_returning(response)))

    assert "NOT READ AS ANY REQUIREMENT" in output
    assert "legacy template nobody owns" in output


def test_a_fully_recognised_file_says_nothing_about_unread_text():
    from acceptance.cli import render_decomposition

    output = render_decomposition(_decomposition_with_a_shared_and_a_declined_requirement())

    assert "NOT READ AS ANY REQUIREMENT" not in output
