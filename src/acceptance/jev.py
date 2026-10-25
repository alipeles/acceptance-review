"""Jev, TypeSafe's yes/no judge, as a provider a review records and replays (#385).

Jev is not a chat model. It takes a structured `state` and a map of questions,
and for a yes/no ("noul") question it answers with the probability of yes, which
is what DR-379's rule decides on. So it does not go through LiteLLM or
`ModelClient.complete`, both of which are built around a response schema Jev
has no use for.

**It replays like any other call.** Each request goes through
`ModelClient.replay_or_run`, the path a coding agent's edit already takes
(#338): recorded on first sight in RECORD, served from the recording ever
after, and never live in REPLAY. The probability is part of the recorded
response, so a replayed review reaches exactly the decision the recorded one
did, and two recordings of the same input are byte-identical because the
store writes canonical JSON.

The request carries no temperature or seed. Jev offers neither, so there is
nothing to ask for and nothing to report as dropped; as with Claude since #412,
the recording is what makes a run reproducible.

**Cost is computed here, from the recorded input tokens**, at the launch price
DR-379's figures used ($0.042 per million input tokens, output free). Jev's
reply carries token counts and no price, and `acceptance.usage` sums
`cost_usd`, so the price has to be applied before the usage is recorded.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from acceptance.llm import LLMError, MissingKeyError, ModelClient, SchemaValidationError

__all__ = [
    "JEV_KEY",
    "JEV_MODEL",
    "JEV_PRICE_PER_INPUT_TOKEN",
    "JEV_URL",
    "JevAnswer",
    "JevProvider",
]

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"
JEV_KEY = "TYPESAFE_API_KEY"
JEV_PRICE_PER_INPUT_TOKEN = 0.042 / 1_000_000

# The `kind` that keeps a Jev request from colliding with a completion, an
# embedding or a coding-agent edit in the content-addressed store.
_KIND = "jev"

_MAX_ATTEMPTS = 5
_FIRST_BACKOFF_SECONDS = 2.0
# 529 is TypeSafe's "overloaded"; the experiment's recorder retried it with 429.
_TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504, 529})
_TIMEOUT_SECONDS = 60.0

PostFn = Callable[[str, dict, dict], tuple[int, Any]]


class JevAnswer:
    """One question's answer: the probability of yes, and what the call cost."""

    __slots__ = ("probability", "usage")

    def __init__(self, probability: float, usage: dict[str, Any]) -> None:
        self.probability = probability
        self.usage = usage


def _default_post(url: str, body: dict, headers: dict) -> tuple[int, Any]:
    """POST `body` as JSON, returning the status and the parsed reply.

    Imported lazily, like every other provider touch, so a replayed review never
    loads an HTTP client.
    """
    import httpx

    response = httpx.post(url, json=body, headers=headers, timeout=_TIMEOUT_SECONDS)
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    return response.status_code, payload


def _usage(reply: dict) -> dict[str, Any]:
    """Jev's token counts in the names `acceptance.usage` reads, priced."""
    raw = reply.get("usage") or {}
    usage: dict[str, Any] = {}
    input_tokens = raw.get("input_tokens")
    output_tokens = raw.get("output_tokens")
    if isinstance(input_tokens, int):
        usage["prompt_tokens"] = input_tokens
        usage["cost_usd"] = input_tokens * JEV_PRICE_PER_INPUT_TOKEN
    if isinstance(output_tokens, int):
        usage["completion_tokens"] = output_tokens
    return usage


def _probability(response: Any, question: str) -> float:
    """The probability of yes for `question`, or a typed error saying why not.

    Checked on the replay path as well as the live one: a recording is a file
    a person can edit, so its shape is not trusted because it was valid once.
    """
    try:
        value = response["answers"][question]["noul"]
    except (KeyError, TypeError) as exc:
        raise SchemaValidationError(
            f"Jev's reply carries no yes/no answer for question {question!r}"
        ) from exc
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
        raise SchemaValidationError(
            f"Jev's answer to {question!r} is not a probability between 0 and 1: {value!r}"
        )
    return float(value)


class JevProvider:
    """Asks Jev one question per call, recorded and replayed through `client`.

    `post_fn` replaces the HTTP call, for tests; with one injected, no key is
    required, exactly as an injected completion function needs none.
    """

    def __init__(self, post_fn: PostFn | None = None) -> None:
        self._post_fn = post_fn or _default_post
        self._needs_key = post_fn is None

    def ask(
        self,
        client: ModelClient,
        state: dict[str, str],
        questions: dict[str, dict],
        stage: str,
        label: str | None = None,
    ) -> dict[str, JevAnswer]:
        """Every question's answer, from a recording or one live call."""
        request = {
            "kind": _KIND,
            "model": JEV_MODEL,
            "url": JEV_URL,
            "state": state,
            "questions": questions,
        }
        response = client.replay_or_run(
            request, lambda: self._run(request, stage), stage, label=label
        )
        usage = _usage(response) if isinstance(response, dict) else {}
        return {name: JevAnswer(_probability(response, name), usage) for name in questions}

    def _run(self, request: dict, stage: str) -> dict[str, Any]:
        """One live call, retried on a transient failure, validated before it is kept.

        Validated here as well as on read for the reason
        `ModelClient._persist_live_call` gives (#160): a reply that is kept is
        served for ever, so one the harness would reject must never be stored.
        """
        headers: dict[str, str] = {}
        if self._needs_key:
            key = os.environ.get(JEV_KEY)
            if not key:
                raise MissingKeyError(
                    f"Jev call for stage {stage!r} was not sent: {JEV_KEY} is not set. "
                    "Set it in the environment or in a .env file in the directory "
                    "acceptance runs from."
                )
            headers["Authorization"] = f"Bearer {key}"
        body = {
            "model": request["model"],
            "state": request["state"],
            "questions": request["questions"],
        }
        delay = _FIRST_BACKOFF_SECONDS
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            status, reply = self._post_fn(request["url"], body, headers)
            if status == 200:
                break
            if status in _TRANSIENT_STATUSES and attempt < _MAX_ATTEMPTS:
                time.sleep(delay)
                delay *= 2
                continue
            outcome = (
                f"after {attempt} attempts"
                if status in _TRANSIENT_STATUSES
                else "and was not retried"
            )
            raise LLMError(
                f"Jev call for stage {stage!r} failed with status {status} {outcome}: "
                f"{str(reply)[:300]}"
            )
        if not isinstance(reply, dict):
            raise SchemaValidationError(f"Jev's reply is not a JSON object: {str(reply)[:300]}")
        for name in request["questions"]:
            _probability(reply, name)
        # Only what decides the answer and what it cost. Anything else in the
        # reply — a request id, a timing — would differ between two recordings
        # of the same input, and recordings must be byte-identical (M0.5).
        kept = {
            "answers": {
                name: {"noul": reply["answers"][name]["noul"]} for name in request["questions"]
            },
            "model": reply.get("model"),
            "usage": {
                name: reply["usage"][name]
                for name in ("input_tokens", "output_tokens")
                if isinstance(reply.get("usage"), dict) and name in reply["usage"]
            },
        }
        return {"response": kept, "usage": _usage(kept)}
