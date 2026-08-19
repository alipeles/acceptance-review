"""#269 — an obligation is carried forward when its requirement did not change.

The acceptance items from the issue, each as a test. What every one of them is
really guarding is the same thing: `decompose` used to be a pure function of the
task text, so one edited character re-derived all of it and re-minted every
identifier. #191 measured the cost — 38 distinct criterion wordings across three
runs of ~20 criteria, zero content difference — and since criterion text is the
prompt for every later stage, that churn floors every downstream stability
number.

The tests inject responses rather than calling a model, per the replay-first
invariant. Where a test is about **whether a call was issued at all**, it counts
calls off the double rather than inspecting output: an obligation that was
re-derived to an identical value and one that was never asked about produce the
same obligation and are entirely different behaviours.
"""

from __future__ import annotations

import json

from acceptance.llm import inline_schema_refs
from acceptance.requirement import obligations as obligations_module
from acceptance.requirement.carry import plan_carry, stale_spans
from acceptance.requirement.ledger import (
    DECOMPOSE_STAGE_LOGIC_VERSION,
    Derivation,
    LedgerEntry,
    LedgerStore,
    MergeDecision,
    RequirementDerivation,
    carry_key,
    new_run_id,
)
from acceptance.requirement.linking import link_duplicate_obligations
from acceptance.requirement.obligations import (
    Decomposition,
    build_ledger_entry,
    decompose,
    decompose_carry_keys,
)
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
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
from tests.support import client_dispatching

_TASK = """# Task
The tool records what it derived.

## Constraints
- The ledger is append-only.
- The run reports its own identifier.

## Completion expectations
- Implementation
- A test asserts the ledger is append-only.
"""


def _response_for(requirement_ids: list[str]) -> dict:
    """One yielded obligation per requirement, ids derived from the requirement."""
    return {
        "open_questions": [],
        "requirement_dispositions": [
            {
                "requirement_id": requirement_id,
                "disposition": "yielded",
                "obligation": {
                    "id": f"ob-{requirement_id}",
                    "description": f"obligation for {requirement_id}",
                    "type": "functional",
                    "importance": "normal",
                    "explicit": True,
                    "observable_behavior": f"{requirement_id} holds",
                    "source_quote": "",
                    "required_evidence": "code_and_tests",
                    "required_evidence_reason": "",
                },
                "more_obligations": [],
            }
            for requirement_id in requirement_ids
        ],
    }


class _CountingClient:
    """A double that records every call it was asked to answer.

    Uses `client_dispatching(capture=...)`, the helper's own supported hook, so
    the count is of calls the client actually issued rather than of a wrapper this
    test hoped was installed.
    """

    def __init__(self, task: str, alignment: list[dict] | None = None, **kwargs):
        self.calls: list[dict] = []
        parsed = parse_task_file(task)
        ids = [requirement.id for requirement in build_registry(parsed)]
        self.client = client_dispatching(
            {
                "_Decomposition": _response_for(ids),
                # The residue aligner (#209), reached only when both sides have
                # requirements left over after exact-text matching. Defaults to
                # matching nothing, which is what a correct aligner returns for
                # two unrelated task files.
                "_Alignment": {"matches": alignment or []},
            },
            capture=self.calls,
            **kwargs,
        )

    @property
    def decompose_calls(self) -> int:
        return sum(1 for call in self.calls if call["schema"] == "_Decomposition")

    def prompts_for(self, schema: str) -> list[str]:
        return [call["prompt"] for call in self.calls if call["schema"] == schema]


def _run(task: str, prior: LedgerEntry | None = None, alignment=None, **kwargs):
    """Decompose `task`, returning the result and how many calls it took."""
    parsed = parse_task_file(task)
    counting = _CountingClient(task, alignment=alignment, **kwargs)
    result = decompose(parsed, counting.client, prior=prior)
    return result, counting


def _ledger_from(result, run_id: str = "run-one", parent: str | None = None) -> LedgerEntry:
    return build_ledger_entry(result, run_id=run_id, parent_run_id=parent, task_digest="d")


# --- the headline: an unchanged task file costs nothing ----------------------


def test_a_rerun_over_an_unchanged_task_file_issues_no_decompose_call():
    """The acceptance item the whole issue exists for.

    Counted off the double, not inferred from the output: re-deriving to the same
    answer and not asking at all are indistinguishable in the result and are the
    entire difference this change makes.
    """
    first, _ = _run(_TASK)
    prior = _ledger_from(first)

    _, second = _run(_TASK, prior=prior)

    assert second.decompose_calls == 0


def test_a_rerun_over_an_unchanged_task_file_returns_byte_identical_obligations():
    """Identifiers and descriptions included — the churn #191 measured is exactly
    a change of identifier and wording over unchanged substance, so comparing the
    obligation set alone would pass while the defect was fully present."""
    first, _ = _run(_TASK)
    second, _ = _run(_TASK, prior=_ledger_from(first))

    assert [o.to_dict() for o in second.obligations] == [o.to_dict() for o in first.obligations]
    assert [o.id for o in second.obligations] == [o.id for o in first.obligations]
    assert [o.description for o in second.obligations] == [o.description for o in first.obligations]


def test_every_requirement_is_recorded_as_carried():
    first, _ = _run(_TASK)
    second, _ = _run(_TASK, prior=_ledger_from(first))

    assert {d.derivation for d in second.derivations} == {Derivation.CARRIED}
    assert all(
        disposition.derivation == "carried" for disposition in second.requirement_map.dispositions
    )


def test_a_carried_disposition_records_the_digest_it_came_from_not_a_run_id():
    """`carried_from` holds a CONTENT digest deliberately.

    A run id is minted randomly, so recording one in review state would make two
    runs over the same input differ in their bytes and break M0.5. The digest is
    a function of the derivation itself.
    """
    first, _ = _run(_TASK)
    prior = _ledger_from(first, run_id="run-abc")
    second, _ = _run(_TASK, prior=prior)

    digests = {d.carried_from for d in second.requirement_map.dispositions}
    assert None not in digests
    assert "run-abc" not in digests
    by_text = prior.by_text()
    for derivation in second.derivations:
        assert derivation.carried_from == by_text[derivation.text].digest()


# --- default-to-fresh, and no cross-task contamination -----------------------


def test_no_continued_run_carries_nothing():
    result, counting = _run(_TASK)

    assert counting.decompose_calls > 0
    assert {d.derivation for d in result.derivations} == {Derivation.DERIVED}


def test_a_ledger_recording_a_different_task_produces_what_an_empty_ledger_does():
    """Cross-task contamination is a bug, not a feature of carrying forward.

    Identity is the requirement's exact text, so a ledger whose requirements share
    none of this task's wording matches nothing and every requirement derives
    fresh — the same result as no ledger at all.
    """
    other = """# Task
Something else entirely.

## Constraints
- Pagination is unchanged.
"""
    other_result, _ = _run(other)
    against_other, counting_other = _run(_TASK, prior=_ledger_from(other_result))
    against_nothing, counting_nothing = _run(_TASK)

    assert [o.to_dict() for o in against_other.obligations] == [
        o.to_dict() for o in against_nothing.obligations
    ]
    assert counting_other.decompose_calls == counting_nothing.decompose_calls


# --- editing one requirement -------------------------------------------------

_EDITED = _TASK.replace("- The ledger is append-only.", "- The ledger is only ever appended to.")


def test_editing_one_requirement_leaves_every_other_requirement_carried():
    """The other half of the headline: an edit costs one requirement, not all of
    them. Before this change, `rerun.py`'s rule was that a changed task
    invalidates everything."""
    first, _ = _run(_TASK)

    # The aligner matches the one edited bullet to the one it replaced — the only
    # residue on either side.
    second, counting = _run(
        _EDITED,
        prior=_ledger_from(first),
        alignment=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    kinds = {d.requirement_id: d.derivation for d in second.derivations}
    changed = [rid for rid, kind in kinds.items() if kind is not Derivation.CARRIED]
    assert len(changed) == 1, kinds
    assert kinds[changed[0]] is Derivation.REVISED
    assert counting.decompose_calls == 1


def test_an_edited_requirements_persisting_obligations_keep_their_identifiers():
    """Id stability across an edit is the whole point — #191 found identifiers
    re-minted alongside re-worded criteria on input that had not changed at all.

    The prompt is what carries this: the revised requirement's previous wording
    and the obligations it produced are put in front of the model, so reusing an
    id is available to it. Asserted on the prompt because the response is a
    fixture — a test that injected the reused id and then asserted it would be
    asserting its own double.
    """
    first, _ = _run(_TASK)
    prior = _ledger_from(first)
    previous_ids = [o.id for o in prior.derivations[1].obligations]

    _, counting = _run(
        _EDITED,
        prior=prior,
        alignment=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    prompt = counting.prompts_for("_Decomposition")[0]
    assert "PREVIOUSLY DERIVED" in prompt
    assert "The ledger is append-only." in prompt
    for obligation_id in previous_ids:
        assert obligation_id in prompt
    assert "reuse its id" in prompt


def test_a_fresh_run_prompt_is_unchanged_by_the_revision_block():
    """`completion-06` in prompt form: with nothing carried, the request this
    stage issues is byte-for-byte what it issued before carry-forward existed, so
    every recorded transcript still replays and no work is lost to a tool update.
    """
    _, counting = _run(_TASK)

    for prompt in counting.prompts_for("_Decomposition"):
        assert "PREVIOUSLY DERIVED" not in prompt


def test_a_revised_requirement_records_that_it_was_revised_and_why():
    """`constraint-32` and `constraint-33`.

    Found by the tool's own Gate 2, and it was a defect rather than a missing
    test: a revised requirement's disposition came back saying `derived` with no
    reason, which is exactly what a genuinely new requirement says. The two are
    different — one had a predecessor and was re-asked against it — and losing the
    distinction loses the only record that an identifier could have been reused.
    """
    first, _ = _run(_TASK)
    prior = _ledger_from(first)

    second, _ = _run(_EDITED, prior=prior, alignment=[{"ground_truth": "g0", "reviewer": "r0"}])

    revised = [d for d in second.derivations if d.derivation is Derivation.REVISED]
    assert len(revised) == 1
    assert "The ledger is append-only." in revised[0].revision_reason

    disposition = second.requirement_map.disposition_for(revised[0].requirement_id)
    assert disposition.derivation == "revised"
    assert disposition.revision_reason == revised[0].revision_reason
    assert disposition.carried_from is not None

    # And the untouched requirements are not stamped, so the mark means something.
    others = [
        d
        for d in second.requirement_map.dispositions
        if d.requirement_id != revised[0].requirement_id
    ]
    assert {d.derivation for d in others} == {"carried"}
    assert all(d.revision_reason is None for d in others)


def test_carrying_forward_does_not_freeze_a_superseded_obligation_in_place():
    """DR-180's constraint, and the one this whole feature could most easily
    violate: **do not buy stability by blunting the decomposer.**

    #191 is the cautionary tale — its pre-change discrimination judge scored
    beautifully on variance precisely because it answered `caught` to 114 of 114
    defects. A carry-forward that carried everything would score perfectly on
    every stability metric here and be exactly as useless.

    The discriminating setup: the re-derivation returns a DIFFERENT obligation
    from the one on file. An implementation that carried the edited requirement
    anyway would still show the old obligation, and would pass every other test in
    this module.
    """
    first, _ = _run(_TASK)
    prior = _ledger_from(first)
    # Exact text, not a substring: "append-only" also appears in the Completion
    # bullet that demands a test of it, and that requirement is NOT being edited.
    superseded = {
        obligation.id
        for derivation in prior.derivations
        if derivation.text == "The ledger is append-only."
        for obligation in derivation.obligations
    }
    assert superseded, "fixture must have an obligation on the requirement being edited"

    parsed = parse_task_file(_EDITED)
    registry = build_registry(parsed)
    edited_id = next(r.id for r in registry if "only ever appended to" in r.text)
    counting = _CountingClient(_EDITED, alignment=[{"ground_truth": "g0", "reviewer": "r0"}])
    # The re-derivation answers with a new obligation id, as a real one would
    # after a wording change that altered what is required.
    counting.client._completion_fn = _answering(
        {edited_id: ("ob-supersedes", "the ledger is only ever appended to")},
        alignment=[{"ground_truth": "g0", "reviewer": "r0"}],
    )

    second = decompose(parsed, counting.client, prior=prior)

    ids = {obligation.id for obligation in second.obligations}
    assert "ob-supersedes" in ids
    assert not (ids & superseded), "a superseded obligation was frozen in place"
    # The requirements that did NOT change still kept theirs — the change is
    # surgical rather than a full re-derivation wearing a carry-forward label.
    assert second.requirement_map.disposition_for(edited_id).derivation == "revised"
    assert (
        sum(1 for d in second.derivations if d.derivation is Derivation.CARRIED)
        == len(registry) - 1
    )


def _answering(by_requirement: dict[str, tuple[str, str]], alignment: list[dict] | None = None):
    """A completion double answering the decompose call with chosen obligations.

    Dispatches on the response schema, because a carrying run issues two different
    kinds of call — the residue aligner and the re-derivation — and a double that
    answered both with the same payload would fail the first.
    """

    def completion_fn(**kwargs):
        from types import SimpleNamespace

        if kwargs["response_format"]["json_schema"]["name"] == "_Alignment":
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps({"matches": alignment or []}))
                    )
                ],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

        dispositions = [
            {
                "requirement_id": requirement_id,
                "disposition": "yielded",
                "obligation": {
                    "id": obligation_id,
                    "description": description,
                    "type": "functional",
                    "importance": "normal",
                    "explicit": True,
                    "observable_behavior": description,
                    "source_quote": "",
                    "required_evidence": "code_and_tests",
                    "required_evidence_reason": "",
                },
                "more_obligations": [],
            }
            for requirement_id, (obligation_id, description) in by_requirement.items()
        ]
        payload = json.dumps({"open_questions": [], "requirement_dispositions": dispositions})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    return completion_fn


def test_a_removed_requirement_is_reported_and_its_obligations_dropped():
    """Reported rather than silent: a requirement that vanished took its
    obligations with it, and a run that simply stops mentioning them is
    indistinguishable from one where they were never written."""
    first, _ = _run(_TASK)
    shortened = _TASK.replace("- The run reports its own identifier.\n", "")

    second, _ = _run(shortened, prior=_ledger_from(first))

    assert len(second.removed_requirements) == 1
    removed = second.removed_requirements[0]
    assert "reports its own identifier" in removed.text
    assert removed.obligations
    surviving = {o.id for o in second.obligations}
    assert not {o.id for o in removed.obligations} & surviving


# --- what invalidates a carried entry ----------------------------------------


def test_a_tool_change_that_leaves_the_request_unaltered_carries_everything():
    """The backwards-compatible-by-default half of the design.

    Modelled as a second run with identical determinism controls, which is what
    "the request did not move" means operationally.
    """
    first, _ = _run(_TASK)
    _, counting = _run(_TASK, prior=_ledger_from(first))

    assert counting.decompose_calls == 0


def test_a_changed_model_invalidates_every_carried_entry():
    first, _ = _run(_TASK, model="gpt-4o-mini")
    _, counting = _run(_TASK, prior=_ledger_from(first), model="another-model")

    assert counting.decompose_calls > 0


def test_a_changed_seed_invalidates_every_carried_entry():
    first, _ = _run(_TASK, seed=1)
    _, counting = _run(_TASK, prior=_ledger_from(first), seed=2)

    assert counting.decompose_calls > 0


def test_a_changed_stage_logic_version_invalidates_every_carried_entry():
    """The gap the request key cannot see.

    A code change that alters what we do with an unchanged response leaves the
    request identical, so nothing else in the system would notice it.
    """
    first, _ = _run(_TASK)
    prior = _ledger_from(first).model_copy(
        update={"stage_logic_version": DECOMPOSE_STAGE_LOGIC_VERSION + 1}
    )

    _, counting = _run(_TASK, prior=prior)

    assert counting.decompose_calls > 0


def test_a_changed_response_schema_invalidates_the_entries_derived_under_it():
    """The response schema is one of the four determinism controls `llm.py` puts
    in a request key, so an entry recorded under a different one is not an entry
    this run could reproduce.

    Modelled as a prior whose keys were computed under a different schema — which
    is exactly what "obligations derived under the previous schema" is — rather
    than by mutating the live model, so the assertion is about `plan_carry`
    comparing keys rather than about a patched class.
    """
    first, counting = _run(_TASK)
    prior = _ledger_from(first)
    under_old_schema = prior.model_copy(
        update={
            "derivations": [
                derivation.model_copy(
                    update={
                        "carry_key": carry_key(
                            system_prompt=obligations_module._SYSTEM_PROMPT,
                            response_schema={"name": "_Decomposition", "schema": {"older": True}},
                            model=counting.client.model,
                            temperature=counting.client.temperature,
                            seed=counting.client.seed,
                            stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
                            requirement_text=derivation.text,
                        )
                    }
                )
                for derivation in prior.derivations
            ]
        }
    )

    _, second = _run(_TASK, prior=under_old_schema)

    assert second.decompose_calls > 0


def test_the_carry_key_reads_the_live_response_schema():
    """The wiring behind the test above.

    That test would still pass if `decompose_carry_keys` hashed some constant
    instead of the real schema — every key would move together and nothing would
    carry, which looks like correct invalidation. This recomputes the key from
    `_Decomposition`'s actual schema and requires a match, so silently dropping
    the schema from the key fails here.
    """
    parsed = parse_task_file(_TASK)
    registry = build_registry(parsed)
    _, counting = _run(_TASK)

    keys = decompose_carry_keys(counting.client, registry)

    expected = carry_key(
        system_prompt=obligations_module._SYSTEM_PROMPT,
        response_schema={
            "name": "_Decomposition",
            "schema": inline_schema_refs(obligations_module._Decomposition.model_json_schema()),
        },
        model=counting.client.model,
        temperature=counting.client.temperature,
        seed=counting.client.seed,
        stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
        requirement_text=registry[0].text,
    )
    assert keys[registry[0].id] == expected


def test_a_changed_prompt_invalidates_the_entries_derived_under_it(monkeypatch):
    """The carry key hashes the system prompt, so editing it strands every entry
    recorded under the old one."""
    from acceptance.requirement import obligations as module

    first, _ = _run(_TASK)
    prior = _ledger_from(first)
    monkeypatch.setattr(module, "_SYSTEM_PROMPT", module._SYSTEM_PROMPT + "\nAnd one more rule.")

    _, counting = _run(_TASK, prior=prior)

    assert counting.decompose_calls > 0


def test_a_carried_entry_quoting_text_the_requirement_lost_is_rederived():
    """Caught in code rather than by trusting the model to notice.

    The obligation's source span is checked against the NEW requirement text, so
    an entry carried over from an older wording cannot survive on an id match.
    """
    derivation = RequirementDerivation(
        requirement_id="constraint-01",
        text="The ledger is append-only.",
        carry_key="k",
        derivation=Derivation.DERIVED,
        disposition=Disposition.YIELDED,
        obligations=[
            Obligation(
                id="ob",
                description="d",
                type=ObligationType.FUNCTIONAL,
                importance="normal",
                explicit=True,
                observable_behavior="b",
                source_spans=[TextSpan(text="append-only", start=0, end=11)],
            )
        ],
    )

    assert not stale_spans(derivation, "The ledger is append-only.")
    assert stale_spans(derivation, "The ledger is rewritten in place.")


def test_whitespace_only_reflow_does_not_strand_a_carried_span():
    """Task prose is hard-wrapped, so a reflowed paragraph is not a changed one —
    the same rule `_locate_quotation` already applies when deriving."""
    derivation = RequirementDerivation(
        requirement_id="constraint-01",
        text="The ledger is\n  append-only.",
        carry_key="k",
        derivation=Derivation.DERIVED,
        disposition=Disposition.YIELDED,
        obligations=[
            Obligation(
                id="ob",
                description="d",
                type=ObligationType.FUNCTIONAL,
                importance="normal",
                explicit=True,
                observable_behavior="b",
                source_spans=[TextSpan(text="ledger is append-only", start=0, end=21)],
            )
        ],
    )

    assert not stale_spans(derivation, "The ledger is\n  append-only.")


# --- the plan itself ---------------------------------------------------------


def test_the_plan_issues_calls_only_for_what_changed():
    parsed = parse_task_file(_TASK)
    registry = build_registry(parsed)
    first, counting = _run(_TASK)
    prior = _ledger_from(first)
    keys = decompose_carry_keys(counting.client, registry)

    plan = plan_carry(registry, prior, keys, counting.client)

    assert plan.issues_calls_for == set()
    assert set(plan.carried) == {requirement.id for requirement in registry}
    assert not plan.is_fresh()


def test_a_plan_with_no_prior_is_fresh():
    parsed = parse_task_file(_TASK)
    registry = build_registry(parsed)
    _, counting = _run(_TASK)
    keys = decompose_carry_keys(counting.client, registry)

    plan = plan_carry(registry, None, keys, counting.client)

    assert plan.is_fresh()
    assert plan.issues_calls_for == {requirement.id for requirement in registry}
    assert plan.removed == ()


# --- the ledger --------------------------------------------------------------


def test_the_ledger_records_what_was_carried_derived_and_revised(tmp_path):
    first, _ = _run(_TASK)
    store = LedgerStore(tmp_path / "ledger")
    entry = _ledger_from(first, run_id=new_run_id())
    store.write(entry)

    read_back = store.read(entry.run_id)

    assert read_back.derived_count() == len(first.derivations)
    assert read_back.carried_count() == 0
    assert read_back.revised_count() == 0
    assert read_back.calls_issued == first.calls_issued
    assert read_back.stage_logic_version == DECOMPOSE_STAGE_LOGIC_VERSION


def test_the_ledger_records_the_request_key_of_each_derivation():
    first, _ = _run(_TASK)
    entry = _ledger_from(first)

    assert all(derivation.carry_key for derivation in entry.derivations)
    assert len({derivation.carry_key for derivation in entry.derivations}) == len(entry.derivations)


def test_a_run_records_the_run_it_continues_as_its_parent():
    first, _ = _run(_TASK)
    second, _ = _run(_TASK, prior=_ledger_from(first, run_id="parent-run"))

    entry = build_ledger_entry(
        second, run_id="child-run", parent_run_id="parent-run", task_digest="d"
    )

    assert entry.run_id == "child-run"
    assert entry.parent_run_id == "parent-run"


def test_a_ledger_file_is_never_rewritten(tmp_path):
    """Append-only is enforced, not merely intended: a silent clobber would lose
    the history a later feature counts settling runs from."""
    store = LedgerStore(tmp_path / "ledger")
    entry = LedgerEntry(run_id="only-once")
    store.write(entry)

    try:
        store.write(entry)
    except FileExistsError:
        pass
    else:  # pragma: no cover - the assertion below reports it
        raise AssertionError("a second write to the same run id must be refused")


def test_the_ledger_is_not_written_under_the_cache(tmp_path):
    """DR-259 lost two runs to a cache clear. The ledger has to survive one."""
    from acceptance.requirement.ledger import DEFAULT_LEDGER_ROOT

    assert "cache" not in DEFAULT_LEDGER_ROOT.parts


def test_an_unknown_continued_run_is_not_an_error(tmp_path):
    """Default-to-fresh: the failure mode of the default must be lost work, never
    imported work, so an absent prior degrades to a full derivation."""
    store = LedgerStore(tmp_path / "ledger")

    assert store.read_if_present("no-such-run") is None
    assert store.read_if_present(None) is None


# --- run identifiers stay out of review state --------------------------------


def test_a_run_identifier_appears_in_no_review_state():
    """The M0.5 guard. A random id in review state makes two runs over the same
    input differ in their bytes, which is exactly why `Review` has no timestamp."""
    first, _ = _run(_TASK)
    run_id = "deadbeefcafe"
    second, _ = _run(_TASK, prior=_ledger_from(first, run_id=run_id))

    serialized = json.dumps(second.requirement_map.to_dict())
    assert run_id not in serialized
    assert run_id not in json.dumps([o.to_dict() for o in second.obligations])


def test_two_runs_over_the_same_task_and_ledger_state_are_byte_identical():
    """M0.5, restated for this feature: same task file PLUS same ledger state."""
    first, _ = _run(_TASK)
    prior = _ledger_from(first)

    left, _ = _run(_TASK, prior=prior)
    right, _ = _run(_TASK, prior=prior)

    assert json.dumps(left.to_dict(), sort_keys=True) == json.dumps(right.to_dict(), sort_keys=True)


# --- merge decisions ---------------------------------------------------------


def test_a_merge_decision_is_keyed_by_content_not_by_pair_position():
    """Pair ids are positional (`pair-0007`) and assigned before filtering, so
    carrying one obligation forward renumbers every pair after it. Keying on
    content is what makes a carried decision survive that."""

    def obligation(obligation_id: str, description: str) -> Obligation:
        return Obligation(
            id=obligation_id,
            description=description,
            type=ObligationType.FUNCTIONAL,
            importance="normal",
            explicit=True,
            observable_behavior=f"{obligation_id} holds",
        )

    left = obligation("a", "first")
    right = obligation("b", "second")

    forwards = MergeDecision.between(left, right, True)
    backwards = MergeDecision.between(right, left, True)

    assert forwards.key == backwards.key

    changed = MergeDecision.between(left, obligation("b", "second, reworded"), True)
    assert changed.key != forwards.key


def test_the_decompose_command_writes_a_ledger_entry_and_a_second_run_carries(
    tmp_path, monkeypatch
):
    """The wiring, not the helper.

    Defect injection has repeatedly found the same shape of hole in this
    repository: a helper with a good unit test that the pipeline never calls. This
    drives the real CLI entry point twice — the second naming the first — and
    asserts that the second issued no decompose call.
    """
    from acceptance import cli

    task = tmp_path / "task.md"
    task.write_text(_TASK)
    ledger = LedgerStore(tmp_path / "ledger")
    counting = _CountingClient(_TASK)
    monkeypatch.setattr(cli.RunConfig, "build_client", lambda self: counting.client)

    _, _, first_run = cli.run_decompose(str(task), cli.RunConfig(), ledger=ledger)

    assert ledger.path_for(first_run).exists()
    assert ledger.read(first_run).derived_count() > 0
    calls_after_first = counting.decompose_calls
    assert calls_after_first > 0

    _, _, second_run = cli.run_decompose(
        str(task), cli.RunConfig(), continue_from=first_run, ledger=ledger
    )

    assert counting.decompose_calls == calls_after_first
    assert ledger.read(second_run).parent_run_id == first_run
    assert ledger.read(second_run).carried_count() == len(ledger.read(first_run).derivations)


def test_the_review_pipeline_carries_forward_and_hands_back_what_it_derived(tmp_path):
    """`check` decomposes too, through `run_review`, so the same carry-forward has
    to reach it — otherwise only one of the two entry points could be continued
    and the ledger would describe half the runs.

    Driven through `run_review` itself rather than through `decompose`, because
    the defect this guards against is precisely a pipeline that never calls the
    thing its unit tests cover.
    """
    from acceptance.pipeline import run_review
    from acceptance.review_state import ChangeSet

    first, _ = _run(_TASK)
    prior = _ledger_from(first, run_id="seed-run")
    counting = _CountingClient(_TASK)
    sink: list = []

    run_review(
        task_text=_TASK,
        change_set=ChangeSet(base_revision="a", head_revision="b", files=[]),
        repo=tmp_path,
        client=counting.client,
        reviewed_revision="b",
        ledger_prior=prior,
        ledger_sink=sink,
    )

    assert counting.decompose_calls == 0
    assert len(sink) == 1
    derived, _linked = sink[0]
    assert {d.derivation for d in derived.derivations} == {Derivation.CARRIED}


def test_the_review_pipeline_leaves_no_ledger_behind_when_given_no_sink(tmp_path):
    """The benchmark runs the same pipeline over many cases and must not litter
    run records; writing is the caller's, which is why the sink is opt-in."""
    from acceptance.pipeline import run_review
    from acceptance.review_state import ChangeSet

    counting = _CountingClient(_TASK)

    run_review(
        task_text=_TASK,
        change_set=ChangeSet(base_revision="a", head_revision="b", files=[]),
        repo=tmp_path,
        client=counting.client,
        reviewed_revision="b",
    )

    assert not (tmp_path / ".acceptance").exists()


def _linkable() -> tuple[Decomposition, list[Obligation]]:
    """Two obligations under two requirements — one askable pair."""
    obligations = [
        Obligation(
            id=obligation_id,
            description=f"{obligation_id} is required",
            type=ObligationType.FUNCTIONAL,
            importance="normal",
            explicit=True,
            observable_behavior=f"{obligation_id} holds",
        )
        for obligation_id in ("alpha", "beta")
    ]
    requirements = [
        RequirementRef(
            id=requirement_id,
            section=RequirementSection.CONSTRAINT,
            ordinal=index,
            span=TextSpan(text=requirement_id, start=0, end=len(requirement_id)),
        )
        for index, requirement_id in enumerate(("constraint-01", "constraint-02"))
    ]
    dispositions = [
        RequirementDisposition(
            requirement_id=requirement.id,
            disposition=Disposition.YIELDED,
            obligation_ids=[obligation.id],
        )
        for requirement, obligation in zip(requirements, obligations, strict=True)
    ]
    return (
        Decomposition(
            obligations=obligations,
            requirement_map=RequirementMap(requirements=requirements, dispositions=dispositions),
        ),
        obligations,
    )


def _linking_client(capture: list | None = None):
    return client_dispatching(
        {
            "_Verdicts": {
                "verdicts": [
                    {"pair_id": "pair-0000", "same_requirement": False, "reason": "double"}
                ]
            }
        },
        capture=capture,
    )


def test_a_merge_decision_over_two_unchanged_obligations_is_not_asked_again():
    """`constraint-11`. Counted off the double: a re-asked pair answered the same
    way is indistinguishable in the output from one that was never asked."""
    decomposition, obligations = _linkable()
    prior = LedgerEntry(
        run_id="prior",
        merge_decisions=[MergeDecision.between(obligations[0], obligations[1], False)],
    )
    calls: list[dict] = []

    link_duplicate_obligations(decomposition, _linking_client(calls), prior=prior)

    assert [call["schema"] for call in calls] == []


def test_a_merge_decision_is_asked_again_when_either_obligation_changed():
    """`constraint-12`. The linking prompt renders both obligations, so a verdict
    about one wording is not a verdict about another."""
    decomposition, obligations = _linkable()
    stale = obligations[1].model_copy(update={"description": "beta, reworded"})
    prior = LedgerEntry(
        run_id="prior",
        merge_decisions=[MergeDecision.between(obligations[0], stale, False)],
    )
    calls: list[dict] = []

    link_duplicate_obligations(decomposition, _linking_client(calls), prior=prior)

    assert [call["schema"] for call in calls] == ["_Verdicts"]


def test_a_carried_merge_decision_still_merges():
    """Carrying a decision must carry its EFFECT, not merely skip the call — a
    confirmed pair that stopped merging would silently un-deduplicate the set."""
    decomposition, obligations = _linkable()
    prior = LedgerEntry(
        run_id="prior",
        merge_decisions=[MergeDecision.between(obligations[0], obligations[1], True)],
    )

    linked = link_duplicate_obligations(decomposition, _linking_client(), prior=prior)

    assert [o.id for o in linked.obligations] == ["alpha"]
    assert all(d.obligation_ids == ["alpha"] for d in linked.requirement_map.dispositions)


def test_the_decisions_a_run_stands_on_are_recorded_carried_and_fresh_alike():
    """So the next run inherits the whole set rather than only what this one
    happened to re-ask — otherwise a decision decays after one carry."""
    decomposition, _ = _linkable()

    linked = link_duplicate_obligations(decomposition, _linking_client())

    assert len(linked.merge_decisions) == 1
    carried_forward = link_duplicate_obligations(
        decomposition,
        _linking_client(),
        prior=LedgerEntry(run_id="p", merge_decisions=linked.merge_decisions),
    )
    assert [d.key for d in carried_forward.merge_decisions] == [
        d.key for d in linked.merge_decisions
    ]
