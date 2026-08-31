"""Degenerate judges for the #190 regression suite.

The suite has to fail in both directions, because each direction catches a
different bad fix. A judge that rates everything `strongly supported` must fail
it; so must a judge that rates nothing `strongly supported`. Damping the judge
until it stops moving would pass a one-directional suite while losing every real
gap the corpus records.

These two clients are those judges. Neither is a stand-in for the real one: the
corpus holds rendered reports, not transcripts, so the runs cannot be replayed
(see `benchmark/corpus.py`). What they do exercise is everything downstream of
the per-pair verdict — which is not nothing:

    `defects/support.py` is a deterministic reduce, not a fresh judgement. All
    enumerated defects killed by some test -> strongly_supported; some ->
    partially_supported; none -> nominally_supported; no candidate test at all
    -> unsupported.

So a judge is steered by the `fails` booleans it returns, and the reduce, the
prescription wiring, the coverage->finding derivation and the verdict all run for
real. Run 5 of the corpus is the case in point: two runs one commit apart,
byte-identical candidate tests, the same defect named in both and judged
oppositely — and because the reduce is a pure function, that single flipped
boolean produced the whole rating.

**The steering moved from the criterion to the pair** (#316). It used to run
through `_Mappings` (map every test to every criterion) and `_Discrimination`
(one defect per criterion, caught or not); it now runs through `_Enumeration`
(one defect per criterion) and `_PairVerdicts` (every pair, killed or not). The
suite's shape is unchanged because both stages feed a pure reduce; what changed
is which stage the boolean enters through.

Ids are read out of the **request schema** rather than parsed from the prompt.
#163 constrains every id-bearing response field to the ids that call supplied,
by injecting them as a JSON-schema enum, so the schema is an exact, structured
statement of what this call is allowed to answer about. Parsing the prompt text
would re-derive the same list less reliably and would break whenever the prompt
is reworded.
"""

from __future__ import annotations

import json
import tempfile
from typing import Any

from acceptance.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_MODEL
from acceptance.llm import Mode, ModelClient, TranscriptStore
from tests.support import (
    _EMPTY_BY_SCHEMA,
    _completed,
    _fake_response,
    constant_embedding_fn,
)


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
        # Filled in by the caller, which can see the supplied requirement ids.
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
            # Dispositions are completed by the shared helper, which attaches
            # the seeded obligations to the first requirement the call was
            # given and declines the rest. Since #204 an obligation is carried
            # inside the disposition that derived it, so it must have an owner —
            # declining every requirement would leave these orphaned and they
            # would not reach the stage this suite is actually steering.
            return _fake_response(json.dumps(_completed(_decomposition(obligations), **kwargs)))

        if name == "_Enumeration":
            # One way to fail, per criterion. The enumerator answers for one
            # criterion per call and constrains `obligation_id` to it, so the id
            # comes off the schema rather than from a fixed fixture.
            ids = _enums(schema, "obligation_id") or [o["id"] for o in obligations]
            return _fake_response(
                json.dumps(
                    {
                        "obligation_id": ids[0] if ids else "",
                        "defects": [
                            {
                                "slug": "behaviour-is-wrong",
                                "type": "other",
                                "description": "the behaviour under review is wrong",
                                "code_refs": [],
                            }
                        ],
                        "reason": "",
                    }
                )
            )

        if name == "_PairVerdicts":
            # The verdict that steers the whole suite (#316). Every defect
            # offered with every test gets the same fixed answer, so the only
            # thing separating the two judges is `always_strong`.
            #
            # Answering for EVERY offered pair matters in its own right: a pair
            # the response passes over is recorded as a judgement not obtained,
            # and my derivation refuses to classify a criterion whose defects are
            # partly unknown — so a double that skipped one would drive the run
            # `indeterminate` rather than steering the rating this suite is about.
            # Both id sets come off the schema. The pair stage constrains
            # `test_id` as well as `defect_id` (`_allowed`), unlike the mapping
            # stage this replaced, whose per-batch test ids #302 dropped from the
            # schema and left only in the prompt.
            tests = _enums(schema, "test_id")
            defect_ids = _enums(schema, "defect_id")
            verdict: dict[str, Any] = {"fails": always_strong}
            if always_strong:
                # A killing answer carries a reason and a surviving one carries
                # no `reason` key at all — the response is a union of the two
                # shapes, and sending the wrong one is a validation error.
                verdict["reason"] = "fixed verdict from a degenerate judge"
            return _fake_response(
                json.dumps(
                    {
                        "tests": [
                            {
                                "test_id": test_id,
                                "defects": [{"defect_id": did, **verdict} for did in defect_ids],
                            }
                            for test_id in tests
                        ]
                    }
                )
            )

        if name == "_Coverage":
            ids = _enums(schema, "obligation_id") or [o["id"] for o in obligations]
            return _fake_response(
                json.dumps(
                    {
                        "classifications": [
                            {
                                "obligation_id": oid,
                                "status": "addressed" if always_strong else "not_addressed",
                                "rationale": "fixed verdict from a degenerate judge",
                                "diff_refs": [],
                            }
                            for oid in ids
                        ]
                    }
                )
            )

        return _fake_response(json.dumps(_completed(_EMPTY_BY_SCHEMA[name], **kwargs)))

    return ModelClient(
        model=DEFAULT_MODEL,
        # RECORD because an injected completion_fn is only reached on the live
        # path; a REPLAY double would find an empty store and raise. No network
        # call happens — completion_fn stands in for the provider.
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        temperature=0.0,
        completion_fn=completion_fn,
        # Linking prefilters before it asks (#259), so a client driving the
        # full pipeline has to be able to embed. Neutral vectors, for the
        # reason `constant_embedding_fn` gives: a degenerate JUDGE is the
        # variable here, and the prefilter must not become a second one.
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=constant_embedding_fn,
    )
