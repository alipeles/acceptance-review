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
import tempfile
from types import SimpleNamespace

from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import Obligation, ObligationType

_DEFAULT_MODEL = "anthropic/claude-sonnet-5"


def _fake_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def client_returning(response: dict, model: str = _DEFAULT_MODEL) -> ModelClient:
    """A client whose every call returns the same fixed response."""

    def completion_fn(**kwargs):
        return _fake_response(json.dumps(response))

    return ModelClient(
        model=model,
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
    )


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


def client_dispatching(responses_by_schema: dict, model: str = _DEFAULT_MODEL) -> ModelClient:
    """A client for multi-call hooks: each call returns the response keyed by
    its response schema's class name (e.g. `_Decomposition`, `_Coverage`)."""

    def completion_fn(**kwargs):
        schema_name = kwargs["response_format"]["json_schema"]["name"]
        return _fake_response(json.dumps(responses_by_schema[schema_name]))

    return ModelClient(
        model=model,
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        completion_fn=completion_fn,
    )


# An empty result per pipeline response schema (schemas are strict, so each
# needs exactly its own field). A client returning these finds nothing at every
# step — the "no-op checker" stand-in for tests that exercise the harness loop
# (fixture -> case -> run -> score) or CLI plumbing rather than any model
# judgment. Since M7.4's shared pipeline, `run_check` makes real model calls, so
# these tests must inject a client instead of relying on an empty skeleton.
_EMPTY_BY_SCHEMA = {
    "_Decomposition": {"obligations": [], "open_questions": []},
    "_Mappings": {"mappings": []},
    "_Discrimination": {"discriminations": []},
    "_Coverage": {"classifications": []},
    "_Detections": {"unrequested_changes": []},
    "_Judgments": {"resolutions": []},
    "_Recommendations": {"recommendations": []},
    "_Mismatches": {"mismatches": []},
}


def client_finding_nothing(model: str = _DEFAULT_MODEL) -> ModelClient:
    """A client whose every pipeline call returns an empty result — the
    checker runs end to end and reports nothing found."""
    return client_dispatching(_EMPTY_BY_SCHEMA, model=model)
