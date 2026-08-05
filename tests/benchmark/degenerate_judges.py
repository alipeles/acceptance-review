"""Degenerate judges for the #190 regression suite.

The suite has to fail in both directions, because each direction catches a
different bad fix. A judge that rates everything `strongly supported` must fail
it; so must a judge that rates nothing `strongly supported`. Damping the judge
until it stops moving would pass a one-directional suite while losing every real
gap the corpus records.

These two clients are those judges. Neither is a stand-in for the real one: the
corpus holds rendered reports, not transcripts, so the runs cannot be replayed
(see `benchmark/corpus.py`). What they do exercise is everything downstream of
the per-defect verdict — which is not nothing:

    `evidence/strength.py` is a deterministic reduce, not a fresh judgement.
    All named defects caught -> strongly_supported; some -> partially_supported;
    none -> nominally_supported; no mapped test at all -> unsupported.

So a judge is steered by the `would_be_caught` booleans it returns, and the
reduce, the mapping wiring, the coverage->finding derivation and the verdict all
run for real. Run 5 of the corpus is the case in point: two runs one commit
apart, byte-identical mapped tests, the same defect named in both and judged
oppositely — and because the reduce is a pure function, that single flipped
boolean produced the whole rating.

Ids are read out of the **request schema** rather than parsed from the prompt.
#163 constrains every id-bearing response field to the ids that call supplied,
by injecting them as a JSON-schema enum, so the schema is an exact, structured
statement of what this call is allowed to answer about. Parsing the prompt text
would re-derive the same list less reliably and would break whenever the prompt
is reworded.
"""

from __future__ import annotations

import json
from typing import Any

from acceptance.config import DEFAULT_MODEL
from acceptance.llm import Mode, ModelClient, TranscriptStore
from tests.support import _EMPTY_BY_SCHEMA, _fake_response

import tempfile


def _enums(schema: Any, field: str) -> list[str]:
    """Every enum offered for `field` anywhere in `schema`, de-duplicated.

    A walk rather than a fixed path: the id fields sit at different depths per
    response model (`mappings[].test_id`, `obligations[].obligation_id`), and
    pydantic may emit them behind `$defs`.
    """
    found: list[str] = []

    def walk(node: Any, key: str | None) -> None:
        if isinstance(node, dict):
            if key == field and isinstance(node.get("enum"), list):
                found.extend(v for v in node["enum"] if isinstance(v, str))
            for name, value in node.items():
                walk(value, name if name not in ("properties", "$defs", "items") else key)
        elif isinstance(node, list):
            for item in node:
                walk(item, key)

    walk(schema, None)
    return list(dict.fromkeys(found))


def _decomposition(obligations: list[dict]) -> dict:
    return {
        "obligations": [
            {
                "id": o["id"],
                "description": o["description"],
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "...",
                "source_quote": o["description"][:60],
            }
            for o in obligations
        ],
        "open_questions": [],
        "requirement_dispositions": [],
    }


def degenerate_client(obligations: list[dict], *, always_strong: bool) -> ModelClient:
    """A judge with its mind made up before it reads anything.

    `obligations` seeds the decomposition, because what is under test here is the
    evidence judgement, not the decomposer — leaving decomposition to chance
    would score a different stage than the one this suite is about.
    """

    def completion_fn(**kwargs):
        spec = kwargs["response_format"]["json_schema"]
        name, schema = spec["name"], spec["schema"]

        if name == "_Decomposition":
            return _fake_response(json.dumps(_decomposition(obligations)))

        if name == "_Mappings":
            # Map every test to every obligation the call allows. A permissive
            # judge with no mapped tests would score `unsupported` and look
            # pessimistic, so the mapping must be generous in BOTH judges for
            # the difference between them to be the verdict and nothing else.
            tests = _enums(schema, "test_id")
            allowed = _enums(schema, "obligation_ids") or [o["id"] for o in obligations]
            return _fake_response(json.dumps({
                "mappings": [
                    {"test_id": t, "obligation_ids": allowed, "rationale": "."}
                    for t in tests
                ]
            }))

        if name == "_Discrimination":
            ids = _enums(schema, "obligation_id") or [o["id"] for o in obligations]
            return _fake_response(json.dumps({
                "obligations": [
                    {
                        "obligation_id": oid,
                        "defects": [{
                            "description": "the behaviour under review is wrong",
                            "would_be_caught": always_strong,
                            "reason": "fixed verdict from a degenerate judge",
                        }],
                    }
                    for oid in ids
                ]
            }))

        if name == "_Coverage":
            ids = _enums(schema, "obligation_id") or [o["id"] for o in obligations]
            return _fake_response(json.dumps({
                "classifications": [
                    {
                        "obligation_id": oid,
                        "status": "addressed" if always_strong else "not_addressed",
                        "rationale": "fixed verdict from a degenerate judge",
                        "diff_refs": [],
                    }
                    for oid in ids
                ]
            }))

        return _fake_response(json.dumps(_EMPTY_BY_SCHEMA[name]))

    return ModelClient(
        model=DEFAULT_MODEL,
        # RECORD because an injected completion_fn is only reached on the live
        # path; a REPLAY double would find an empty store and raise. No network
        # call happens — completion_fn stands in for the provider.
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        temperature=0.0,
        completion_fn=completion_fn,
    )
