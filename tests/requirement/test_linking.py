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

from acceptance.requirement.linking import (
    _confirmed_clusters,
    _pairs,
    _PairVerdict,
    _Verdicts,
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


def _client_confirming(ordered_ids: list[str], same: set[frozenset[str]]):
    """Answer every pair: True for the ones named, False for the rest.

    A double that answered only the True pairs would not exercise the sweep —
    the stage asks about every pair and a real response carries a verdict for
    each, so the double must too.
    """
    verdicts = [
        {
            "pair_id": pair_id,
            "same_requirement": frozenset((left, right)) in same,
            "reason": "test double",
        }
        for pair_id, left, right in _pairs(ordered_ids)
    ]
    return client_dispatching({"_Verdicts": {"verdicts": verdicts}})


def _client(same_pairs: list[tuple[str, str]] = ()):
    """For the two-obligation fixtures, whose ids are always alpha/beta-shaped."""
    return _client_confirming(_IDS, {frozenset(pair) for pair in same_pairs})


_IDS = ["alpha", "beta"]


# --- the link, not a deletion ------------------------------------------------


def test_one_requirement_stated_in_two_sections_yields_one_obligation_linked_to_both():
    """The issue's headline acceptance, in its post-DR-204 shape: one obligation
    named by BOTH requirements, not one obligation and one deletion."""
    decomposition = _decomposition(
        ("constraint-01", "typed-links"), ("completion-01", "typed-links-tested")
    )

    linked = link_duplicate_obligations(
        decomposition,
        _client_confirming(
            ["typed-links", "typed-links-tested"],
            {frozenset(("typed-links", "typed-links-tested"))},
        ),
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

    linked = link_duplicate_obligations(decomposition, _client([("alpha", "beta")]))

    survivor = linked.obligations[0]
    assert [span.text for span in survivor.source_spans] == [
        "alpha is required",
        "beta is required",
    ]


def test_no_requirement_is_left_without_an_obligation_by_a_merge():
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    linked = link_duplicate_obligations(decomposition, _client([("alpha", "beta")]))

    assert all(d.obligation_ids for d in linked.requirement_map.dispositions)


# --- under-merging bias ------------------------------------------------------


def test_obligations_the_model_does_not_link_are_left_separate():
    """The bias is load-bearing: an unreported pair must survive intact, or the
    pass would be merging on its own initiative rather than on a judgement."""
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    linked = link_duplicate_obligations(decomposition, _client())

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

    verdicts = [
        {
            "pair_id": pair_id,
            "same_requirement": False,
            "reason": "alpha and beta are the same requirement",
        }
        for pair_id, _, _ in _pairs(_IDS)
    ]
    linked = link_duplicate_obligations(
        decomposition, client_dispatching({"_Verdicts": {"verdicts": verdicts}})
    )

    assert [o.id for o in linked.obligations] == ["alpha", "beta"]


def test_the_response_schema_offers_no_free_text_route_to_a_link():
    """The relation is expressible only as a boolean against a pair the code
    chose. There is no field in which the model could name an obligation, so it
    cannot state a link the code is unable to validate or count (#211)."""
    schema = _Verdicts.model_json_schema()
    verdict = schema["$defs"]["_PairVerdict"]["properties"]

    assert set(verdict) == {"pair_id", "same_requirement", "reason"}
    assert verdict["same_requirement"]["type"] == "boolean"
    assert verdict["pair_id"]["type"] == "string"


def test_an_unsupplied_obligation_id_is_recorded_rather_than_silently_dropped():
    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))
    unusable = UnusableAnswerLog()

    linked = link_duplicate_obligations(
        decomposition,
        client_dispatching(
            {
                "_Verdicts": {
                    "verdicts": [
                        {
                            "pair_id": "pair-9999",
                            "same_requirement": True,
                            "reason": "a pair this call was never given",
                        }
                    ]
                }
            }
        ),
        unusable,
    )

    assert [o.id for o in linked.obligations] == ["alpha", "beta"]
    assert unusable.answers, "a link naming an id we never supplied must be recorded"


# --- determinism of the merge itself ----------------------------------------


def test_the_survivor_is_chosen_by_derivation_order_not_by_the_models_nomination():
    """Two responses that agree on WHICH obligations are duplicates must agree on
    the survivor, even when they nominate opposite members."""
    forward = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))
    backward = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))

    one = link_duplicate_obligations(forward, _client([("alpha", "beta")]))
    two = link_duplicate_obligations(backward, _client([("beta", "alpha")]))

    assert [o.id for o in one.obligations] == [o.id for o in two.obligations] == ["alpha"]


def test_a_confirmed_triangle_merges_into_one_cluster():
    """Sameness is transitive — the criterion is identical truth conditions — so
    a fully confirmed triangle is one requirement stated three ways."""
    survivors, inconsistent = _confirmed_clusters(
        ["alpha", "beta", "gamma"],
        {
            frozenset(("alpha", "beta")),
            frozenset(("beta", "gamma")),
            frozenset(("alpha", "gamma")),
        },
    )

    assert survivors == {"alpha": "alpha", "beta": "alpha", "gamma": "alpha"}
    assert inconsistent == []


def test_an_inconsistent_triangle_merges_nothing_and_is_recorded():
    """alpha~beta and beta~gamma confirmed, alpha~gamma denied. The relation is
    transitive, so these three answers cannot all be right — and because every
    pair was asked, the contradiction is visible rather than inferred away.

    Nothing merges. Resolving it would mean choosing which answer to believe,
    and every failure this pass has had was an over-merge."""
    survivors, inconsistent = _confirmed_clusters(
        ["alpha", "beta", "gamma"],
        {frozenset(("alpha", "beta")), frozenset(("beta", "gamma"))},
    )

    assert survivors == {"alpha": "alpha", "beta": "beta", "gamma": "gamma"}
    assert inconsistent == [["alpha", "beta", "gamma"]]


def test_an_inconsistency_does_not_block_an_unrelated_confirmed_pair():
    """The conservative rule is per-component, not global: one contradiction must
    not discard every other judgment in the run."""
    survivors, inconsistent = _confirmed_clusters(
        ["alpha", "beta", "gamma", "delta", "epsilon"],
        {
            frozenset(("alpha", "beta")),
            frozenset(("beta", "gamma")),
            frozenset(("delta", "epsilon")),
        },
    )

    assert survivors["delta"] == "delta" and survivors["epsilon"] == "delta"
    assert inconsistent == [["alpha", "beta", "gamma"]]


def test_the_same_derived_obligations_produce_the_same_links():
    """The stage-2 half of the determinism requirement: linking is a function of
    the derived obligations, so an unchanged derivation yields unchanged links."""
    first = link_duplicate_obligations(
        _decomposition(("constraint-01", "alpha"), ("completion-01", "beta")),
        _client([("alpha", "beta")]),
    )
    second = link_duplicate_obligations(
        _decomposition(("constraint-01", "alpha"), ("completion-01", "beta")),
        _client([("alpha", "beta")]),
    )

    assert first.to_dict() == second.to_dict()


def test_the_prompt_shows_typed_fields_and_never_the_task_files_markdown():
    """The interchange invariant: the parse has already computed this structure,
    so the model is handed identified fields, not source to re-derive."""
    from acceptance.requirement.linking import _user_prompt

    decomposition = _decomposition(("constraint-01", "alpha"), ("completion-01", "beta"))
    prompt = _user_prompt(decomposition, _pairs(_IDS))

    assert "[pair-0000]" in prompt
    assert "[alpha] from requirement constraint-01" in prompt
    assert "[beta] from requirement completion-01" in prompt
    assert "## Constraints" not in prompt


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


def _verdicts(same: bool):
    """Two derived obligations means exactly one pair to answer."""
    return {
        "verdicts": [{"pair_id": "pair-0000", "same_requirement": same, "reason": "test double"}]
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


def _reviewed(tmp_path, same=True):
    from acceptance.change.diff import extract_change_set
    from acceptance.pipeline import run_review

    base, head = _repo(tmp_path)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(tmp_path, base, head),
        repo=tmp_path,
        client=client_dispatching({"_Decomposition": _DERIVED, "_Verdicts": _verdicts(same)}),
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
    review = _reviewed(tmp_path)

    assert len(review.derived_obligation_map) == 2
    assert len(review.obligation_map) == 1


def test_both_requirements_name_the_surviving_obligation_in_the_stored_map(tmp_path):
    review = _reviewed(tmp_path)

    assert review.requirement_map is not None
    named = {d.requirement_id: d.obligation_ids for d in review.requirement_map.dispositions}
    assert named["constraint-01"] == ["tier-on-every-line"]
    assert named["completion-01"] == ["tier-on-every-line"]


def test_a_review_whose_pair_comes_back_false_keeps_both_obligations(tmp_path):
    """The discriminating half: if the pipeline merged on its own rather than on
    the pass's judgement, this would collapse too."""
    review = _reviewed(tmp_path, same=False)

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


# --- wiring: `decompose` de-duplicates too, not only `check` ----------------


def test_the_decompose_command_runs_the_linking_pass(tmp_path, monkeypatch):
    """Obligation determination is two stages, and `decompose` reports its
    OUTPUT. A decompose that skipped linking would show a different obligation
    set from the one `check` reviews — so the breakdown a reader confirms would
    not be the set every later stage judges.

    Asserted through the CLI entry point rather than the helper, because the
    defect being guarded is precisely a stage that exists but is not called.
    """
    from acceptance import cli

    called: list[int] = []
    real = cli.link_duplicate_obligations

    def spy(decomposition, client, *args, **kwargs):
        called.append(len(decomposition.obligations))
        return real(decomposition, client, *args, **kwargs)

    monkeypatch.setattr(cli, "link_duplicate_obligations", spy)
    task = tmp_path / "task.md"
    task.write_text(_TASK)
    monkeypatch.setattr(
        cli.RunConfig, "build_client", lambda self: client_dispatching({"_Decomposition": _DERIVED})
    )

    result, _ = cli.run_decompose(str(task), cli.RunConfig())

    assert called == [2], "decompose must hand its derived obligations to the linking pass"
    assert len(result.obligations) <= 2


def test_the_decompose_command_surfaces_an_unreconciled_group(tmp_path, monkeypatch, capsys):
    """A rejected clique is the difference between "nothing looked like a
    duplicate" and "the answers could not be reconciled, so nothing merged".
    Dropping the log would report the first while the second happened."""
    from acceptance import cli

    task = tmp_path / "task.md"
    task.write_text(_TASK)
    monkeypatch.setattr(
        cli.RunConfig, "build_client", lambda self: client_dispatching({"_Decomposition": _DERIVED})
    )

    _, unusable = cli.run_decompose(str(task), cli.RunConfig())

    assert hasattr(unusable, "answers"), "decompose must carry the linking stage's log"


def test_the_linking_schemas_are_pydantic_models():
    """Typed schemas are pydantic models, as the rest of the repository defines
    them — asserted rather than assumed.

    Not a style check. `constrain` builds the id-restricted subclass with
    pydantic's model machinery and `model_json_schema` is what reaches the
    provider, so a hand-rolled schema class would pass every behavioural test
    here and break the supplied-id guarantee (#163) at the wire.
    """
    from pydantic import BaseModel

    from acceptance.review_state import Obligation

    assert issubclass(_Verdicts, BaseModel)
    assert issubclass(_PairVerdict, BaseModel)
    # The review-state field this task adds is the same model type as the
    # obligations it holds, so the pre-link set serialises canonically too.
    assert issubclass(Obligation, BaseModel)


def test_the_constrained_response_schema_is_still_a_pydantic_model():
    """`constrain` returns a subclass, so the guarantee survives the narrowing
    the stage applies before every call."""
    from pydantic import BaseModel

    from acceptance.supplied_ids import constrain

    narrowed = constrain(_Verdicts, {"pair_id": ["pair-0000"]})

    assert issubclass(narrowed, BaseModel)
    assert issubclass(narrowed, _Verdicts)


# --- a test demand and its behavior never merge (#232, DR-232) ---------------


def _typed_decomposition(*specs: tuple[str, str, ObligationType]) -> Decomposition:
    """Like `_decomposition`, but each obligation carries a chosen type."""
    base = _decomposition(
        *[(requirement_id, obligation_id) for requirement_id, obligation_id, _ in specs]
    )
    retyped = [
        obligation.model_copy(update={"type": obligation_type})
        for obligation, (_, _, obligation_type) in zip(base.obligations, specs)
    ]
    return base.model_copy(update={"obligations": retyped})


def _behaviour_and_its_test() -> Decomposition:
    return _typed_decomposition(
        ("constraint-01", "alpha", ObligationType.FUNCTIONAL),
        ("completion-01", "beta", ObligationType.TEST_DEMAND),
    )


def test_a_behaviour_and_a_demand_for_a_test_of_it_are_never_asked_about():
    """The pair is not a question. Skipping it, rather than asking and hoping
    for `false`, is what makes the non-merger a property of the code.

    Two prompt attempts failed to stop this merge, because the prompt's own
    sameness criteria point the wrong way: the test that asserts X is also the
    evidence for X, so "the same test would demonstrate both" reads true."""
    decomposition = _behaviour_and_its_test()

    assert _pairs(["alpha", "beta"], {o.id: o for o in decomposition.obligations}) == []


def test_a_behaviour_and_a_demand_for_a_test_of_it_are_not_merged_even_if_confirmed():
    """The stronger property: a model that says `true` cannot merge them.

    Asserting on the outcome and not merely on which questions were asked —
    a later change that reinstated the question would still have to keep the
    obligations apart to pass this."""
    decomposition = _behaviour_and_its_test()

    linked = link_duplicate_obligations(
        decomposition, _client_confirming(["alpha", "beta"], {frozenset(("alpha", "beta"))})
    )

    assert [obligation.id for obligation in linked.obligations] == ["alpha", "beta"]
    behaviour = linked.requirement_map.disposition_for("constraint-01").obligation_ids
    its_test = linked.requirement_map.disposition_for("completion-01").obligation_ids
    assert set(behaviour).isdisjoint(its_test)


def test_two_test_demands_can_still_merge_with_each_other():
    """The rule is about a MIXED pair. Two obligations that both demand a test
    are ordinary candidates, and a rule that skipped every `test_demand` pair
    would silently stop de-duplicating them."""
    decomposition = _typed_decomposition(
        ("constraint-01", "alpha", ObligationType.TEST_DEMAND),
        ("completion-01", "beta", ObligationType.TEST_DEMAND),
    )

    linked = link_duplicate_obligations(
        decomposition, _client_confirming(["alpha", "beta"], {frozenset(("alpha", "beta"))})
    )

    assert len(linked.obligations) == 1


def test_no_model_call_is_made_when_every_pair_is_structurally_settled():
    """Two obligations, one pair, and that pair cannot merge — so there is
    nothing to ask. The stage already skips the call for a single obligation;
    this is the same economy for a set whose every pair is decided."""

    calls: list[str] = []

    def counting(**kwargs):
        calls.append(kwargs["response_format"]["json_schema"]["name"])
        raise AssertionError("linking made a call about a structurally settled pair")

    client = client_dispatching({})
    client.completion_fn = counting

    linked = link_duplicate_obligations(_behaviour_and_its_test(), client)

    assert len(linked.obligations) == 2
    assert calls == []
