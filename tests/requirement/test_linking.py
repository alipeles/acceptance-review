"""#144 — de-duplication links obligations, it does not delete them.

The judgement itself (does the model *recognise* a duplicate?) is not testable
with injected responses: a test that supplies the link and then asserts the link
is asserting its own fixture. Those claims live in `tests/prompts/`, over the
recorded corpus. What is tested here is everything downstream of the judgement —
that a recognised duplicate produces a link rather than a deletion, that an
unrecognised one is left alone, and that the two stages stay separately
attributable.
"""

from __future__ import annotations

import json

import pytest

from acceptance.requirement.linking import (
    _LinkedPair,
    _Links,
    _clusters,
    link_duplicate_obligations,
)
from acceptance.requirement.obligations import Decomposition
from acceptance.review_state import (
    Disposition,
    Obligation,
    ObligationType,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
    RequirementSection,
)
from acceptance.source_ref import TextSpan
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_dispatching


def _obligation(obligation_id: str, description: str, start: int) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior=f"{obligation_id}() holds",
        source_spans=[TextSpan(text=description, start=start, end=start + len(description))],
    )


def _requirement(requirement_id: str, section: RequirementSection, ordinal: int) -> RequirementRef:
    return RequirementRef(
        id=requirement_id,
        section=section,
        ordinal=ordinal,
        span=TextSpan(text=requirement_id, start=0, end=len(requirement_id)),
    )


def _decomposition(*pairs: tuple[str, str]) -> Decomposition:
    """One obligation per requirement — derivation's output shape (#204)."""
    obligations = [
        _obligation(obligation_id, f"{obligation_id} is required", index * 100)
        for index, (_, obligation_id) in enumerate(pairs)
    ]
    requirements = [
        _requirement(
            requirement_id,
            RequirementSection.CONSTRAINT
            if requirement_id.startswith("constraint")
            else RequirementSection.COMPLETION,
            index,
        )
        for index, (requirement_id, _) in enumerate(pairs)
    ]
    dispositions = [
        RequirementDisposition(
            requirement_id=requirement_id,
            disposition=Disposition.YIELDED,
            obligation_ids=[obligation_id],
        )
        for requirement_id, obligation_id in pairs
    ]
    return Decomposition(
        obligations=obligations,
        requirement_map=RequirementMap(requirements=requirements, dispositions=dispositions),
    )


def _client(links: list[dict]):
    return client_dispatching({"_Links": {"links": links}})


def _link(canonical: str, duplicate: str, reason: str = "same requirement") -> dict:
    return {
        "canonical_obligation_id": canonical,
        "duplicate_obligation_id": duplicate,
        "reason": reason,
    }


# --- the link, not a deletion ------------------------------------------------


def test_one_requirement_stated_in_two_sections_yields_one_obligation_linked_to_both():
    """The issue's headline acceptance, in its post-DR-204 shape: one obligation
    named by BOTH requirements, not one obligation and one deletion."""
    decomposition = _decomposition(
        ("constraint-01", "typed-links"), ("completion-01", "typed-links-tested")
    )

    linked = link_duplicate_obligations(
        decomposition, _client([_link("typed-links", "typed-links-tested")])
    )

    assert [o.id for o in linked.obligations] == ["typed-links"]
    named_by = [
        d.requirement_id
        for d in linked.requirement_map.dispositions
        if "typed-links" in d.obligation_ids
    ]
    assert named_by == ["constraint-01", "completion-01"]


def test_the_surviving_obligation_carries_the_source_spans_of_both_statements():
    """Nothing is discarded — the merged obligation still traces to every piece
    of task text that produced it, which the findings-link invariant requires."""
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    linked = link_duplicate_obligations(decomposition, _client([_link("alpha", "beta")]))

    survivor = linked.obligations[0]
    assert [span.text for span in survivor.source_spans] == [
        "alpha is required",
        "beta is required",
    ]


def test_no_requirement_is_left_without_an_obligation_by_a_merge():
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    linked = link_duplicate_obligations(decomposition, _client([_link("alpha", "beta")]))

    assert all(d.obligation_ids for d in linked.requirement_map.dispositions)


# --- under-merging bias ------------------------------------------------------


def test_obligations_the_model_does_not_link_are_left_separate():
    """The bias is load-bearing: an unreported pair must survive intact, or the
    pass would be merging on its own initiative rather than on a judgement."""
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    linked = link_duplicate_obligations(decomposition, _client([]))

    assert [o.id for o in linked.obligations] == ["alpha", "beta"]
    assert [d.obligation_ids for d in linked.requirement_map.dispositions] == [["alpha"], ["beta"]]


def test_a_single_obligation_makes_no_model_call_at_all():
    """Nothing can be linked to nothing. Asserted because the call is not free."""
    calls: list[str] = []

    def counting(**kwargs):
        calls.append(kwargs["response_format"]["json_schema"]["name"])
        raise AssertionError("the linking pass must not call the model here")

    decomposition = _decomposition(("constraint-01", "alpha"))
    client = client_dispatching({})
    client.completion_fn = counting

    assert link_duplicate_obligations(decomposition, client) is decomposition
    assert calls == []


# --- the link is a typed field ----------------------------------------------


def test_a_link_is_read_from_the_typed_ids_and_never_from_free_text():
    """`reason` is an audit field and carries no relation. A response whose prose
    asserts a merge, while its id fields do not, merges nothing.

    This is the discriminating case for "links are typed fields": if the pass
    ever read the relation out of free text, this response would merge."""
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    linked = link_duplicate_obligations(
        decomposition,
        _client([_link("alpha", "alpha", reason="alpha and beta are the same requirement")]),
    )

    assert [o.id for o in linked.obligations] == ["alpha", "beta"]


def test_the_response_schema_offers_no_free_text_route_to_a_link():
    """The relation is expressible only as the two id fields. A schema that also
    accepted, say, a list of ids in a string would let the model state a link the
    code cannot validate or count (#211)."""
    schema = _Links.model_json_schema()
    pair = schema["$defs"]["_LinkedPair"]["properties"]

    assert set(pair) == {"canonical_obligation_id", "duplicate_obligation_id", "reason"}
    assert pair["canonical_obligation_id"]["type"] == "string"
    assert pair["duplicate_obligation_id"]["type"] == "string"
    # One duplicate per pair: a list would let one entry name several ids, and
    # "which of these is the survivor" would stop being a property of the shape.
    assert schema["$defs"]["_LinkedPair"]["type"] == "object"


def test_an_unsupplied_obligation_id_is_recorded_rather_than_silently_dropped():
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))
    unusable = UnusableAnswerLog()

    linked = link_duplicate_obligations(
        decomposition, _client([_link("alpha", "not-an-obligation")]), unusable
    )

    assert [o.id for o in linked.obligations] == ["alpha", "beta"]
    assert unusable.answers, "a link naming an id we never supplied must be recorded"


# --- determinism of the merge itself ----------------------------------------


def test_the_survivor_is_chosen_by_derivation_order_not_by_the_models_nomination():
    """Two responses that agree on WHICH obligations are duplicates must agree on
    the survivor, even when they nominate opposite members."""
    forward = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))
    backward = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    one = link_duplicate_obligations(forward, _client([_link("alpha", "beta")]))
    two = link_duplicate_obligations(backward, _client([_link("beta", "alpha")]))

    assert [o.id for o in one.obligations] == [o.id for o in two.obligations] == ["alpha"]


def test_a_transitive_chain_resolves_to_one_cluster():
    survivors = _clusters(
        ["alpha", "beta", "gamma"],
        [
            _LinkedPair(
                canonical_obligation_id="gamma", duplicate_obligation_id="beta", reason="r"
            ),
            _LinkedPair(
                canonical_obligation_id="beta", duplicate_obligation_id="alpha", reason="r"
            ),
        ],
    )

    assert survivors == {"alpha": "alpha", "beta": "alpha", "gamma": "alpha"}


@pytest.mark.parametrize(
    "pair",
    [
        ("alpha", "alpha"),  # self-link asserts nothing
        ("alpha", "missing"),  # id never supplied
    ],
)
def test_a_link_that_asserts_nothing_merges_nothing(pair):
    canonical, duplicate = pair
    survivors = _clusters(
        ["alpha", "beta"],
        [
            _LinkedPair(
                canonical_obligation_id=canonical, duplicate_obligation_id=duplicate, reason="r"
            )
        ],
    )

    assert survivors == {"alpha": "alpha", "beta": "beta"}


def test_the_same_derived_obligations_produce_the_same_links():
    """The stage-2 half of the determinism requirement: linking is a function of
    the derived obligations, so an unchanged derivation yields unchanged links."""
    first = link_duplicate_obligations(
        _decomposition(("constraint-01", "alpha"), ("completion-01", "beta")),
        _client([_link("alpha", "beta")]),
    )
    second = link_duplicate_obligations(
        _decomposition(("constraint-01", "alpha"), ("completion-01", "beta")),
        _client([_link("alpha", "beta")]),
    )

    assert first.to_dict() == second.to_dict()


def test_the_prompt_shows_typed_fields_and_never_the_task_files_markdown():
    """The interchange invariant: the parse has already computed this structure,
    so the model is handed identified fields, not source to re-derive."""
    from acceptance.requirement.linking import _user_prompt

    prompt = _user_prompt(_decomposition(("constraint-01", "alpha"), ("completion-01", "beta")))

    assert "[alpha]" in prompt and "derived from requirement: constraint-01" in prompt
    assert "## Constraints" not in prompt
    assert json.dumps(prompt).count("\\n\\n") >= 1


# --- wiring: the pipeline actually runs this pass ---------------------------
#
# Defect injection has repeatedly found the same hole in this repo: a helper with
# a good unit test that the pipeline never calls. Every assertion below goes
# through `run_review`, so a linking pass that was written but not wired fails
# here rather than passing everything above.

_TASK = """# Task
The report shows a tier on every line.

## Constraints
- Every rendered line carries its evidence tier.

## Completion expectations
- A test asserts that every rendered line carries its evidence tier.
"""

_DERIVED = {
    "obligations": [
        {
            "id": "tier-on-every-line",
            "description": "Every rendered line carries its evidence tier",
            "type": "functional",
            "importance": "critical",
            "explicit": True,
            "observable_behavior": "each line shows a tier",
            "source_quote": "Every rendered line carries its evidence tier.",
        },
        {
            "id": "tier-on-every-line-tested",
            "description": "A test asserts every rendered line carries its tier",
            "type": "regression",
            "importance": "critical",
            "explicit": True,
            "observable_behavior": "a test asserts each line shows a tier",
            "source_quote": "A test asserts that every rendered line carries its evidence tier.",
        },
    ],
    "open_questions": [],
    "requirement_dispositions": [
        {
            "requirement_id": "constraint-01",
            "disposition": "yielded",
            "obligation_id": "tier-on-every-line",
            "more_obligation_ids": [],
        },
        {
            "requirement_id": "completion-01",
            "disposition": "yielded",
            "obligation_id": "tier-on-every-line-tested",
            "more_obligation_ids": [],
        },
        # Every requirement carries a disposition or the response is malformed
        # (#204) — the Task prose is declined here so the fixture is about the
        # Constraints/Completion duplicate and nothing else.
        {
            "requirement_id": "task-01",
            "disposition": "no_obligation",
            "reason": "restated as constraint-01",
        },
    ],
}

_MERGE = {
    "links": [
        {
            "canonical_obligation_id": "tier-on-every-line",
            "duplicate_obligation_id": "tier-on-every-line-tested",
            "reason": "the constraint and its acceptance criterion state one requirement",
        }
    ]
}


def _repo(tmp_path):
    import subprocess

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "render.py").write_text("def render():\n    return ''\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    (tmp_path / "render.py").write_text("def render():\n    return 'tier'\n")
    git("add", "-A")
    git("commit", "-qm", "head")
    return base, git("rev-parse", "HEAD")


def _reviewed(tmp_path, links=_MERGE):
    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review

    base, head = _repo(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching({"_Decomposition": _DERIVED, "_Links": links}),
        reviewed_revision=head,
    )


def test_the_pipeline_links_duplicates_before_the_rest_of_the_review_runs(tmp_path):
    review = _reviewed(tmp_path)

    assert [o.id for o in review.obligation_map] == ["tier-on-every-line"]


def test_the_pre_link_obligations_are_persisted_in_the_review_state(tmp_path):
    """Stage 1's output is provenance, not report content — but it is on disk, or
    a movement in the final set cannot be attributed to the stage that caused it."""
    review = _reviewed(tmp_path)

    assert [o.id for o in review.derived_obligation_map] == [
        "tier-on-every-line",
        "tier-on-every-line-tested",
    ]


def test_the_two_stages_are_separately_readable_from_the_stored_review(tmp_path):
    """The whole point of persisting stage 1: the two sets differ, and a reader
    can see which stage removed the obligation."""
    review = _reviewed(tmp_path)

    assert len(review.derived_obligation_map) == 2
    assert len(review.obligation_map) == 1


def test_both_requirements_name_the_surviving_obligation_in_the_stored_map(tmp_path):
    review = _reviewed(tmp_path)

    assert review.requirement_map is not None
    named = {d.requirement_id: d.obligation_ids for d in review.requirement_map.dispositions}
    assert named["constraint-01"] == ["tier-on-every-line"]
    assert named["completion-01"] == ["tier-on-every-line"]


def test_a_review_that_links_nothing_keeps_both_obligations(tmp_path):
    """The discriminating half: if the pipeline merged on its own rather than on
    the pass's judgement, this would collapse too."""
    review = _reviewed(tmp_path, links={"links": []})

    assert len(review.obligation_map) == 2
    assert len(review.derived_obligation_map) == 2


def test_two_runs_over_identical_task_text_produce_identical_state_at_both_stages(tmp_path):
    """Determinism at BOTH stages, which is what makes a movement attributable."""
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    first = _reviewed(one)
    second = _reviewed(two)

    assert [o.id for o in first.derived_obligation_map] == [
        o.id for o in second.derived_obligation_map
    ]
    assert [o.to_dict() for o in first.obligation_map] == [
        o.to_dict() for o in second.obligation_map
    ]
