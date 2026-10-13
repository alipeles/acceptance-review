"""Probe: does GPT-5.4 Mini return token probabilities, runner-up included?

Deliverable 1 of #379. Approach D needs the probability of both answers at the
answer token, so a reply carrying only the chosen token's probability is not
enough. Two answer shapes are tried on one toy question (no BugsInPy content):

- ``text``: a one-token yes/no answer, ``max_tokens=1``.
- ``schema``: the structured-output shape the harness uses, ``{"fails": bool}``,
  reading the probabilities at the ``true``/``false`` token.

Run live once:  .venv/bin/python docs/experiments/jev/m52/probe_mini_logprobs.py
"""

from __future__ import annotations

import json
import math
import sys

import litellm

MODEL = "openai/gpt-5.4-mini"
TOP = 5

QUESTION = (
    "Test:\n"
    "def test_add():\n"
    "    assert add(2, 3) == 5\n\n"
    "Defect: in add(a, b), `a + b` is replaced with `a - b`.\n\n"
    "Would this test fail with the defect in place?"
)

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"fails": {"type": "boolean"}},
            "required": ["fails"],
            "additionalProperties": False,
        },
    },
}


def _call(messages: list[dict], **extra) -> object:
    return litellm.completion(
        model=MODEL,
        messages=messages,
        logprobs=True,
        top_logprobs=TOP,
        reasoning_effort="none",
        **extra,
    )


def _tokens(response) -> list:
    choice = response.choices[0]
    lp = getattr(choice, "logprobs", None)
    if lp is None:
        return []
    content = lp.get("content") if isinstance(lp, dict) else getattr(lp, "content", None)
    return content or []


def _field(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name)


def _report(label: str, response, answer_tokens: set[str]) -> bool:
    text = response.choices[0].message.content
    print(f"== {label}")
    print(f"content: {text!r}")
    tokens = _tokens(response)
    if not tokens:
        print("no logprobs returned")
        return False
    print(f"tokens with logprobs: {len(tokens)}")
    found = False
    for tok in tokens:
        token = _field(tok, "token")
        if token.strip().lower() not in answer_tokens:
            continue
        found = True
        top = _field(tok, "top_logprobs") or []
        print(f"answer token {token!r}  p={math.exp(_field(tok, 'logprob')):.6f}")
        for alt in top:
            alt_token = _field(alt, "token")
            print(f"  alt {alt_token!r}  p={math.exp(_field(alt, 'logprob')):.6f}")
        runner_up = [a for a in top if _field(a, "token") != token]
        print(f"runner-up present: {bool(runner_up)}")
        return bool(runner_up)
    if not found:
        print("answer token not found in logprobs")
    return False


def main() -> int:
    results = {}
    text_messages = [
        {"role": "system", "content": "Answer with exactly one word: yes or no."},
        {"role": "user", "content": QUESTION},
    ]
    try:
        r = _call(text_messages, max_tokens=1)
        results["text"] = _report("text", r, {"yes", "no"})
    except Exception as exc:  # noqa: BLE001 — the probe records the failure
        print(f"== text\nerror: {type(exc).__name__}: {exc}")
        results["text"] = False

    schema_messages = [
        {"role": "system", "content": "Answer in the given JSON shape."},
        {"role": "user", "content": QUESTION},
    ]
    try:
        r = _call(schema_messages, response_format=SCHEMA)
        results["schema"] = _report("schema", r, {"true", "false"})
    except Exception as exc:  # noqa: BLE001 — the probe records the failure
        print(f"== schema\nerror: {type(exc).__name__}: {exc}")
        results["schema"] = False

    print("== summary")
    print(json.dumps(results))
    return 0 if any(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
