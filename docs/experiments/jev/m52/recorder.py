"""Record-if-missing, then replay, for Jev and Mini calls in this experiment.

Each request is keyed by the sha256 of its canonical JSON plus a repeat
index, and stored as one file under ``.acceptance/cache/jev-m52/`` (gitignored).
A recorded request never goes live again; ``replay_only=True`` raises instead
of calling, so scoring can prove it ran off recordings.

``llm.py`` is deliberately not used: it neither requests nor stores token
probabilities, and changing it would move every stage's request key (#379).
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import httpx
from keys import key
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / ".acceptance" / "cache" / "jev-m52"

JEV_URL = "https://api.typesafe.ai/v1/systemone"
MINI_MODEL = "gpt-5.4-mini"


class NotRecorded(LookupError):
    pass


def _key(provider: str, request: dict, repeat: int) -> str:
    blob = json.dumps(
        {"provider": provider, "request": request, "repeat": repeat},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cached(provider: str, request: dict, repeat: int, live, replay_only: bool) -> dict:
    path = CACHE / f"{_key(provider, request, repeat)}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if replay_only:
        raise NotRecorded(path.name)
    start = time.monotonic()
    response = live(request)
    record = {
        "provider": provider,
        "repeat": repeat,
        "request": request,
        "response": response,
        "elapsed_ms": round((time.monotonic() - start) * 1000),
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)
    return record


# --- Jev -------------------------------------------------------------------

_jev_client: httpx.Client | None = None


def _jev_live(request: dict) -> dict:
    global _jev_client
    if _jev_client is None:
        _jev_client = httpx.Client(
            headers={"Authorization": f"Bearer {key('TYPESAFE_API_KEY')}"}, timeout=60
        )
    for attempt in range(5):
        r = _jev_client.post(JEV_URL, json=request)
        if r.status_code in (429, 529) and attempt < 4:
            time.sleep(2**attempt)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("unreachable")


def jev(request: dict, repeat: int = 0, replay_only: bool = False) -> dict:
    return _cached("jev", request, repeat, _jev_live, replay_only)


def jev_p_yes(record: dict) -> float:
    return float(record["response"]["answers"]["fails"]["noul"])


# --- Mini ------------------------------------------------------------------

_mini_client: OpenAI | None = None


def _mini_live(request: dict) -> dict:
    global _mini_client
    if _mini_client is None:
        _mini_client = OpenAI(api_key=key("OPENAI_API_KEY"))
    r = _mini_client.chat.completions.create(**request)
    choice = r.choices[0]
    tokens = []
    for tok in (choice.logprobs.content or []) if choice.logprobs else []:
        tokens.append(
            {
                "token": tok.token,
                "logprob": tok.logprob,
                "top": [{"token": a.token, "logprob": a.logprob} for a in tok.top_logprobs or []],
            }
        )
    return {
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "tokens": tokens,
        "usage": r.usage.model_dump() if r.usage else None,
    }


def mini_request(messages: list[dict]) -> dict:
    return {
        "model": MINI_MODEL,
        "messages": messages,
        "logprobs": True,
        "top_logprobs": 5,
        "reasoning_effort": "none",
        # 4 left 62 of 548 tuning calls with an empty answer and no tokens,
        # finish_reason "length"; 16 leaves room for whatever precedes it.
        "max_completion_tokens": 16,
    }


def mini(request: dict, repeat: int = 0, replay_only: bool = False) -> dict:
    return _cached("mini", request, repeat, _mini_live, replay_only)


def mini_p_yes(record: dict) -> float | None:
    """p(yes) normalised over yes and no at the first non-blank token, or None."""
    tokens = [t for t in record["response"]["tokens"] if t["token"].strip()]
    if not tokens:
        return None
    yes = no = 0.0
    for alt in tokens[0]["top"]:
        word = alt["token"].strip().lower()
        if word == "yes":
            yes += math.exp(alt["logprob"])
        elif word == "no":
            no += math.exp(alt["logprob"])
    if yes + no == 0:
        return None
    return yes / (yes + no)
