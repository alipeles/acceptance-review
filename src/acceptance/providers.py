"""How a live completion reaches a provider: one adapter per provider (#432).

`ModelClient` owns everything about a call that does not depend on who answers
it: the request and its key, recording and replay, validating the reply, retries
and the record of what was spent. An adapter owns the rest — turning the request
into the provider's own call, and turning the provider's reply back into the
fields a recording holds.

Two paths exist:

- **`AnthropicAdapter`**, on Anthropic's official SDK, for every model whose name
  states `anthropic/` (`llm.provider_of`). This is the main path, where batching,
  cache breakpoints, exact token counts and exact cost matter, and where routing
  through LiteLLM meant reconstructing each of them (#432).
- **The LiteLLM path** (`LITELLM_CAPABILITIES`), for every other provider and for
  a completion function a caller injects. Its code stays in `llm`, where it
  served every call before this module.

Each adapter declares what its provider can do (`Capabilities`), and the client
reads that declaration rather than inferring behaviour from a model's name.

## What an adapter never touches

**The request key.** The key is computed from `ModelClient.build_request`, which
knows nothing about providers, before any adapter is chosen. Moving a provider
from one adapter to another therefore re-keys nothing: every recording made
through LiteLLM replays unchanged after this module, and a recording made here
replays with no adapter involved at all.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

#: The provider value `llm.provider_of` returns for Anthropic's own API.
ANTHROPIC = "anthropic"

#: The value of a recording's `sent_via` field when its call was batched.
SENT_VIA_BATCH = "batch"

#: How long one direct call may take before it is abandoned and retried. The
#: same ten minutes LiteLLM allowed, given explicitly: left unset, the SDK
#: refuses a non-streaming call whose output ceiling could outlast it.
_REQUEST_TIMEOUT_SECONDS = 600.0


@dataclass(frozen=True)
class Capabilities:
    """What a provider does with a request, declared by its adapter.

    The client asks these questions of the adapter, never of the model's name.
    A control answer of None means the adapter cannot say in advance, and asks
    the provider's own controls per call instead (the LiteLLM path).
    """

    #: Takes an explicit marker where the reusable opening of a request ends.
    cache_breakpoints: bool
    #: Can send a run's calls through a batch endpoint at a lower price.
    batching: bool
    #: Applies the run's temperature.
    honours_temperature: bool | None
    #: Applies the run's seed.
    honours_seed: bool | None
    #: The reasoning efforts it passes on; anything else is refused before the call.
    efforts: frozenset[str] | None
    #: Where a call's cost comes from: "adapter" (this module's price table,
    #: applied to the provider's own token counts) or "litellm" (its pricing).
    pricing: str


@dataclass
class ProviderReply:
    """The fields a recording takes from one provider reply."""

    content: str
    usage: dict[str, Any]
    stop_reason: str | None
    sent_via: str | None = None


# ---------------------------------------------------------------------------
# LiteLLM

#: Every provider without an adapter of its own, and every injected completion
#: function, goes through `llm._default_completion_fn` or the injected function,
#: which is the code that served every call before #432. LiteLLM decides per
#: provider which controls survive, and the client asks it per call
#: (`llm._litellm_effective_controls`), so the control answers here are None.
#: It never marks an opening and never batches: the providers it serves either
#: reuse an opening on their own or were not measured, and batching is the
#: Anthropic adapter's.
LITELLM_CAPABILITIES = Capabilities(
    cache_breakpoints=False,
    batching=False,
    honours_temperature=None,
    honours_seed=None,
    efforts=None,
    pricing="litellm",
)


# ---------------------------------------------------------------------------
# Anthropic


ANTHROPIC_CAPABILITIES = Capabilities(
    cache_breakpoints=True,
    batching=True,
    # Claude has no seed, and has refused any temperature since 2026-10-21, so
    # neither is sent. The run still asks for both: they are part of the hashed
    # request, and the recording says neither was applied.
    honours_temperature=False,
    honours_seed=False,
    # `output_config.effort`. `max` exists too, but no stage may ask for it:
    # `llm.ReasoningEffort` does not list it.
    efforts=frozenset({"low", "medium", "high", "xhigh"}),
    pricing="adapter",
)

#: What a call costs, in US dollars per million tokens, by the model name with
#: its `anthropic/` prefix removed. Read from Anthropic's pricing on 2026-11-02.
#: A cache write is the 5-minute write, which is the only one this client asks
#: for. A model absent here is not priced: its recording carries token counts
#: and no `cost_usd`, which is what a provider LiteLLM cannot price gets too,
#: and "unknown" is a truer figure than a guess.
ANTHROPIC_PRICES_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
}

#: A batched call's price as a share of the same call sent directly.
BATCH_PRICE_FACTOR = 0.5


def bare_model(model: str) -> str:
    """The model id Anthropic's API takes: the configured name without `anthropic/`."""
    return model.split("/", 1)[1] if "/" in model else model


def _default_sdk_client() -> Any:
    """The Anthropic SDK client. Imported lazily, so replay never needs the SDK.

    Retries are off because `ModelClient._call_provider` already retries a
    transient failure; with both, one outage would be asked about fifteen times.
    """
    import anthropic

    return anthropic.Anthropic(max_retries=0)


def _sdk_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """`fn(*args, **kwargs)`, with the SDK's connection failures made recognisable.

    The client's retry rule (`llm._is_transient`) treats a status of 408, 429 or
    5xx, or Python's own `ConnectionError` or `TimeoutError`, as worth asking
    again. The SDK's status errors carry `status_code` already; its connection
    and timeout errors carry no status and are not Python's own, so they are
    re-raised as those. Anything else passes through untouched.
    """
    import anthropic

    try:
        return fn(*args, **kwargs)
    except anthropic.APITimeoutError as exc:
        raise TimeoutError(str(exc)) from exc
    except anthropic.APIConnectionError as exc:
        raise ConnectionError(str(exc)) from exc


def to_anthropic_messages(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split a request's messages into Anthropic's `system` blocks and turns.

    Every system message becomes system text, in order. Consecutive messages of
    one role become one turn of several text blocks, which is how Anthropic
    reads two user messages in a row anyway. A message whose content is already
    a list of blocks — the one carrying a cache breakpoint — keeps its blocks.
    Nothing is added and nothing is reworded: the provider receives the request's
    text in the request's order.
    """
    system: list[dict] = []
    turns: list[dict] = []
    for message in messages:
        content = message["content"]
        blocks = (
            [{"type": "text", "text": content}]
            if isinstance(content, str)
            else [dict(block) for block in content]
        )
        role = message["role"]
        if role == "system":
            system.extend(blocks)
        elif turns and turns[-1]["role"] == role:
            turns[-1]["content"].extend(blocks)
        else:
            turns.append({"role": role, "content": blocks})
    return system, turns


def anthropic_usage(raw: Mapping[str, Any], model: str, batched: bool) -> dict[str, Any]:
    """The usage figures a recording keeps, from Anthropic's own `usage`.

    Recorded under the names every recording already uses, so the spend summary
    reads a call the same way whichever adapter made it. Anthropic reports input
    in three parts — uncached, read from cache, written to cache — and
    `prompt_tokens` is their sum, which is also what LiteLLM recorded.

    A count Anthropic did not report is omitted, never written as zero, for the
    reason `llm._extract_usage` gives. The cost is priced here, at the rate the
    call was billed at: a batched call at the batch rate, so nothing corrects
    it afterwards.
    """
    uncached = int(raw.get("input_tokens") or 0)
    read = raw.get("cache_read_input_tokens")
    written = raw.get("cache_creation_input_tokens")
    output = int(raw.get("output_tokens") or 0)
    prompt = uncached + int(read or 0) + int(written or 0)

    usage: dict[str, Any] = {
        "prompt_tokens": prompt,
        "completion_tokens": output,
        "total_tokens": prompt + output,
    }
    if read is not None:
        usage["cached_tokens"] = int(read)
    if written is not None:
        usage["cache_creation_tokens"] = int(written)

    prices = ANTHROPIC_PRICES_PER_MTOK.get(bare_model(model))
    if prices is not None:
        cost = (
            uncached * prices["input"]
            + int(read or 0) * prices["cache_read"]
            + int(written or 0) * prices["cache_write"]
            + output * prices["output"]
        ) / 1_000_000
        usage["cost_usd"] = cost * (BATCH_PRICE_FACTOR if batched else 1.0)
    return usage


class AnthropicAdapter:
    """Sends completions to Anthropic's Messages API through its official SDK.

    One adapter serves one client. `sdk_factory` is injectable so every part of
    this path can run in a test with no network; by default it builds the SDK's
    own client, which reads `ANTHROPIC_API_KEY`.
    """

    capabilities = ANTHROPIC_CAPABILITIES

    def __init__(self, sdk_factory: Callable[[], Any] | None = None) -> None:
        self._sdk_factory = sdk_factory
        self._sdk: Any = None
        self._lock = threading.Lock()
        # Answers to questions asked once per run rather than once per call.
        self._max_tokens: dict[str, int] = {}
        self._opening_tokens: dict[str, int] = {}

    def __eq__(self, other: object) -> bool:
        """Two adapters built the same way are the same configuration.

        What one has cached — an output ceiling, an opening's length — is a fact
        about the provider, not about how the adapter was configured, so it is
        not compared.
        """
        if not isinstance(other, AnthropicAdapter):
            return NotImplemented
        return self._sdk_factory == other._sdk_factory

    __hash__ = None  # type: ignore[assignment]  # mutable caches; never a dict key

    def sdk(self) -> Any:
        with self._lock:
            if self._sdk is None:
                factory = self._sdk_factory or _default_sdk_client
                self._sdk = factory()
            return self._sdk

    @staticmethod
    def missing_keys(model: str) -> list[str]:
        """The variable the SDK needs and does not have.

        The SDK also accepts `ANTHROPIC_AUTH_TOKEN`, so either one present is
        enough; the message names the API key, which is what a user sets.
        """
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return []
        return ["ANTHROPIC_API_KEY"]

    def effective_controls(self, model: str, requested: Mapping[str, Any]) -> dict[str, Any]:
        """Which of the requested controls this adapter will send.

        Answered from the declared capabilities, with no call. A control that is
        not sent is recorded as None, the same claim LiteLLM's answer made: the
        run asked for it and the provider ran without it.
        """
        caps = self.capabilities
        applied: dict[str, Any] = {}
        for name, value in requested.items():
            if name == "temperature":
                applied[name] = value if caps.honours_temperature else None
            elif name == "seed":
                applied[name] = value if caps.honours_seed else None
            elif name == "reasoning_effort":
                accepted = caps.efforts is not None and value in caps.efforts
                applied[name] = value if accepted else None
            else:
                applied[name] = None
        return applied

    def count_tokens(self, model: str, messages: list[dict]) -> int:
        """Anthropic's own count of `messages`, asked once per distinct opening.

        Used only to decide whether an opening clears the model's minimum for a
        cache breakpoint. Exact, where LiteLLM's count used OpenAI's tokenizer.
        Counting is free and makes no completion; it does need the network,
        which is why it happens only on the live path.
        """
        system, turns = to_anthropic_messages(messages)
        digest = hashlib.sha256(
            json.dumps([model, system, turns], sort_keys=True).encode()
        ).hexdigest()
        with self._lock:
            known = self._opening_tokens.get(digest)
        if known is not None:
            return known
        params: dict[str, Any] = {"model": bare_model(model), "messages": turns}
        if system:
            params["system"] = system
        counted = int(_sdk_call(self.sdk().messages.count_tokens, **params).input_tokens)
        with self._lock:
            self._opening_tokens[digest] = counted
        return counted

    def max_tokens(self, model: str) -> int:
        """The model's own output ceiling, from Anthropic's Models API.

        The same ceiling LiteLLM sent — the most the model can produce — so a
        long answer is not cut short by a limit of ours. Asked once per model.
        """
        bare = bare_model(model)
        with self._lock:
            known = self._max_tokens.get(bare)
        if known is not None:
            return known
        ceiling = int(_sdk_call(self.sdk().models.retrieve, bare).max_tokens)
        with self._lock:
            self._max_tokens[bare] = ceiling
        return ceiling

    def build_params(
        self,
        model: str,
        messages: list[dict],
        schema: dict,
        effort: str | None,
    ) -> dict[str, Any]:
        """The Messages API request for one call.

        `messages` arrive already marked (see `llm.mark_reusable_opening`). The
        response schema goes through the SDK's own `transform_schema`, which
        removes the constraints Anthropic's structured output rejects and states
        them in the field's description instead; the reply is still validated
        against the original schema by the client.
        """
        from anthropic import transform_schema

        system, turns = to_anthropic_messages(messages)
        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": transform_schema(schema)}
        }
        if effort is not None:
            output_config["effort"] = effort
        params: dict[str, Any] = {
            "model": bare_model(model),
            "max_tokens": self.max_tokens(model),
            "messages": turns,
            "output_config": output_config,
        }
        if system:
            params["system"] = system
        return params

    def send(self, params: dict[str, Any], batcher: Any | None) -> dict:
        """One call, direct or through `batcher`, returning the reply as a dict."""
        if batcher is not None:
            return batcher.send(params)
        message = _sdk_call(self.sdk().messages.create, **params, timeout=_REQUEST_TIMEOUT_SECONDS)
        return message if isinstance(message, dict) else message.to_dict(mode="json")

    @staticmethod
    def reply(message: Mapping[str, Any], model: str, batched: bool) -> ProviderReply:
        """The recorded fields of one Messages API reply.

        The answer is the reply's text. Claude may think before it answers, and
        its thinking arrives as blocks of another type, which are not the answer
        and are left out. The stop reason is Anthropic's own (`end_turn`,
        `max_tokens`, `refusal`), not translated into another provider's words.
        """
        texts = [
            block.get("text", "")
            for block in message.get("content") or []
            if isinstance(block, Mapping) and block.get("type") == "text"
        ]
        stop_reason = message.get("stop_reason")
        return ProviderReply(
            content="".join(texts),
            usage=anthropic_usage(message.get("usage") or {}, model, batched),
            stop_reason=stop_reason if isinstance(stop_reason, str) else None,
            sent_via=SENT_VIA_BATCH if batched else None,
        )
