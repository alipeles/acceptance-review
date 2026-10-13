"""Probe: does a Jev yes/no question work with our key, and what comes back?

The same toy question the Mini probe used (``probe_mini_logprobs_raw.py``), so
the two answers can be compared. No BugsInPy content.

Request shape from https://docs.typesafe.ai/api.md: ``questions`` is a map
keyed by question id; a yes/no ("noul") answer is ``answers[id].noul``, the
probability of yes.

Run live once:  .venv/bin/python docs/experiments/jev/m52/probe_jev.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from keys import key

URL = "https://api.typesafe.ai/v1/systemone"

STATE = {
    "test_source": "def test_parse():\n    assert parse('1,2') is not None\n",
    "defect": "In parse(s), `s.split(',')` is replaced with `s.split(';')`.",
}

BODY = {
    "model": "jev-latest",
    "state": STATE,
    "questions": {
        "fails": {
            "type": "noul",
            "instructions": "Would this test fail with the defect in place?",
            "criteria": {
                "true": "Running the test with the defect in place raises or fails an assertion.",
                "false": "The test still passes with the defect in place.",
            },
        }
    },
}


def main() -> int:
    headers = {"Authorization": f"Bearer {key('TYPESAFE_API_KEY')}"}
    start = time.monotonic()
    r = httpx.post(URL, json=BODY, headers=headers, timeout=30)
    elapsed_ms = (time.monotonic() - start) * 1000
    print(f"status: {r.status_code}  elapsed_ms: {elapsed_ms:.0f}")
    try:
        print(json.dumps(r.json(), indent=2))
    except ValueError:
        print(r.text[:2000])
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
