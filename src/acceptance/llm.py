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
    """Live provider call. Imported lazily so REPLAY never needs LiteLLM."""
    import litellm

    return litellm.completion(**kwargs)


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
                "schema": response_model.model_json_schema(),
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
            record = self._record_live_call(key, request)

        return self._validate(record["response"], response_model)

    def _record_live_call(self, key: str, request: dict) -> dict:
        response = self._completion_fn(
            model=request["model"],
            messages=request["messages"],
            temperature=request["temperature"],
            # strict mode is the strongest constraint providers offer; response
            # models must therefore be strict-compatible (every field required,
            # no open-ended dicts). A model that isn't fails loudly on the live
            # call rather than degrading to unconstrained text.
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": request["response_schema"]["name"],
                    "schema": request["response_schema"]["schema"],
                    "strict": True,
                },
            },
            **({"seed": request["seed"]} if "seed" in request else {}),
        )
        record = {
            "request": request,
            "response": _extract_content(response),
            "usage": _extract_usage(response),
        }
        self.store.write(key, record)
        return record

    @staticmethod
    def _validate(content: str, response_model: type[ResponseModelT]) -> ResponseModelT:
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            raise SchemaValidationError(
                f"model response did not match {response_model.__name__}: {exc}"
            ) from exc
