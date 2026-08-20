"""Does the provider's prompt cache key cover the response schema? (#265)

Run it:

    .venv/bin/python docs/experiments/265-cache-key-scope/cache_key_scope.py
    .venv/bin/python docs/experiments/265-cache-key-scope/cache_key_scope.py --json out.json

**This makes live calls.** Six of them, a few thousand tokens each. It needs
`OPENAI_API_KEY` from `.env`.

## The question

#265's change made coverage classification and unrequested-change detection open
with a byte-identical ~70k-token diff block, issued seconds apart in one review
run. The second reused **none** of it — both reported 0.0% cached. The bytes were
identical and the ordering was right, so something other than the messages is
keeping them apart.

The obvious suspect is the response schema. Every stage sends a different
`response_format` (`_Coverage`, `_Detections`, ...), and if the provider's cache
key covers the schema as well as the messages, then no two stages can ever share
a prefix however their messages are ordered — and the ordering lever is confined
to sibling calls *within* one partitioned stage.

## The design

One prompt body, long enough to clear the 1,024-token floor, and six calls:

1. `cold`            — first call, schema A. Establishes the miss.
2. `repeat_same`     — identical messages, identical schema A. If this does not
                       hit, caching is not working at all here and nothing else
                       in the table means anything. It is the positive control.
3. `same_schema_new_tail`
                     — identical opening, different trailing message, schema A.
                       This is the sibling-call case a partitioned stage
                       produces, and the case #265's ordering change is for.
4. `different_schema`
                     — identical messages, schema B. **The question.** A hit
                       means the schema is outside the key and the 0.0% has some
                       other cause; a miss means cross-stage reuse is impossible
                       by construction.
5. `different_schema_same_shape`
                     — identical messages, schema B2: same fields as A, different
                       schema *name*. Separates "the shape is in the key" from
                       "the name is in the key".
6. `different_prefix`
                     — different opening, schema A. The negative control: this
                       must miss, or the numbers are not measuring reuse.

Calls are issued in that order and the provider needs a moment to populate its
cache, so a short pause precedes the reads.

## Reading the result

`cached` is `usage.prompt_tokens_details.cached_tokens`, the same field #285
records. It is reported raw and never defaulted to zero — a provider that says
nothing about caching is `None`, which is a different claim from a measured miss.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import litellm

from acceptance.config import DEFAULT_MODEL, DEFAULT_SEED
from acceptance.llm import inline_schema_refs
from acceptance.request_blocks import SHARED_PREAMBLE


def _opening(nonce: str) -> str:
    """Long enough to clear OpenAI's 1,024-token minimum, and unique per run.

    **The nonce is load-bearing.** Without it a second run inside the provider's
    retention window starts warm: the `cold` row is not cold and the
    `different_prefix` negative control HITS, because that opening was sent by
    the previous run. That happened — the third run of this script reported 94.9%
    on every row including both controls, which is why `verdict()` refuses to
    conclude when the negative control hits.

    A fresh nonce makes every opening in a run unseen, so the run measures reuse
    it caused rather than reuse it inherited.
    """
    return "\n".join(
        f"[hunk {i}] def handler_{i}_{nonce}(payload, *, retries={i}):\n"
        f"    # normalise the {i}th field before dispatch\n"
        f"    return dispatch(payload, retries=retries, strict=True)"
        for i in range(220)
    )


def _alt_opening(nonce: str) -> str:
    return _opening(nonce).replace("handler_", "worker_").replace("dispatch", "route")


_SCHEMA_A = {
    "name": "_Coverage",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"verdict": {"type": "string"}, "why": {"type": "string"}},
        "required": ["verdict", "why"],
    },
}
# Different name AND different fields — a real other stage.
_SCHEMA_B = {
    "name": "_Detections",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "kind": {"type": "string"},
            "refs": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["kind", "refs"],
    },
}
# Same fields as A, different name only.
_SCHEMA_B2 = {**_SCHEMA_B, "name": "_Renamed", "schema": _SCHEMA_A["schema"]}


def _constrained(values: list[str]) -> dict:
    """Schema A with an id field constrained to `values` — what `constrain` builds.

    This is the shape every partitioned stage actually sends. `supplied_ids.
    constrain` restricts each id field to a `Literal` of the ids *that call*
    supplied, so two sibling calls of one stage carry the same schema NAME and
    the same fields but a different enum. Whether that difference breaks reuse is
    a separate question from the name and the shape, and it is the one that
    decides whether sibling calls can share an opening at all.
    """
    return {
        "name": "_Mappings",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "verdict": {"type": "string"},
                "why": {"type": "string"},
                "target_id": {"type": "string", "enum": values},
            },
            "required": ["verdict", "why", "target_id"],
        },
    }


def _call(messages: list[dict], schema: dict, model: str) -> dict:
    response = litellm.completion(
        drop_params=True,
        model=model,
        messages=messages,
        temperature=0.0,
        seed=DEFAULT_SEED,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema["name"],
                "schema": inline_schema_refs(schema["schema"]),
                "strict": True,
            },
        },
    )
    usage = response.usage
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details is not None else None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        # Never defaulted to 0 — see the module docstring.
        "cached_tokens": cached,
    }


def _messages(opening: str, tail: str) -> list[dict]:
    return [
        {"role": "system", "content": SHARED_PREAMBLE},
        {"role": "user", "content": opening},
        {"role": "user", "content": tail},
    ]


def run(model: str, pause: float, nonce: str) -> list[dict]:
    opening = _opening(nonce)
    base = _messages(opening, "Return a one-word verdict and a one-line reason.")
    cases = [
        ("cold", base, _SCHEMA_A),
        ("repeat_same", base, _SCHEMA_A),
        (
            "same_schema_new_tail",
            _messages(opening, "Different question entirely; answer in the schema."),
            _SCHEMA_A,
        ),
        ("different_schema", base, _SCHEMA_B),
        ("different_schema_same_shape", base, _SCHEMA_B2),
        ("different_prefix", _messages(_alt_opening(nonce), "Return a verdict."), _SCHEMA_A),
        # The sibling-call pair. Same schema name, same fields, and an id enum
        # that differs the way two batches of one partitioned stage differ. The
        # first is the cold call for this schema; the second is the question.
        ("constrained_enum_cold", base, _constrained(["a-1", "a-2", "a-3"])),
        (
            "constrained_enum_same",
            _messages(opening, "A sibling batch, same enum."),
            _constrained(["a-1", "a-2", "a-3"]),
        ),
        (
            "constrained_enum_differs",
            _messages(opening, "A sibling batch, different enum."),
            _constrained(["b-1", "b-2", "b-3"]),
        ),
    ]

    results = []
    for name, messages, schema in cases:
        time.sleep(pause)
        usage = _call(messages, schema, model)
        prompt = usage["prompt_tokens"] or 0
        cached = usage["cached_tokens"]
        share = None if cached is None else (cached / prompt if prompt else 0.0)
        results.append({"case": name, "schema": schema["name"], "share": share, **usage})
        shown = "not reported" if cached is None else f"{cached:,} ({share:.1%})"
        print(f"  {name:<28} schema={schema['name']:<12} prompt={prompt:>7,}  cached={shown}")
    return results


def verdict(results: list[dict]) -> str:
    """Two independent findings, reported together.

    They were separate branches of one `if` in the first version of this script,
    which meant the cross-stage answer returned before the sibling-call rows were
    read — and printed a conclusion about partitioned stages that the sibling
    rows contradict. They are different questions and both get answered.
    """
    return f"{_cross_stage(results)}\n\n{_sibling(results)}"


def _cross_stage(results: list[dict]) -> str:
    by_case = {r["case"]: r for r in results}

    def hit(name: str) -> bool:
        return bool(by_case[name]["cached_tokens"])

    if not hit("repeat_same"):
        return (
            "INCONCLUSIVE — the positive control missed. An identical repeat "
            "reused nothing, so this prompt is not being cached at all and no "
            "other row here is interpretable. Check the prompt length against "
            "the provider's minimum before reading anything else."
        )
    if hit("different_prefix"):
        return (
            "INCONCLUSIVE — the negative control hit. A different opening reused "
            "tokens, so these figures are not measuring prefix reuse."
        )
    if hit("different_schema") and hit("different_schema_same_shape"):
        return (
            "The response schema is NOT in the cache key. Two stages CAN share an "
            "opening, so #265's 0.0% across coverage classification and "
            "unrequested-change detection has some other cause — look next at "
            "temporal locality and at whether their openings are byte-identical "
            "in a real run."
        )
    if not hit("different_schema") and not hit("different_schema_same_shape"):
        return (
            "CROSS-STAGE: the response schema IS in the cache key, and the schema "
            "NAME alone is enough to break reuse. Two stages can never share an "
            "opening, because every stage sends a different response model."
        )
    if hit("different_schema_same_shape"):
        return (
            "CROSS-STAGE: the schema SHAPE is in the cache key but the name is "
            "not. Stages sharing a response shape could share an opening; stages "
            "with different shapes cannot."
        )
    return (
        "CROSS-STAGE: the schema NAME is in the cache key but the shape is not — "
        "an odd result, worth re-running before acting on it."
    )


def _sibling(results: list[dict]) -> str:
    """Can two batches of ONE partitioned stage share an opening?

    A separate question from the cross-stage one, because sibling calls already
    agree on the schema's name and its fields. What they do not agree on is the
    id enum `supplied_ids.constrain` embeds per call.
    """
    by_case = {r["case"]: r for r in results}
    if "constrained_enum_differs" not in by_case:
        return "SIBLING CALLS: not measured in this run."

    def hit(name: str) -> bool:
        return bool(by_case[name]["cached_tokens"])

    if not hit("constrained_enum_same"):
        return (
            "SIBLING CALLS: INCONCLUSIVE — even an IDENTICAL constrained schema "
            "missed, so the enum rows cannot be read."
        )
    if hit("constrained_enum_differs"):
        return (
            "SIBLING CALLS: they CAN share an opening. The id enum differs "
            "between batches and reuse survived it, so the ordering change pays "
            "for the partitioned stages and a low measured share has some other "
            "cause."
        )
    return (
        "SIBLING CALLS: they CANNOT share an opening. The per-call id enum that "
        "`supplied_ids.constrain` embeds is enough to break reuse, so every batch "
        "of a partitioned stage is a cache miss by construction. Prompt ordering "
        "cannot help ANY stage as things stand, and #265's lever is the "
        "constrained-decoding design rather than the prompt."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--json", type=Path, help="write the full result here")
    parser.add_argument("--pause", type=float, default=3.0, help="seconds between calls")
    parser.add_argument(
        "--nonce",
        default=None,
        help="makes this run's openings unique. Defaults to the clock; pass one "
        "explicitly only to reproduce a recorded run, which will report every "
        "row as a hit if the provider still holds it.",
    )
    args = parser.parse_args()

    if not (os.environ.get("OPENAI_API_KEY") or Path(".env").is_file()):
        print("no credentials found; this experiment makes live calls", file=sys.stderr)
        return 2

    nonce = args.nonce or f"r{int(time.time())}"
    print(f"model {args.model}, seed {DEFAULT_SEED}, temperature 0.0, nonce {nonce}")
    print(f"opening is {len(_opening(nonce)):,} chars\n")
    results = run(args.model, args.pause, nonce)

    answer = verdict(results)
    print(f"\n{answer}")

    if args.json:
        args.json.write_text(
            json.dumps(
                {"model": args.model, "nonce": nonce, "results": results, "verdict": answer},
                indent=2,
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
