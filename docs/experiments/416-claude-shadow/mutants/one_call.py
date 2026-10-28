"""Arm 2 of #416's mutant slice: #379's "Mini, one call per case", with Sonnet 5.5 as the model.

The prompt is ``docs/experiments/jev/m52/prompts.py::mini_messages(case,
"context+description")``, unchanged: the requirement text (commit message), the
file, the original code, the test and the defect description, asking for one
word, yes or no. ``jev_mini.py`` sent it to GPT-5.4 Mini with reasoning off
(``reasoning_effort: "none"``) and at most 16 output tokens.

The messages are unchanged (the system message goes in ``system``). The call
settings could not carry over. The first probe sent Sonnet 5.5 the Mini
settings, reasoning off (``thinking: {"type": "between_tools"}``, since
``disabled`` is refused) and 16 tokens: on 4 of 4 cases Sonnet ignored "exactly
one word", began reasoning in its visible answer and was cut off, so no verdict.
Those 4 recordings stay in the cache. This arm therefore runs Sonnet on its
default settings (adaptive thinking, as the shipped-judge arm also does) with
``max_tokens`` 4096, room for the thinking and the one-word answer.
Two further things cannot carry over and are stated, not hidden:
- Mini's verdict was p(yes) >= 0.5 from token log-probabilities; the Anthropic
  API gives none, so Sonnet's verdict is the last word of its answer (even
  with thinking on, it writes its reasoning out and ends on yes or no).
- Where Mini gave no usable answer, ``jev_mini.py`` fell back to Jev's own
  p >= 0.5. Here an unusable answer is counted as no verdict (wrong).

Recorded under ``.acceptance/cache/416-mutants/one-call/`` (gitignored), keyed by
the sha256 of the canonical request; a recorded request never goes live again.

Run from the repo root:
    .venv/bin/python docs/experiments/416-claude-shadow/mutants/one_call.py \
        --side held_out [--limit 5] [--replay-only]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
M52 = HERE.parents[1] / "jev" / "m52"
sys.path.insert(0, str(M52))
sys.path.insert(0, str(HERE))

import prompts
from keys import key
from metrics import summary
from split import cases, load_split

ROOT = HERE.parents[3]
CACHE = ROOT / ".acceptance" / "cache" / "416-mutants" / "one-call"
MODEL = "claude-sonnet-5-5"
VARIANT = "context+description"
# Sonnet 5.5 list prices, $ per token.
PRICE_IN, PRICE_OUT = 2.00 / 1_000_000, 10.00 / 1_000_000
PRICE_CACHE_WRITE, PRICE_CACHE_READ = 2.50 / 1_000_000, 0.20 / 1_000_000


def request_for(case) -> dict:
    msgs = prompts.mini_messages(case, VARIANT)
    system = [m["content"] for m in msgs if m["role"] == "system"]
    return {
        "model": MODEL,
        "system": system[0],
        "messages": [m for m in msgs if m["role"] != "system"],
        "max_tokens": 4096,
    }


_client = None


def _live(request: dict) -> dict:
    global _client
    import anthropic

    if _client is None:
        import ssl

        import certifi

        # The SDK's default trust store is the macOS keychain, which the
        # sandbox blocks (OSStatus -26276); certifi's bundle is what LiteLLM uses.
        _client = anthropic.Anthropic(
            api_key=key("ANTHROPIC_API_KEY"),
            max_retries=6,
            http_client=anthropic.DefaultHttpxClient(
                verify=ssl.create_default_context(cafile=certifi.where())
            ),
        )
    body = dict(request)
    extra = {"thinking": body.pop("thinking")} if "thinking" in body else {}
    r = _client.messages.create(**body, extra_body=extra or None)
    return {
        "content": [b.to_dict() for b in r.content],
        "stop_reason": r.stop_reason,
        "usage": r.usage.to_dict(),
        "model": r.model,
    }


def ask(request: dict, replay_only: bool) -> dict:
    blob = json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    path = CACHE / f"{hashlib.sha256(blob.encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if replay_only:
        raise LookupError(f"not recorded: {path.name}")
    start = time.monotonic()
    response = _live(request)
    record = {
        "request": request,
        "response": response,
        "elapsed_ms": round((time.monotonic() - start) * 1000),
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)
    return record


def verdict(record: dict) -> bool | None:
    text = "".join(
        b.get("text", "") for b in record["response"]["content"] if b.get("type") == "text"
    )
    # Sonnet writes its reasoning first and the one-word answer last, so the
    # verdict is the final word (a lone yes/no is both first and last).
    word = text.strip().split()[-1].strip(".,!:;\"'*`").lower() if text.strip() else ""
    return {"yes": True, "no": False}.get(word)


def cost(record: dict) -> float:
    u = record["response"]["usage"]
    return (
        (u.get("input_tokens") or 0) * PRICE_IN
        + (u.get("output_tokens") or 0) * PRICE_OUT
        + (u.get("cache_creation_input_tokens") or 0) * PRICE_CACHE_WRITE
        + (u.get("cache_read_input_tokens") or 0) * PRICE_CACHE_READ
    )


def usable(side: str):
    ids = set(load_split()[side])
    out = []
    for c in cases():
        if c.case_id in ids:
            try:
                prompts.mutated_hunk(c)
                out.append(c)
            except prompts.CannotBuild:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["held_out", "tuning"], default="held_out")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--replay-only", action="store_true")
    args = ap.parse_args()

    cs = usable(args.side)
    if args.limit:
        cs = cs[: args.limit]
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(lambda c: ask(request_for(c), args.replay_only), cs))

    y = [c.killed for c in cs]
    said = [verdict(r) for r in records]
    total = sum(cost(r) for r in records)
    unparsed = [
        {
            "case_id": c.case_id,
            "stop_reason": r["response"]["stop_reason"],
            "content": r["response"]["content"],
        }
        for c, r, s in zip(cs, records, said, strict=True)
        if s is None
    ]
    result = {
        "model": f"anthropic/{MODEL}",
        "side": args.side,
        "design": "one call per case, context+description prompt, default adaptive thinking",
        "cases": len(cs),
        "killed": sum(y),
        "survived": len(y) - sum(y),
        "total_cost_usd": round(total, 4),
        **summary(said, y, cost_total=total),
        "unparsed_answers": unparsed,
        "per_case": {c.case_id: s for c, s in zip(cs, said, strict=True)},
    }
    if not args.limit:
        name = f"one-call-{args.side}-anthropic_{MODEL}.json"
        (HERE / name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_case"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
