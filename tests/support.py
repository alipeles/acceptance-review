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
import tempfile
from types import SimpleNamespace

from acceptance.config import DEFAULT_MODEL
from acceptance.llm import Mode, ModelClient, TranscriptStore
from acceptance.review_state import Obligation, ObligationType

# Sourced from the tool's own default rather than restated, so a double never
# stands in for a model the tool does not actually run. It had drifted to a
# hardcoded Anthropic string while the real default was OpenAI.
_DEFAULT_MODEL = DEFAULT_MODEL


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


def client_dispatching(
    responses_by_schema: dict,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.0,
    seed: int | None = None,
) -> ModelClient:
    """A client for multi-call hooks: each call returns the response keyed by
    its response schema's class name (e.g. `_Decomposition`, `_Coverage`).

    Determinism controls are settable because a review's provenance now reports
    the client that made the calls (#160): a double that hardcoded them would
    make provenance describe the double instead of the run under test.
    """

    def completion_fn(**kwargs):
        schema_name = kwargs["response_format"]["json_schema"]["name"]
        return _fake_response(json.dumps(responses_by_schema[schema_name]))

    return ModelClient(
        model=model,
        # RECORD, always: an injected completion_fn is only ever reached on the
        # live path, so a REPLAY double would find an empty store and raise.
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        temperature=temperature,
        seed=seed,
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


def client_finding_nothing(
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.0,
    seed: int | None = None,
) -> ModelClient:
    """A client whose every pipeline call returns an empty result — the
    checker runs end to end and reports nothing found."""
    return client_dispatching(
        _EMPTY_BY_SCHEMA, model=model, temperature=temperature, seed=seed
    )


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
APPROVED_CORPUS_MODELS = ("openai/gpt-5.4-mini", "anthropic/claude-sonnet-5")


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
    return _corpus_config(
        model, Mode.RECORD if recording_enabled() else Mode.REPLAY
    ).build_client()


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
