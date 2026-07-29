"""LLM-orchestration harness (M0.4, plan §3.2 "LLM orchestration boundary").

A thin layer between the checker's judgments and whatever model produces them:

- **Schema-constrained.** Every call names a pydantic `response_model`; the
  model is asked for that JSON schema and the reply is validated against it.
  A malformed reply raises `SchemaValidationError` — never silently accepted.
- **Provider-agnostic.** Requests go through LiteLLM, so the model is a
  configuration string (`anthropic/claude-sonnet-5`, `openai/gpt-...`) and
  providers can be compared on quality and cost without touching call sites.
- **Replay-first.** Every prompt/response is recorded to a transcript store
  keyed by request content. In `REPLAY` mode no live call is made at all — a
  missing transcript is an error, not a silent fallback to the network.

Transcripts deliberately record no wall-clock time and no run identifiers, so
re-running the same input reproduces byte-identical state (M0.5's acceptance
depends on this). LiteLLM is imported lazily inside the live path only, so
replay-mode runs — including CI and this project's own tests — need neither
the provider stack nor an API key.

M0.5 owns the seed/temperature configuration layer; the fields exist here
because they are part of a request's identity.
"""

from __future__ import annotations

import hashlib
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from acceptance.serialization import canonical_json

DEFAULT_TRANSCRIPT_ROOT = Path(".acceptance/cache/transcripts")

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class StrictResponseModel(BaseModel):
    """Base for a `response_model` passed to `ModelClient.complete`.

    OpenAI strict mode requires every object in the schema to forbid extra
    properties; `extra="forbid"` yields that. Every field must also be
    required (no defaults) — strict mode has no notion of an optional field,
    so a response schema should list one, non-defaulted field per value and
    return empty lists/None explicitly rather than omitting them.
    """

    model_config = ConfigDict(extra="forbid")


class Mode(str, Enum):
    """Whether calls may reach the network.

    RECORD is record-*if-missing*: an already-recorded request is served from
    its transcript rather than re-billed (§17 cost awareness). Delete a
    transcript — or change the prompt or response model, which changes the
    request key — to force a fresh call.
    """

    RECORD = "record"  # live call on a cache miss, then persist the transcript
    REPLAY = "replay"  # transcripts only; never call a provider


class LLMError(Exception):
    """Base class for harness failures."""


class SchemaValidationError(LLMError):
    """A model response did not parse/validate against the target schema."""


class TranscriptNotFoundError(LLMError):
    """REPLAY mode found no recorded transcript for a request."""


def request_key(request: dict) -> str:
    """Content-address a request.

    The response schema is part of the key: changing a `response_model`
    invalidates its old transcripts instead of replaying a stale shape.
    """
    return hashlib.sha256(canonical_json(request).encode("utf-8")).hexdigest()


class TranscriptStore:
    """Content-addressed prompt/response records on disk."""

    def __init__(self, root: Path | str = DEFAULT_TRANSCRIPT_ROOT) -> None:
        self.root = Path(root)

    def path_for(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def read(self, key: str) -> dict | None:
        path = self.path_for(key)
        if not path.is_file():
            return None
        return json.loads(path.read_text())

    def write(self, key: str, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        # Canonical form: identical records serialize byte-identically (M0.5).
        self.path_for(key).write_text(canonical_json(record) + "\n")


def _default_completion_fn(**kwargs: Any) -> Any:
    """Live provider call. Imported lazily so REPLAY never needs LiteLLM.

    `drop_params` lets LiteLLM discard controls a provider rejects instead of
    raising. Without it the harness is OpenAI-only in practice: Anthropic
    refuses `seed` outright and accepts only `temperature=1`, so a run against
    Claude fails before it starts. Dropping is safe *because* we then record
    what actually survived — see `_litellm_effective_controls`.
    """
    import litellm

    return litellm.completion(drop_params=True, **kwargs)


def inline_schema_refs(schema: dict) -> dict:
    """Resolve every `$ref` against `$defs` and drop the definitions block.

    Pydantic factors enums and nested models out into `$defs` and points at them
    with `$ref`. Providers handle that badly, and not only by mangling the reply
    shape — it measurably degrades the judgment itself. With the enum behind a
    `$ref`, `gpt-5.4-mini` answered `separable` 3/3 on an archetype whose ground
    truth is `risky`; with the identical prompt, model and determinism controls
    and the schema inlined, it answered `risky` 3/3 (#158). The allowed values
    have to be visible at the field, not one indirection away.

    This is why the harness cannot simply forward `model_json_schema()`.
    """

    def resolve(node: Any, defs: dict) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                target = defs[node["$ref"].rsplit("/", 1)[1]]
                siblings = {k: v for k, v in node.items() if k != "$ref"}
                # Siblings win: `$ref` alongside overrides is a legal narrowing.
                return {**resolve(target, defs), **siblings}
            return {k: resolve(v, defs) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [resolve(item, defs) for item in node]
        return node

    return resolve(schema, schema.get("$defs", {}))


def _litellm_effective_controls(model: str, **requested: Any) -> dict[str, Any]:
    """Which determinism controls the provider will actually honour.

    `drop_params` discards silently, so asking afterwards is the only way to
    avoid a transcript that claims a seed the provider never received. LiteLLM
    answers this offline, with no call and no billing. A `None` means the
    provider ignores that control and ran at its own default — the run is not
    pinned, and the record has to say so.
    """
    import litellm
    from litellm.utils import get_optional_params

    provider, _, bare = model.rpartition("/")
    applied = get_optional_params(
        model=bare or model,
        custom_llm_provider=provider or litellm.get_llm_provider(model)[1],
        drop_params=True,
        **requested,
    )
    return {name: applied.get(name) for name in requested}


# Carried on the function rather than the client so an injected `completion_fn`
# — every capability test — stays free of the provider stack (M0.4/M0.5).
_default_completion_fn.effective_controls = _litellm_effective_controls  # type: ignore[attr-defined]


def _extract_content(response: Any) -> str:
    """Pull the assistant text out of an OpenAI-shaped response."""
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError) as exc:
        raise SchemaValidationError(f"model response had no message content: {exc}") from exc
    if not isinstance(content, str):
        raise SchemaValidationError(f"model response content was {type(content).__name__}, not str")
    return content


def _extract_usage(response: Any) -> dict:
    """Token usage and cost, recorded so providers can be compared."""
    usage: dict[str, Any] = {}
    raw = getattr(response, "usage", None)
    if raw is not None:
        for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = getattr(raw, name, None)
            if value is not None:
                usage[name] = value

    # Only price a response LiteLLM itself produced. Looking the module up in
    # sys.modules rather than importing it keeps callers that inject their own
    # completion_fn — tests, fixtures — free of the provider stack entirely.
    litellm = sys.modules.get("litellm")
    if litellm is not None:
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            # Unpriced/unknown model; never fail a call over a cost lookup.
            cost = None
        if cost is not None:
            usage["cost_usd"] = cost
    return usage


class ModelClient:
    """Issues schema-constrained model calls and records them for replay."""

    def __init__(
        self,
        model: str,
        mode: Mode = Mode.REPLAY,
        store: TranscriptStore | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        completion_fn: Callable[..., Any] | None = None,
    ) -> None:
        self.model = model
        self.mode = mode
        self.store = store if store is not None else TranscriptStore()
        self.temperature = temperature
        self.seed = seed
        self._completion_fn = completion_fn or _default_completion_fn
        # One entry per completed call: the controls that call ran under, or
        # None if nothing is known about them. Accumulated so a review's
        # provenance can report the controls actually in force rather than the
        # ones configured (#160) — see `controls_in_force`.
        self._observed_controls: list[dict | None] = []

    def build_request(
        self, messages: list[dict], response_model: type[BaseModel]
    ) -> dict:
        """The recorded, hashed description of a call."""
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "response_schema": {
                "name": response_model.__name__,
                # Inlined here, inside the HASHED request, because it is what
                # actually reaches the provider and it changes the answer.
                "schema": inline_schema_refs(response_model.model_json_schema()),
            },
        }
        if self.seed is not None:
            request["seed"] = self.seed
        return request

    def complete(
        self, messages: list[dict], response_model: type[ResponseModelT]
    ) -> ResponseModelT:
        """Return a validated `response_model`, from a live call or a transcript."""
        request = self.build_request(messages, response_model)
        key = request_key(request)
        record = self.store.read(key)

        if record is None:
            if self.mode is Mode.REPLAY:
                raise TranscriptNotFoundError(
                    f"no recorded transcript for request {key} "
                    f"(model={self.model}, response_model={response_model.__name__}); "
                    "REPLAY mode does not fall back to a live call.\n"
                    "\n"
                    "The request key hashes the whole request, INCLUDING the system "
                    "prompt — so if this is a prompt-quality test, the most likely "
                    "cause is that a prompt was edited and has not been re-verified "
                    "against a real model (#146). Re-record and confirm the "
                    "assertions still hold:\n"
                    "    ACCEPTANCE_RECORD=1 pytest tests/prompts -q\n"
                    "Recording makes live calls AND runs the assertions, so a prompt "
                    "that degrades quality fails rather than silently re-recording."
                )
            record = self._persist_live_call(key, request, response_model)

        # Observed on both paths: a replayed run's reproducibility is exactly
        # that of the recording it replays, so a transcript recorded against a
        # provider that discarded a control must not replay as pinned.
        self._observed_controls.append(record.get("controls_applied"))
        return self._validate(record["response"], response_model)

    @property
    def controls_in_force(self) -> dict[str, Any] | None:
        """The determinism controls observed in force across this client's calls.

        `None` means indeterminate: either no call was made, or no call reported
        anything about its controls (a transcript recorded before this was
        tracked). That is distinct from a control being *absent*, which is the
        positive claim that the provider ignored it.

        Otherwise a control counts as in force only if every call agrees on its
        value. Disagreement, or a call that reported nothing, yields `None` for
        that control: a run is only as pinned as its least-pinned call, and
        overstating in the negative direction never claims reproducibility the
        run does not have (§3.7).
        """
        if not any(observed is not None for observed in self._observed_controls):
            return None
        per_call = [observed or {} for observed in self._observed_controls]
        in_force: dict[str, Any] = {}
        for name in ("temperature", "seed"):
            values = [call.get(name) for call in per_call]
            in_force[name] = values[0] if all(v == values[0] for v in values) else None
        return in_force

    def _persist_live_call(
        self, key: str, request: dict, response_model: type[BaseModel]
    ) -> dict:
        """Make the call, validate the reply, and only then keep the transcript.

        Validating first matters because structured output is best-effort on some
        providers: Anthropic omitted a required field in 2 of 4 probes of a real
        response schema. Persisting before validating let one of those replies
        into the corpus, where replay would serve it forever (#160). A response
        the harness rejects is not evidence and must not be stored.
        """
        record = self._live_call(key, request)
        self._validate(record["response"], response_model)
        self.store.write(key, record)
        return record

    def _live_call(self, key: str, request: dict) -> dict:
        requested = {"temperature": request["temperature"]}
        if "seed" in request:
            requested["seed"] = request["seed"]

        response = self._completion_fn(
            model=request["model"],
            messages=request["messages"],
            # LiteLLM's `response_format` is its provider-agnostic interface —
            # it translates this into each provider's own mechanism (Anthropic
            # takes structured output as tool use) and normalizes the reply.
            # We pass the schema rather than the model class only so it can be
            # ref-inlined first; passing the class would have LiteLLM call
            # `model_json_schema()` itself and reintroduce the `$defs` that
            # break Anthropic's reply shape and degrade judgment everywhere.
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": request["response_schema"]["name"],
                    "schema": request["response_schema"]["schema"],
                    # Strict is the strongest constraint providers offer, so
                    # response models must be strict-compatible: every field
                    # required, no open-ended dicts. One that isn't fails loudly
                    # on the live call rather than degrading to free text.
                    "strict": True,
                },
            },
            **requested,
        )

        record = {
            "request": request,
            "response": _extract_content(response),
            "usage": _extract_usage(response),
            # What the provider honoured, which is not always what we asked for.
            # Recorded so a transcript never implies a determinism control that
            # was silently dropped; absent for injected completion functions,
            # which have no provider to drop anything.
            "controls_applied": self._effective_controls(request["model"], requested),
        }
        return record

    def _effective_controls(self, model: str, requested: dict) -> dict:
        reporter = getattr(self._completion_fn, "effective_controls", None)
        if reporter is None:
            return dict(requested)
        return reporter(model, **requested)

    @staticmethod
    def _validate(content: str, response_model: type[ResponseModelT]) -> ResponseModelT:
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            raise SchemaValidationError(
                f"model response did not match {response_model.__name__}: {exc}"
            ) from exc
