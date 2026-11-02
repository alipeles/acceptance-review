"""Send a run's live calls through the Message Batches API instead (#414).

A batched call costs half what the same call costs sent directly, and in
exchange it may take minutes rather than seconds to come back. That trade suits
a run nobody is waiting on — benchmark scoring, an experiment script — and does
not suit `acceptance check`, so it is an opt-in on `RunConfig` and off by
default.

## How a call becomes part of a batch

Nothing above `ModelClient._live_call` knows a batch exists. Every stage still
calls `client.complete` once per question, from the threads `concurrency`
already runs it on, and each call still blocks until its own answer is back.
What changes is where the Anthropic adapter (`providers.AnthropicAdapter`)
sends the request it built: instead of posting it to `/v1/messages`, it hands
it to `MessageBatcher.send`, which queues it and waits. When no new request has
arrived for `gather_seconds`, everything queued goes out as one Message Batch,
and each answer is handed back to the thread that asked for it, matched by
`custom_id`.

The adapter builds the request and reads the reply either way. The params in
the batch are the params a direct call sends — the same `output_config`, the
same `cache_control` breakpoint, the same controls left out — and the reply goes
through the same reading of text, usage and price. A batched recording and a
direct one cannot drift apart in shape, because no code here translates either
of them.

## What it does not change

**The request key.** The key is computed from the request before any provider
sees it, so the same question has the same key however it was sent, and a
batched recording replays with no live call exactly as a direct one does. The
recording gains one field, `sent_via`, and only when it was batched, so every
recording made directly keeps the five fields it always had.

**Order.** Results arrive from a batch in no particular order. Nothing here
depends on it: each answer goes to the thread that asked, and `map_calls`
returns in input order regardless of completion order.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import Future
from typing import Any

#: How many calls may be in flight at once while batching. The default of eight
#: in `concurrency` is a promise to a provider's rate limit, which a batch does
#: not consume; held at eight, a stage would go out as one batch of eight after
#: another, each waiting minutes. A batch takes up to 100,000 requests, so the
#: ceiling here is set by threads, which sit idle waiting for their answer.
BATCH_CALLS_IN_FLIGHT = 512

#: A Message Batch's limit on requests.
MAX_REQUESTS_PER_BATCH = 100_000

#: How long the queue must sit with nothing new arriving before what is in it
#: goes out. A stage's calls are queued within milliseconds of each other, so
#: two seconds of quiet means the stage has nothing more to ask yet.
GATHER_SECONDS = 2.0

#: How often a sent batch is asked whether it has finished. A batch usually
#: takes minutes, so asking more often only spends requests.
POLL_SECONDS = 30.0

# The status an errored result is reported under, by the error type the batch
# gives, so a batched failure reaches `_call_provider` exactly as the same
# failure sent directly would: retried if transient, reported if not.
_ERROR_STATUS = {
    "invalid_request_error": 400,
    "authentication_error": 401,
    "billing_error": 402,
    "permission_error": 403,
    "not_found_error": 404,
    "request_too_large": 413,
    "rate_limit_error": 429,
    "api_error": 500,
    "timeout_error": 504,
    "overloaded_error": 529,
}


class BatchCallError(Exception):
    """A batched call that came back without an answer.

    It carries `status_code` because that is what `_call_provider` reads to
    decide whether a failure is worth asking again.
    A result that expired or was cancelled before it ran is reported as 500:
    nothing was wrong with the request, so asking again is the right answer.
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _default_sdk_client() -> Any:
    """The Anthropic SDK client, built the way the direct path builds it."""
    from acceptance.providers import _default_sdk_client as build

    return build()


def _custom_id(params: dict) -> str:
    # 64 hex characters: exactly the longest `custom_id` a batch accepts. Two
    # identical requests share one id, and therefore one answer.
    body = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def _as_dict(message: Any) -> dict:
    if isinstance(message, dict):
        return message
    return message.to_dict(mode="json")


class MessageBatcher:
    """Collects concurrent live calls into Message Batches.

    One batcher serves a whole run, shared by every thread that calls the
    model. `sdk_client` is injectable so the batch path can be exercised
    without the network; by default it is the SDK's own client, which reads
    the same API key a direct call does.
    """

    def __init__(
        self,
        sdk_client: Any | None = None,
        gather_seconds: float | None = None,
        poll_seconds: float | None = None,
    ) -> None:
        self._sdk_client = sdk_client
        self._gather_seconds = GATHER_SECONDS if gather_seconds is None else gather_seconds
        self._poll_seconds = POLL_SECONDS if poll_seconds is None else poll_seconds
        self._lock = threading.Lock()
        # Requests waiting to be sent, by custom_id.
        self._queued: dict[str, dict] = {}
        self._waiting: dict[str, Future] = {}
        self._last_queued = 0.0
        self._gathering = False
        #: Ids of the batches sent, in the order they were created.
        self.batch_ids: list[str] = []

    def send(self, params: dict) -> dict:
        """Queue one Messages API request and block until its answer is back."""
        custom_id = _custom_id(params)
        with self._lock:
            future = self._waiting.get(custom_id)
            if future is None:
                future = Future()
                self._waiting[custom_id] = future
                self._queued[custom_id] = params
            self._last_queued = time.monotonic()
            if not self._gathering:
                self._gathering = True
                threading.Thread(target=self._gather, daemon=True).start()
        return future.result()

    def _gather(self) -> None:
        """Wait for the queue to go quiet, then send what is in it."""
        while True:
            with self._lock:
                quiet = time.monotonic() - self._last_queued
                if quiet >= self._gather_seconds:
                    queued, self._queued = self._queued, {}
                    self._gathering = False
                    break
            time.sleep(self._gather_seconds - quiet)
        items = list(queued.items())
        for start in range(0, len(items), MAX_REQUESTS_PER_BATCH):
            chunk = dict(items[start : start + MAX_REQUESTS_PER_BATCH])
            threading.Thread(target=self._run_batch, args=(chunk,), daemon=True).start()

    def _run_batch(self, requests: dict[str, dict]) -> None:
        try:
            self._answer(requests)
        except Exception as exc:  # noqa: BLE001 — every waiting caller must hear of it
            # Whatever went wrong with the batch as a whole went wrong for every
            # call in it, and a call left waiting would hang its stage forever.
            self._settle(requests, error=exc)

    def _answer(self, requests: dict[str, dict]) -> None:
        sdk = self._sdk_client if self._sdk_client is not None else _default_sdk_client()
        self._sdk_client = sdk
        batches = sdk.messages.batches
        batch = batches.create(
            requests=[{"custom_id": cid, "params": params} for cid, params in requests.items()],
        )
        with self._lock:
            self.batch_ids.append(batch.id)
        while batch.processing_status != "ended":
            time.sleep(self._poll_seconds)
            batch = batches.retrieve(batch.id)
        for item in batches.results(batch.id):
            if item.custom_id not in requests:
                continue
            result = item.result
            if result.type == "succeeded":
                self._settle({item.custom_id: None}, answer=_as_dict(result.message))
                continue
            if result.type == "errored":
                error = result.error.error
                failure = BatchCallError(
                    f"batch {batch.id}: {error.type}: {error.message}",
                    _ERROR_STATUS.get(error.type, 500),
                )
            else:
                failure = BatchCallError(f"batch {batch.id}: request {result.type}", 500)
            self._settle({item.custom_id: None}, error=failure)
        # A request the results did not mention is as unanswered as one that
        # expired, and its caller must not wait for an answer that is not coming.
        self._settle(
            requests, error=BatchCallError(f"batch {batch.id}: no result for request", 500)
        )

    def _settle(
        self, requests: dict[str, Any], answer: dict | None = None, error: Exception | None = None
    ) -> None:
        with self._lock:
            futures = [self._waiting.pop(cid, None) for cid in requests]
        for future in futures:
            if future is None:
                continue
            if error is not None:
                future.set_exception(error)
            else:
                future.set_result(answer)
