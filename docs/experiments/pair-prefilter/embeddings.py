"""Recorded embedding calls for the prefilter experiment.

## Why this does not go through `ModelClient.embed`

The product's harness is the right place for an embedding a *review* makes, and
`llm.py::embed` records and replays exactly as this does. It is not used here
for one reason: `build_embedding_request` sends `model` and `input` and nothing
else, so it cannot ask for an `input_type`.

That matters. Voyage's embeddings endpoint accepts `input_type` of `query` or
`document` — verified against the live API on 2026-08-30, where a third value is
rejected with a 400 naming those two — and the whole shape of the filters here
is a short natural-language description retrieving a code document. Measuring
the asymmetric form is the point of running the experiment at all.

**Adding `input_type` to the product's request would move the embedding request
key and orphan the recorded linking transcripts.** That is a cost worth paying
only if the measurement says the asymmetry earns it, which is not known yet. So
the experiment carries its own client, the product stays untouched, and the
decision arrives with evidence behind it.

## The rate limit is the binding constraint, not the money

An account with no payment method on file gets **3 requests and 10,000 tokens
per minute**, which Voyage states in the body of the 429 it returns. The whole
experiment is about 59,000 tokens per pass, so it costs a few cents and about
six minutes of waiting. The pacer below exists for the minute, not the cents.

## The cache

Content-addressed on (model, input_type, text), under `.acceptance/cache/`,
which is gitignored. A second run costs nothing and makes no call. A fresh
clone re-embeds.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import deque
from pathlib import Path

import httpx

_URL = "https://api.voyageai.com/v1/embeddings"
_CACHE = Path(".acceptance/cache/experiments/pair-prefilter/embeddings")

#: Voyage rejects any other value; see the module docstring.
INPUT_TYPES = ("query", "document", None)

#: The free-tier ceilings, held to deliberately rather than discovered by 429.
#: Both are per rolling minute.
_MAX_REQUESTS_PER_MINUTE = 3
_MAX_TOKENS_PER_MINUTE = 10_000

#: Requests are built to a token budget rather than a text count, because one
#: 4,900-token hunk and one 40-token description cannot share a fixed batch
#: size. Held below the ceiling so an under-estimate does not cross it.
#:
#: 4,500 rather than 7,000 so two requests fit inside one minute's token budget
#: instead of one, and so a response carries fewer 1,024-wide vectors — `urllib`
#: truncated the larger ones mid-read, which cost a whole minute of the request
#: budget per retry. `httpx` replaced it for the same reason.
_BATCH_TOKENS = 4_500


class EmbeddingError(RuntimeError):
    pass


def _estimate_tokens(text: str) -> int:
    """Four characters to the token — good enough to pace with.

    Only ever used for pacing and batching, never recorded or reported. A
    request that crosses the real limit anyway is caught by the 429 retry.
    """
    return max(1, len(text) // 4)


class _Pacer:
    """Holds a rolling minute of request and token spend, and waits when full."""

    def __init__(self) -> None:
        self._events: deque[tuple[float, int]] = deque()

    def _prune(self, now: float) -> None:
        while self._events and now - self._events[0][0] >= 60:
            self._events.popleft()

    def wait_for(self, tokens: int) -> None:
        while True:
            now = time.monotonic()
            self._prune(now)
            requests = len(self._events)
            spent = sum(count for _, count in self._events)
            if requests < _MAX_REQUESTS_PER_MINUTE and spent + tokens <= _MAX_TOKENS_PER_MINUTE:
                return
            oldest = self._events[0][0]
            delay = max(0.5, 60 - (now - oldest) + 0.5)
            print(
                f"    pacing: {requests} requests / {spent} tokens in flight, waiting {delay:.0f}s"
            )
            time.sleep(delay)

    def record(self, tokens: int) -> None:
        self._events.append((time.monotonic(), tokens))


_PACER = _Pacer()


def _key(model: str, input_type: str | None, text: str) -> str:
    payload = json.dumps([model, input_type, text], sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _api_key() -> str:
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        raise EmbeddingError(
            "VOYAGE_API_KEY is not set. Load the repo's keys first:\n  set -a; . ./.env; set +a"
        )
    return key


def _post(model: str, input_type: str | None, texts: list[str]) -> list[list[float]]:
    body: dict = {"model": model, "input": texts}
    if input_type is not None:
        body["input_type"] = input_type
    tokens = sum(_estimate_tokens(text) for text in texts)

    headers = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    for attempt in range(5):
        _PACER.wait_for(tokens)
        _PACER.record(tokens)
        try:
            response = httpx.post(_URL, json=body, headers=headers, timeout=180)
        except httpx.HTTPError as exc:
            # A transport failure is not a rejection, and it still spent a
            # request against the minute — hence the retry rather than a raise.
            print(f"    {type(exc).__name__}, retrying")
            time.sleep(5)
            continue
        if response.status_code == 429:
            delay = 30 * (attempt + 1)
            print(f"    429, backing off {delay}s")
            time.sleep(delay)
            continue
        if response.status_code != 200:
            raise EmbeddingError(f"HTTP {response.status_code}: {response.text[:300]}")
        return [item["embedding"] for item in response.json()["data"]]
    raise EmbeddingError(f"embedding request still failing after 5 attempts ({len(texts)} texts)")


def _batches(indices: list[int], texts: list[str]) -> list[list[int]]:
    """Group by estimated token budget, never by count."""
    batches: list[list[int]] = []
    current: list[int] = []
    spent = 0
    for index in indices:
        cost = _estimate_tokens(texts[index])
        if current and spent + cost > _BATCH_TOKENS:
            batches.append(current)
            current, spent = [], 0
        current.append(index)
        spent += cost
    if current:
        batches.append(current)
    return batches


def embed(
    texts: list[str], model: str, input_type: str | None, label: str = ""
) -> list[list[float]]:
    """Vectors for `texts`, in order, served from cache where possible."""
    if input_type not in INPUT_TYPES:
        raise EmbeddingError(f"input_type must be one of {INPUT_TYPES}, not {input_type!r}")

    _CACHE.mkdir(parents=True, exist_ok=True)
    vectors: dict[int, list[float]] = {}
    missing: list[int] = []
    for index, text in enumerate(texts):
        path = _CACHE / f"{_key(model, input_type, text)}.json"
        if path.exists():
            vectors[index] = json.loads(path.read_text())
        else:
            missing.append(index)

    if missing:
        batches = _batches(missing, texts)
        print(f"  embedding {len(missing)}/{len(texts)} {label} in {len(batches)} requests")
        for number, chunk in enumerate(batches, start=1):
            fetched = _post(model, input_type, [texts[index] for index in chunk])
            if len(fetched) != len(chunk):
                raise EmbeddingError(f"asked for {len(chunk)} vectors, got {len(fetched)}")
            for index, vector in zip(chunk, fetched, strict=True):
                vectors[index] = vector
                (_CACHE / f"{_key(model, input_type, texts[index])}.json").write_text(
                    json.dumps(vector)
                )
            print(f"    {number}/{len(batches)} done")

    return [vectors[index] for index in range(len(texts))]


def cosine(left: list[float], right: list[float]) -> float:
    """Voyage returns unit-norm vectors, but this does not assume it.

    DR-259's threshold is stated in cosine *distance*; this returns similarity,
    and the callers convert. Mixing the two silently inverts every comparison.
    """
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if not left_norm or not right_norm:
        raise EmbeddingError("cannot take the cosine of a zero vector")
    return dot / (left_norm * right_norm)
