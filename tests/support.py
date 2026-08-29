"""Shared test doubles for schema-constrained model calls.

Every capability that calls `ModelClient.complete` (decomposition, coverage
classification, unrequested-change detection, and their benchmark hooks) is
tested the same way, per the replay-first invariant: inject a fake
`completion_fn` that returns a fixed, hand-authored response and never
touches the network, backed by an isolated ephemeral `TranscriptStore` so
recording never leaks into the repo's real `.acceptance/` cache.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import tempfile
from types import SimpleNamespace

from acceptance.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_MODEL
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import Obligation, ObligationType

# Sourced from the tool's own default rather than restated, so a double never
# stands in for a model the tool does not actually run. It had drifted to a
# hardcoded Anthropic string while the real default was OpenAI.
_DEFAULT_MODEL = DEFAULT_MODEL


def constant_embedding_fn(**kwargs) -> dict:
    """The neutral embedding double: every input gets the SAME vector.

    Neutral on purpose. Every distance is then 0, so #259's prefilter admits
    every pair and a test that is not about the prefilter exercises exactly the
    sweep it did before the prefilter existed. A double returning arbitrary or
    hash-derived vectors would put most pairs far apart and silently shrink the
    sweep under every unrelated test — turning them into tests of the filter
    rather than of what they are about.

    A test that IS about the filter injects its own `embedding_fn`; see
    `embedding_fn_for`.
    """
    return {"data": [{"embedding": [1.0, 0.0, 0.0]} for _ in kwargs["input"]]}


def embedding_fn_for(vectors_by_text: dict[str, list[float]], default: list[float] | None = None):
    """An embedding double answering from a text -> vector table.

    Keyed by the exact string embedded, which for obligations is
    `linking.embedding_text` — description and observable behavior joined by a
    space — so a test states the geometry it wants rather than reverse-
    engineering it from a hash.
    """

    def embedding_fn(**kwargs):
        data = []
        for text in kwargs["input"]:
            vector = vectors_by_text.get(text, default)
            if vector is None:
                raise AssertionError(f"no vector supplied for embedded text: {text!r}")
            data.append({"embedding": list(vector)})
        return {"data": data}

    return embedding_fn


def _fake_response(content: str, usage: dict | None = None) -> SimpleNamespace:
    figures = (
        usage
        if usage is not None
        else {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        }
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(**figures),
    )


def _candidate_tests(**kwargs) -> list[str]:
    """The test ids a mapping call is asking about, read off its prompt.

    `mapping.py::_tests_block` writes one `### <test_id>` heading per candidate
    under `## Candidate tests`. Since #302 dropped mapping's per-batch `test_id`
    enum that is the only place they appear — and it is where the real model
    reads them, so a double reading them here answers the same question it does.
    Decompose and linking keep their enums, so `_supplied_enum` still serves
    those.
    """
    for message in kwargs.get("messages") or []:
        content = message.get("content", "")
        if "## Candidate tests" not in content:
            continue
        tail = content.split("## Candidate tests", 1)[1]
        return [
            line[4:].strip()
            for line in tail.splitlines()
            if line.startswith("### ") and line[4:].strip()
        ]
    return []


def _pairs_asked_about(**kwargs) -> list[str]:
    """The pair ids a linking call is asking about, read off its prompt.

    `linking.py::_user_prompt` writes each as `[<pair_id>]` on its own line.
    Linking keeps its `pair_id` enum, so this is not about the schema — it is
    that #302 made linking record a pair its answer passed over, so a double
    must answer for every pair rather than returning a bare `[]`.
    """
    found: list[str] = []
    for message in kwargs.get("messages") or []:
        for line in message.get("content", "").splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                pair_id = stripped[1:-1]
                if pair_id and pair_id not in found:
                    found.append(pair_id)
    return found


def _supplied_enum(field: str, **kwargs) -> list[str]:
    """The ids a call supplied for `field`, read back off the schema it sent.

    `constrain` restricts each id field to a `Literal` of the ids that call
    actually offered, so the enum in the outgoing schema is the work list. That
    lets a double answer a call completely without being told the fixture's ids
    separately, and keeps it honest when they change.
    """
    schema = kwargs["response_format"]["json_schema"]["schema"]
    found: list[str] = []

    def walk(node, key=None):
        if isinstance(node, dict):
            if key == field and isinstance(node.get("enum"), list):
                found.extend(v for v in node["enum"] if v not in found)
            for name, value in node.items():
                walk(value, name if name not in ("properties", "$defs", "items") else key)
        elif isinstance(node, list):
            for item in node:
                walk(item, key)

    walk(schema)
    return found


def declining_dispositions(reason: str = "not exercised by this fixture", **kwargs) -> list[dict]:
    """One `no_obligation` disposition per supplied requirement.

    The honest "found nothing" for decomposition since M1.2.r2. A response
    disposing nothing is malformed and raises, so a double that returns an
    empty list is not a no-op checker — it is a broken one.
    """
    return [
        {"requirement_id": requirement_id, "disposition": "no_obligation", "reason": reason}
        for requirement_id in _supplied_enum("requirement_id", **kwargs)
    ]


def _nest_obligations(response: dict) -> dict:
    """Translate the flat-obligations shape into the nested one (#204).

    Fixtures read better as "here are the obligations, here is who claimed
    them", so they keep writing that. The wire shape no longer has a flat list:
    each obligation is carried inside the disposition that derived it, which is
    what makes linking unrepresentable rather than merely forbidden.

    This adapter enforces the same invariant it translates for. A fixture naming
    one obligation from two dispositions RAISES here, because such a response
    can no longer be built — a test that could still express linking would be
    asserting against a shape the model is never offered.
    """
    # Only a DECOMPOSITION response. `_Discrimination` also has a top-level
    # `obligations` key, with an entirely different shape, and must be left
    # alone — the marker is `requirement_dispositions`, which only decomposition
    # carries.
    if "obligations" not in response or "requirement_dispositions" not in response:
        return response

    # Consumed positionally, not looked up in a dict: a fixture may legitimately
    # mint the same id twice (that is what `_unique` renaming is for), and a
    # dict would silently collapse the pair.
    #
    # `required_evidence` (#266) is a required field, so a fixture written
    # before it existed would stop parsing. Defaulted to requiring both kinds —
    # the same safe default the stage itself applies — because a fixture silent
    # about which evidence is owed is not narrowing anything. A fixture that IS
    # about the narrowing states it, and is left alone.
    remaining = [
        {"required_evidence": "code_and_tests", "required_evidence_reason": "", **obligation}
        for obligation in response["obligations"]
    ]
    consumed_by: dict[str, str] = {}
    dispositions = []
    for entry in response.get("requirement_dispositions", []):
        if entry.get("disposition") != "yielded":
            dispositions.append(entry)
            continue
        ids = [entry["obligation_id"], *entry.get("more_obligation_ids", [])]
        carried = []
        for oid in ids:
            match = next((i for i, o in enumerate(remaining) if o["id"] == oid), None)
            if match is None:
                if oid in consumed_by:
                    raise AssertionError(
                        f"fixture links obligation {oid!r} from both "
                        f"{consumed_by[oid]!r} and {entry['requirement_id']!r}. Derivation "
                        f"carries obligations inside the disposition that owns them, so one "
                        f"obligation cannot be named by two requirements — give each "
                        f"requirement its own (#204, DR-204)."
                    )
                raise AssertionError(
                    f"fixture disposes {entry['requirement_id']!r} as 'yielded' naming "
                    f"obligation id {oid!r}, which the response does not define"
                )
            carried.append(remaining.pop(match))
            consumed_by[oid] = entry["requirement_id"]
        rest = {k: v for k, v in entry.items() if k not in ("obligation_id", "more_obligation_ids")}
        dispositions.append({**rest, "obligation": carried[0], "more_obligations": carried[1:]})

    return {
        k: v
        for k, v in {**response, "requirement_dispositions": dispositions}.items()
        if k != "obligations"
    }


_REGISTRY_LINE = re.compile(r"^\[([^\]]+)\] \(([^)]+)\) \[(ANSWER FOR THIS|context only)\] (.*)$")


def _registry_from_prompt(**kwargs) -> list[dict]:
    """The requirement listing a decompose call carries, read back off its prompt.

    `_user_prompt` renders every requirement as
    `[id] (section) [ANSWER FOR THIS|context only] <text>`, wrapped across
    following lines where the source is — task prose is hard-wrapped, so a
    requirement is not always one line.

    Needed because since #317 a call answers for ONE requirement, so a fixture
    that lists the whole mandate's obligations has to be split across the calls
    rather than repeated in each; repeating them would multiply the set and
    `_unique` would rename the copies.
    """
    for message in reversed(kwargs.get("messages") or []):
        lines = message.get("content", "").splitlines()
        found: list[dict] = []
        for line in lines:
            match = _REGISTRY_LINE.match(line)
            if match:
                found.append(
                    {
                        "id": match.group(1),
                        "section": match.group(2),
                        "answering": match.group(3) == "ANSWER FOR THIS",
                        "text": match.group(4),
                    }
                )
            elif found and line.strip():
                found[-1]["text"] += "\n" + line
            elif found:
                break
        if found:
            return found
    return []


def _quotes_this_requirement(obligation: dict, requirement_text: str) -> bool:
    """Whether this obligation's quotation lies in the requirement being asked about.

    Whitespace-insensitive, like the stage's own `locate_within`: task prose is
    hard-wrapped, so an exact-substring test would answer no for a property of
    the file's line width.
    """
    quote = " ".join(str(obligation.get("source_quote", "")).split())
    return bool(quote) and quote in " ".join(requirement_text.split())


def _schema_name(**kwargs) -> str:
    return kwargs.get("response_format", {}).get("json_schema", {}).get("name", "")


def _one_disposition(response: dict, **kwargs) -> dict:
    """Translate the fixture's disposition LIST into the one entry this call wants.

    Since #317 a decompose call is asked about one requirement and returns one
    disposition, so the wire shape has no list. Fixtures keep writing the whole
    mandate's dispositions in one dict — that is how they read — and this picks
    out the entry for the requirement each call actually asks about. A fixture
    listing five requirements is therefore now answering five calls with the same
    dict, which is exactly what the stage does.

    A requirement the fixture says nothing about declines, as it did when one
    call answered for a whole batch and the fixture named only some of them.
    """
    if "requirement_dispositions" not in response:
        return response
    schema = kwargs.get("response_format", {}).get("json_schema", {}).get("schema", {})
    if "requirement_disposition" not in schema.get("properties", {}):
        return response
    entries = response["requirement_dispositions"]
    supplied = _supplied_enum("requirement_id", **kwargs)
    if len(supplied) != 1:
        # An UNCONSTRAINED `_Decomposition` — a harness-level test calling
        # `complete` directly rather than through the stage, so there is no
        # requirement to pick by. Any well-formed single disposition will do.
        return {
            **{k: v for k, v in response.items() if k != "requirement_dispositions"},
            "requirement_disposition": entries[0]
            if entries
            else {
                "requirement_id": "requirement-01",
                "disposition": "no_obligation",
                "reason": "no obligation, deliberately (test double)",
            },
        }
    wanted = supplied[0]
    match = next((e for e in entries if e.get("requirement_id") == wanted), None)
    if match is None and "-span-" in wanted:
        # A call authoring obligations for an uncovered span of the summary. The
        # span's id is `<summary id>-span-NN` and no fixture writes one, so the
        # summary's own entry answers for it: a fixture saying "task-01 yields
        # this obligation" keeps meaning that once the summary is accounted for
        # span by span.
        parent = wanted.split("-span-")[0]
        match = next((e for e in entries if e.get("requirement_id") == parent), None)
        if match is not None:
            match = {**match, "requirement_id": wanted}
    chosen = match or {
        "requirement_id": wanted,
        "disposition": "no_obligation",
        "reason": "no obligation, deliberately (test double)",
    }
    rest = {k: v for k, v in response.items() if k != "requirement_dispositions"}

    # An open question goes out on the call whose disposition names it, and on no
    # other. Repeating the fixture's whole question list per call would mint the
    # same question once per requirement, with `_unique` renaming the copies —
    # and the disposition would then name a different question from the one the
    # rest of the pipeline resolved.
    def _names(entry: dict) -> set[str]:
        ids = {entry["open_question_id"]} if entry.get("open_question_id") else set()
        return ids | set(entry.get("more_open_question_ids") or [])

    named_here = _names(chosen)
    named_anywhere = set().union(*(_names(entry) for entry in entries)) if entries else set()
    # A question no disposition names belongs to a fixture that is about the
    # questions rather than about which requirement raised them. It goes out on
    # the first requirement the mandate offers — the same rule the homeless
    # obligations follow, and for the same reason: deterministic, and once.
    listed = _registry_from_prompt(**kwargs)
    first_answerable = next((r["id"] for r in listed if r["section"] != "task"), None)
    rest["open_questions"] = [
        question
        for question in (rest.get("open_questions") or [])
        if question["id"] in named_here
        or (question["id"] not in named_anywhere and wanted == first_answerable)
    ]
    return {**rest, "requirement_disposition": chosen}


def covered_summary(**kwargs) -> dict:
    """The neutral answer for the summary pass (#317): one span, already required.

    Neutral in the same sense as `constant_embedding_fn`. The summary step exists
    to decide whether the bullets already require what the opening paragraph
    says, and for a fixture that is not about it the answer that changes nothing
    is "yes" — the summary yields no obligation of its own and no further call is
    made. Answering `uncovered` would instead have every unrelated test author an
    extra obligation from a span.

    A test that IS about the summary pass supplies its own spans and verdicts.
    """
    nearest = _supplied_enum("nearest", **kwargs)
    return {
        "spans": [_summary_text(**kwargs)],
        "span_dispositions": [
            {
                "span_index": 0,
                "nearest": nearest[:1],
                "counterexample": "none",
                "disposition": "covered",
            }
        ],
    }


def uncovered_summary(spans: list[str]) -> dict:
    """A summary pass answer holding each named span uncovered.

    For a test that wants the opening summary to yield obligations of its own.
    Each span must appear in the summary verbatim, and each one then gets a call
    of its own asked about that span alone — which `_one_disposition` answers
    from the fixture's entry for the summary.
    """
    return {
        "spans": list(spans),
        "span_dispositions": [
            {
                "span_index": index,
                "nearest": [],
                "counterexample": (
                    "a change satisfying every listed obligation without this property"
                ),
                "disposition": "uncovered",
            }
            for index in range(len(spans))
        ],
    }


#: A fixture's `_SummarySpans` response meaning "the whole opening paragraph is
#: uncovered", for a mandate whose text the fixture does not have to hand — the
#: benchmark archetypes, whose task files are a Task paragraph and nothing else.
#: With the covered answer such a mandate yields no obligation at all, because
#: there are no bullets for the ordinary decomposer to answer about.
WHOLE_SUMMARY_UNCOVERED = {"__whole_summary_uncovered__": True}


def _summary_text(**kwargs) -> str:
    """The summary as the call presents it, read back off the prompt.

    A span must be a substring of the summary or the stage rejects the whole
    answer, so a double cannot invent one. `summary.py::_user_prompt` puts the
    summary last, under a `The summary:` line.
    """
    for message in reversed(kwargs.get("messages") or []):
        content = message.get("content", "")
        if "The summary:" in content:
            return content.split("The summary:", 1)[1].strip()
    return ""


def _completed(response: dict, **kwargs) -> dict:
    """Fill an empty response list from the ids the call supplied.

    Two stages reject an under-filled answer rather than absorbing it, so `[]`
    is not the neutral stand-in it used to be — a double returning one is not a
    no-op checker but a broken one:

    - decomposition (M1.2.r2, #217) — a response disposing nothing does not parse;
    - recommendations (#218) — a weak obligation with no recommendation is an
      error, not an absence.

    Rather than make every fixture restate ids it never cared about, the doubles
    complete both. A test that IS about either names them explicitly, and a
    non-empty list is left alone.
    """
    if not isinstance(response, dict):
        return response
    # The summary pass has its own schema, and a fixture written for the
    # decomposer says nothing it can use. Answered here so an unrelated test does
    # not have to know the stage exists.
    if _schema_name(**kwargs) == "_SummarySpans" and "span_dispositions" not in response:
        if response.get("__whole_summary_uncovered__"):
            return uncovered_summary([_summary_text(**kwargs)])
        return covered_summary(**kwargs)
    # Defect enumeration asks about ONE criterion per call and constrains
    # `obligation_id` to it, so a fixed fixture cannot name it. Filled from the
    # call's own enum, exactly as the recommendation branch below does — a blank
    # would otherwise be scanned as an id the call never supplied and file an
    # unusable-answer finding in every unrelated test (#313).
    if _schema_name(**kwargs) == "_Enumeration" and not response.get("obligation_id"):
        supplied = _supplied_enum("obligation_id", **kwargs)
        return {**response, "obligation_id": supplied[0] if supplied else ""}
    if response.get("requirement_dispositions") == []:
        supplied = _supplied_enum("requirement_id", **kwargs)
        obligations = response.get("obligations") or []
        # Since #204 an obligation is carried inside the disposition that
        # derived it, so it cannot be an orphan; since #317 a call answers for
        # one requirement, so the fixture's obligations have to be SPLIT across
        # the calls rather than repeated in each — repeating them would multiply
        # the set and `_unique` would rename the copies.
        #
        # Split by quotation: an obligation whose `source_quote` lies in the
        # requirement this call asks about belongs to this call, which is the
        # same rule the stage itself applies. A fixture whose quotations do not
        # land anywhere gets its obligations on the first requirement offered, so
        # a test that is about the obligations rather than about ownership still
        # sees all of them.
        listed = _registry_from_prompt(**kwargs)
        answering = next((r for r in listed if r["answering"]), None)
        answering_text = answering["text"] if answering else ""
        mine = [o for o in obligations if _quotes_this_requirement(o, answering_text)]
        # An obligation whose quotation lands in NO requirement belongs to a
        # fixture that is about the obligations rather than about ownership. It
        # goes to the first requirement the mandate offers, which is where it
        # went when one call answered for the whole batch — deterministic, and
        # the same requirement on every call, so it is emitted exactly once.
        homeless = [
            o
            for o in obligations
            if not any(_quotes_this_requirement(o, r["text"]) for r in listed)
        ]
        first_answerable = next((r["id"] for r in listed if r["section"] != "task"), None)
        if answering is not None and answering["id"] == first_answerable:
            mine = mine + [o for o in homeless if o not in mine]
        dispositions = []
        if supplied and mine:
            dispositions.append(
                {
                    "requirement_id": supplied[0],
                    "disposition": "yielded",
                    "obligation_id": mine[0]["id"],
                    "more_obligation_ids": [o["id"] for o in mine[1:]],
                }
            )
            supplied = supplied[1:]
        dispositions.extend(
            {
                "requirement_id": rid,
                "disposition": "no_obligation",
                "reason": "no obligation, deliberately (test double)",
            }
            for rid in supplied
        )
        # Only this call's obligations are offered for nesting, so an obligation
        # another call owns is not consumed here.
        return _one_disposition(
            _nest_obligations(
                {**response, "obligations": mine, "requirement_dispositions": dispositions}
            ),
            **kwargs,
        )
    if response.get("mappings") == []:
        # Since #302 a candidate test the response passes over is recorded as a
        # judgment not obtained, and drives the run's unmapped obligations to
        # `indeterminate`. So `[]` no longer means "these tests evidence
        # nothing" — that has to be SAID, one entry per test with an empty
        # `obligation_ids`, which is what the stage's own prompt asks for and
        # what a real response does. A double returning a bare `[]` against a
        # non-empty batch is now the broken kind, not the neutral kind.
        return {
            **response,
            "mappings": [
                {"test_id": test_id, "obligation_ids": [], "rationale": "test double"}
                for test_id in _candidate_tests(**kwargs)
            ],
        }
    if response.get("verdicts") == []:
        # Same reason: #302 records a pair the response passed over, so "none of
        # these pairs are the same requirement" has to be stated per pair.
        return {
            **response,
            "verdicts": [
                {"pair_id": pair_id, "same_requirement": False, "reason": "test double"}
                for pair_id in _pairs_asked_about(**kwargs)
            ],
        }
    if response.get("recommendations") == []:
        return {
            **response,
            "recommendations": [
                {
                    "obligation_id": obligation_id,
                    "required_inputs": "inputs where the defect changes the outcome",
                    "boundary_conditions": "none",
                    "expected_output": "the criterion holds",
                    "required_assertions": ["asserts the criterion"],
                    "plausible_defect": "the criterion is not met",
                    "repo_conventions": "follow the existing test module",
                }
                for obligation_id in _supplied_enum("obligation_id", **kwargs)
            ],
        }
    return _one_disposition(_nest_obligations(response), **kwargs)


def client_returning(
    response: dict,
    model: str = _DEFAULT_MODEL,
    embedding_fn=None,
    summary: dict | None = None,
) -> ModelClient:
    """A client whose every call returns the same fixed response.

    A `requirement_dispositions` of `[]` is completed from the requirements the
    call supplied, so a test about obligations does not have to restate the
    fixture's whole requirement list to stay well-formed. It is a convenience
    for tests that are not about dispositions; a test that IS about them names
    them explicitly and this leaves it alone.

    `summary` answers the summary pass (#317), which has its own schema and can
    take nothing from a decomposer fixture. Left unset it is `covered_summary` —
    the opening paragraph states nothing the bullets do not — so an unrelated
    test is unaffected by the step existing. `uncovered_summary` is the other
    side, for a test that wants the summary to yield.
    """

    def completion_fn(**kwargs):
        chosen = response
        if _schema_name(**kwargs) == "_SummarySpans":
            chosen = summary if summary is not None else {}
        return _fake_response(json.dumps(_completed(chosen, **kwargs)))

    return ModelClient(
        model=model,
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=embedding_fn or constant_embedding_fn,
    )


def model_client_with(completion_fn, model: str = _DEFAULT_MODEL, embedding_fn=None) -> ModelClient:
    """A client backed by a caller-supplied `completion_fn`.

    For tests that need to vary the answer per call — which partitioned stages
    do by construction, since a single fixed response cannot tell "every batch
    was asked" from "one batch was".
    """
    return ModelClient(
        model=model,
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=embedding_fn or constant_embedding_fn,
    )


def client_answering_per_call(
    responder, model: str = _DEFAULT_MODEL, embedding_fn=None
) -> tuple[ModelClient, list[dict]]:
    """A client that answers each call from the prompt it was given.

    Returns the client and a list that accumulates one entry per call —
    `{"prompt": ..., "response": ...}` — so a test can assert what was asked as
    well as what came back. Needed for partitioned stages, where a single fixed
    response cannot distinguish "every batch was asked" from "one batch was".
    """
    calls: list[dict] = []

    def completion_fn(**kwargs):
        prompt = "\n".join(message["content"] for message in kwargs["messages"])
        response = responder(prompt)
        calls.append({"prompt": prompt, "response": response})
        return _fake_response(json.dumps(response))

    client = ModelClient(
        model=model,
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=embedding_fn or constant_embedding_fn,
    )
    return client, calls


def client_capturing_schemas(
    response: dict, model: str = _DEFAULT_MODEL, embedding_fn=None
) -> tuple[ModelClient, list[dict]]:
    """A client returning a fixed response, recording the schema each call sent.

    The response schema is now part of what a stage produces, not just plumbing:
    the ids a call supplies are constrained there, so "the constraint reached the
    provider" is only assertable by looking at the schema actually sent (#163).
    """
    schemas: list[dict] = []

    def completion_fn(**kwargs):
        schemas.append(kwargs["response_format"]["json_schema"]["schema"])
        return _fake_response(json.dumps(response))

    client = ModelClient(
        model=model,
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=embedding_fn or constant_embedding_fn,
    )
    return client, schemas


def make_obligation(obligation_id: str, description: str, typ: ObligationType) -> Obligation:
    """A minimal but valid Obligation for tests that don't exercise its
    importance/explicitness/observable-behavior fields directly."""
    return Obligation(
        id=obligation_id,
        description=description,
        type=typ,
        importance="critical",
        explicit=True,
        observable_behavior="...",
    )


def client_dispatching(
    responses_by_schema: dict,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.0,
    seed: int | None = None,
    embedding_fn=None,
    capture: list | None = None,
    usage: dict | None = None,
) -> ModelClient:
    """A client for multi-call hooks: each call returns the response keyed by
    its response schema's class name (e.g. `_Decomposition`, `_Coverage`).

    Determinism controls are settable because a review's provenance now reports
    the client that made the calls (#160): a double that hardcoded them would
    make provenance describe the double instead of the run under test.

    Pass `capture` to collect each call as `{"schema", "prompt"}`. A test about
    which obligations a stage was GIVEN cannot be written against the response —
    an obligation that was offered and then discarded produces the same output
    as one that was never offered, and those are different behaviours (#266).

    Pass `usage` to control what each call reports having cost. Only a test
    about cost accounting needs it; the default stands in for a provider whose
    figures nobody is asserting on (#264).
    """

    # Defaults underneath, so a test names only the stages it is about. Adding a
    # pipeline stage would otherwise break every multi-call test at once, which
    # is a maintenance cost with no diagnostic value: a coverage test has no
    # opinion about obligation linking and should not have to state one.
    dispatch = {**_EMPTY_BY_SCHEMA, **responses_by_schema}

    def completion_fn(**kwargs):
        schema_name = kwargs["response_format"]["json_schema"]["name"]
        if capture is not None:
            capture.append(
                {
                    "schema": schema_name,
                    "prompt": "\n".join(m["content"] for m in kwargs["messages"]),
                    # The messages as sent, not just their text. A test about
                    # what a stage was GIVEN can use `prompt`; a test about how
                    # the request is ORDERED needs the boundaries, which the
                    # join destroys (#265).
                    "messages": [dict(m) for m in kwargs["messages"]],
                }
            )
        return _fake_response(json.dumps(_completed(dispatch[schema_name], **kwargs)), usage=usage)

    return ModelClient(
        model=model,
        # RECORD, always: an injected completion_fn is only ever reached on the
        # live path, so a REPLAY double would find an empty store and raise.
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        temperature=temperature,
        seed=seed,
        completion_fn=completion_fn,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=embedding_fn or constant_embedding_fn,
    )


# An empty result per pipeline response schema (schemas are strict, so each
# needs exactly its own field). A client returning these finds nothing at every
# step — the "no-op checker" stand-in for tests that exercise the harness loop
# (fixture -> case -> run -> score) or CLI plumbing rather than any model
# judgment. Since M7.4's shared pipeline, `run_check` makes real model calls, so
# these tests must inject a client instead of relying on an empty skeleton.
_EMPTY_BY_SCHEMA = {
    "_Decomposition": {
        "obligations": [],
        "open_questions": [],
        "requirement_dispositions": [],
    },
    # The summary pass (#317). Filled in by `covered_summary` from the request,
    # because a span must be a substring of the summary the call was shown and no
    # fixed dict can satisfy that. "Already required" is the neutral answer: the
    # summary yields nothing of its own and no further call is made.
    "_SummarySpans": {},
    # Every pair comes back "not the same requirement", so the de-duplication
    # pass runs its full sweep and merges nothing — a test's derived obligations
    # reach the rest of the pipeline exactly as it wrote them (#144).
    #
    # An empty `verdicts` list would do the same thing here, and is what the
    # other stages' defaults look like. It is spelled this way because the
    # completion helper fills a supplied-id enum when it sees one, so the double
    # answers the pairs it was actually given rather than none of them.
    "_Verdicts": {"verdicts": []},
    # Defect enumeration (#313). `obligation_id` is filled in by the completion
    # helper from the supplied-id enum, so the double answers about the criterion
    # it was actually asked about. No defects and a reason for the empty set,
    # which is a valid answer rather than a degenerate one — and the stage is
    # advisory, so a test with no opinion about defects gets a review whose
    # verdict and ratings are what they were before this stage existed.
    "_Enumeration": {
        "obligation_id": "",
        "defects": [],
        "reason": "No defects were enumerated by this test's model double.",
    },
    "_Mappings": {"mappings": []},
    "_Discrimination": {"discriminations": []},
    "_Coverage": {"classifications": []},
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def client_finding_nothing(
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.0,
    seed: int | None = None,
) -> ModelClient:
    """A client whose every pipeline call returns an empty result — the
    checker runs end to end and reports nothing found."""
    return client_dispatching(_EMPTY_BY_SCHEMA, model=model, temperature=temperature, seed=seed)


# --- Recorded prompt-quality corpus (#146) ---------------------------------
#
# The helpers above inject a hand-authored response: the test supplies the very
# answer the code is supposed to obtain, so it verifies plumbing and says
# nothing about whether the PROMPT elicits that answer. Editing a prompt cannot
# fail such a test (#138).
#
# `recorded_client` closes that gap. It replays a committed corpus of REAL model
# responses, so an assertion over its output is an assertion about real model
# behaviour — while still replaying byte-identically, with no API key and no
# live call in CI.
#
# The enforcement is free: `request_key` hashes the whole request, including the
# system prompt, so EDITING A PROMPT IS A CACHE MISS. The test then fails with
# `TranscriptNotFoundError`, which is exactly the signal that a prompt changed
# and has not been re-verified.
#
# To re-record after an intentional prompt change:
#     ACCEPTANCE_RECORD=1 pytest tests/prompts -q
# That makes live calls AND runs the assertions against the real responses, so
# a prompt that degrades quality fails instead of silently re-recording.
#
# Recorded ONLY against archetype fixtures, never against this repo's own
# dogfood runs: a transcript embeds the full request, so recording a dogfood run
# would commit our own diffs and task text into test fixtures.
RECORDED_TRANSCRIPTS = pathlib.Path(__file__).parent / "fixtures" / "transcripts"

# Models the corpus is allowed to hold recordings for.
#
# The tool routes through LiteLLM so the model can be swapped to compare quality
# and cost (M0.4), and that claim needs the same recorded evidence as every
# other capability — otherwise provider-agnosticism is the one thing asserted
# only by hand. So the corpus is deliberately multi-model rather than pinned to
# the single production model.
#
# It stays a CLOSED set, not "any model": a recording's whole value is that it
# reflects a model the tool actually runs, and an unlisted model in the corpus
# means something recorded that should not have. Add a model here deliberately.
#
# `openai/gpt-5.4` is here because a STAGE may name its own model (#317), not
# because the run's default moved: the summary step runs on it, so a corpus
# recorded through `decompose` necessarily holds recordings against it.
APPROVED_CORPUS_MODELS = (
    "openai/gpt-5.4-mini",
    "openai/gpt-5.4",
    "anthropic/claude-sonnet-5",
)


def recording_enabled() -> bool:
    return os.environ.get("ACCEPTANCE_RECORD") == "1"


def replaying_client(model: str | None = None, completion_fn=None) -> ModelClient:
    """A client pinned to REPLAY against the committed corpus, whatever the
    environment says.

    For tests that deliberately MISS the corpus (e.g. proving a prompt edit is
    detected). Such a test must never be able to record: under RECORD a miss
    becomes a live call that writes a junk transcript into the committed
    fixtures — and a stray entry can satisfy a lookup that should have missed,
    silently disabling the very detection being tested. Use this rather than
    relying on an env var being unset."""
    return _corpus_config(model, Mode.REPLAY).build_client(completion_fn)


def recorded_client(model: str | None = None) -> ModelClient:
    """Replay the committed corpus of real model responses (record with
    ACCEPTANCE_RECORD=1). A missing transcript means the prompt changed."""
    return _corpus_config(model, Mode.RECORD if recording_enabled() else Mode.REPLAY).build_client()


def empty_corpus_client(root, model: str | None = None) -> ModelClient:
    """Replay against an EMPTY store, under the same determinism controls as
    the real corpus — so a lookup differs from `replaying_client()` only in the
    backing store, and a miss proves the corpus is load-bearing rather than
    proving the controls happened to differ."""
    config = _corpus_config(model, Mode.REPLAY)
    return config.model_copy(update={"transcript_root": root}).build_client()


def _corpus_config(model: str | None, mode: Mode):
    """Build the corpus client from `RunConfig` rather than constructing a
    `ModelClient` by hand, so it inherits EVERY production determinism control
    — model, temperature, and seed — from one source of truth.

    Constructing directly silently dropped the seed, so the corpus would not
    have reflected how the tool actually runs (#154). The same argument as
    recording against the production model applies to the controls that shape
    the response."""
    from acceptance.config import DEFAULT_MODEL, RunConfig

    return RunConfig(
        model=model or DEFAULT_MODEL,
        mode=mode,
        transcript_root=RECORDED_TRANSCRIPTS,
    )
