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
