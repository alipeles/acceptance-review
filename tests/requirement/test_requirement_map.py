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

import inspect

from acceptance.requirement.obligations import _user_prompt, decompose
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
    return {
        "requirement_id": rid,
        "disposition": disposition,
        "obligation_ids": kwargs.get("obligation_ids", []),
        "open_question_ids": kwargs.get("open_question_ids", []),
        "reason": kwargs.get("reason", ""),
    }


# --- the registry -----------------------------------------------------------


def test_every_requirement_in_the_file_is_identified():
    registry = build_registry(parse_task_file(TASK))

    assert [r.id for r in registry] == [
        "task",
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


def test_a_fully_accounted_response_leaves_no_requirement_undisposed():
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
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["usd-format"]),
            _disposition("constraint-02", "yielded", obligation_ids=["csv-unchanged"]),
            _disposition("exclusion-01", "yielded", obligation_ids=["pdf-untouched"]),
            _disposition("completion-01", "yielded", obligation_ids=["usd-format"]),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    assert result.requirement_map.undisposed() == []
    assert result.requirement_map.unyielding() == []


def test_a_requirement_the_response_never_mentions_is_recorded_as_undisposed():
    """The load-bearing case. The response is well-formed and internally
    consistent; it simply says nothing about two of the five requirements, which
    is precisely what the old flat list could not express."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd-format", "Format money as USD.", "Format money as USD"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["usd-format"]),
            _disposition("completion-01", "yielded", obligation_ids=["usd-format"]),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    undisposed = [entry.requirement_id for entry in result.requirement_map.undisposed()]
    assert undisposed == ["constraint-02", "exclusion-01"]
    for entry in result.requirement_map.undisposed():
        assert entry.reason, "an undisposed requirement must say why it is undisposed"


def test_a_requirement_deliberately_yielding_nothing_carries_its_reason():
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
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
    # Declined is not the same as unread, and the two must stay distinguishable.
    assert result.requirement_map.undisposed() == []
    assert len(result.requirement_map.unyielding()) == 4


def test_a_yielded_claim_naming_no_real_obligation_is_not_honoured():
    """A disposition may not launder a requirement into 'handled' by naming an
    obligation the same response never produced."""
    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "yielded", obligation_ids=["never-emitted"]),
            _disposition("constraint-02", "yielded", obligation_ids=[]),
            _disposition("exclusion-01", "no_obligation", reason=""),
            _disposition("completion-01", "yielded", obligation_ids=["never-emitted"]),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    undisposed = [entry.requirement_id for entry in result.requirement_map.undisposed()]
    assert undisposed == ["constraint-01", "constraint-02", "exclusion-01", "completion-01"]


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
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
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
            _disposition("task", "yielded", obligation_ids=["dup"]),
            _disposition("constraint-01", "yielded", obligation_ids=["dup"]),
            _disposition("constraint-02", "no_obligation", reason="Not applicable."),
            _disposition("exclusion-01", "no_obligation", reason="Not applicable."),
            _disposition("completion-01", "no_obligation", reason="Not applicable."),
        ],
    }

    result = decompose(parsed, _client_returning(response))

    assert [o.id for o in result.obligations] == ["dup", "dup-2"]
    assert result.requirement_map.disposition_for("task").obligation_ids == ["dup"]
    assert result.requirement_map.undisposed() == []


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
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
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

    for requirement_id in ("[task]", "[constraint-01]", "[constraint-02]", "[exclusion-01]"):
        assert requirement_id in output, f"{requirement_id} is missing from the rendered mapping"
    assert "no obligation, deliberately" in output
    assert "Covered by the CSV suite." in output
    # A deliberate decline is a correct outcome; only an unaccounted requirement
    # is a failure, and the header must not merge the two into one number.
    assert "deliberately none: 1" in output
    assert "unaccounted for: 0" in output


def test_the_cli_says_when_an_obligation_serves_other_requirements():
    """Without this the same obligation appearing under three requirements reads
    as three duplicates rather than as one obligation with three links, which is
    the distinction DR-202 decision 2 turns on."""
    from acceptance.cli import render_decomposition

    output = render_decomposition(_decomposition_with_a_shared_and_a_declined_requirement())

    assert "also serves exclusion-01" in output
    assert "also serves completion-01" in output
    # An obligation is never told it serves the requirement it is listed under.
    assert "also serves task, exclusion-01" not in output


def test_an_obligation_no_requirement_claims_is_still_shown():
    """An unmapped obligation is an invention or a mapping failure — both are
    findings. Dropping it would recreate the same invisibility on the other
    axis."""
    from acceptance.cli import render_decomposition

    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("orphan", "An obligation no requirement claims.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    }

    output = render_decomposition(decompose(parsed, _client_returning(response)))

    assert "Obligations mapped to no requirement:" in output
    assert "orphan" in output


def test_the_header_separates_a_deliberate_decline_from_an_unaccounted_requirement():
    """One "yielding none" figure reads as a defect count, and only one of its
    three components is one. A bare section marker declined with a reason is a
    correct outcome; a requirement the decomposer never addressed is the recall
    failure the stage exists to surface. Merging them puts the defect back behind
    a number that looks the same either way."""
    from acceptance.cli import render_decomposition

    parsed = parse_task_file(TASK)
    response = {
        "obligations": [
            _obligation("render-lines", "Render each invoice line.", "Render each invoice line."),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _disposition("task", "yielded", obligation_ids=["render-lines"]),
            _disposition("constraint-01", "no_obligation", reason="A bare section marker."),
            # constraint-02, exclusion-01 and completion-01 go unmentioned.
        ],
    }

    output = render_decomposition(decompose(parsed, _client_returning(response)))

    assert "with obligations: 1" in output
    assert "deliberately none: 1" in output
    assert "UNACCOUNTED FOR: 3" in output
    assert output.count("!! UNACCOUNTED FOR") == 3
    # The correct decline is not shouted at.
    assert "!! UNACCOUNTED FOR — the decomposer did not address this\n       A bare section marker." not in output
