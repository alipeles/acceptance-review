"""Probe, second pass: the same question through the OpenAI SDK directly.

The first pass (``probe_mini_logprobs.py``) went through LiteLLM and saw no
runner-up token at the answer position. This pass rules LiteLLM out and dumps
the raw ``logprobs`` block, on a question whose answer is not obvious so the
runner-up should carry visible probability.

Run live once:  .venv/bin/python docs/experiments/jev/m52/probe_mini_logprobs_raw.py
"""

from __future__ import annotations

import json
import sys

from openai import OpenAI

MODEL = "gpt-5.4-mini"

QUESTION = (
    "Test:\n"
    "def test_parse():\n"
    "    assert parse('1,2') is not None\n\n"
    "Defect: in parse(s), `s.split(',')` is replaced with `s.split(';')`.\n\n"
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


def _dump(label: str, response) -> None:
    choice = response.choices[0]
    print(f"== {label}")
    print(f"content: {choice.message.content!r}  finish: {choice.finish_reason}")
    lp = choice.logprobs
    if lp is None or not lp.content:
        print("no logprobs returned")
        return
    for tok in lp.content:
        alts = [(a.token, round(a.logprob, 4)) for a in (tok.top_logprobs or [])]
        print(f"{tok.token!r:>12} {tok.logprob:9.4f}  top={alts}")


def main() -> int:
    client = OpenAI()
    cases = {
        "text": {
            "messages": [
                {"role": "system", "content": "Answer with exactly one word: yes or no."},
                {"role": "user", "content": QUESTION},
            ],
            "max_completion_tokens": 4,
        },
        "schema": {
            "messages": [
                {"role": "system", "content": "Answer in the given JSON shape."},
                {"role": "user", "content": QUESTION},
            ],
            "response_format": SCHEMA,
        },
    }
    for label, kwargs in cases.items():
        try:
            r = client.chat.completions.create(
                model=MODEL,
                logprobs=True,
                top_logprobs=5,
                reasoning_effort="none",
                **kwargs,
            )
            _dump(label, r)
        except Exception as exc:  # noqa: BLE001 — the probe records the failure
            print(f"== {label}\nerror: {type(exc).__name__}: {json.dumps(str(exc))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
