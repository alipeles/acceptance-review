"""A minimal Jev reachability question: does the marked line run during this test?

Jev sees only the test source and the mutated implementation hunk, with the
edited line marked by a trailing comment. No change request, no file path,
no original code, no defect description, and nothing about passing or
failing: reach is decided by the test's inputs, not by the edit.

Run:  .venv/bin/python docs/experiments/jev/m52/reach_prompt.py <case-id-prefix>
Prints the request for the first tuning case matching the prefix; makes no call.
"""

from __future__ import annotations

import json
import sys

import prompts
from split import cases, load_split

MARK = "  # <-- marked line"

SITUATION = (
    "We're checking which tests execute which lines of code. We only want to know whether "
    "the marked line runs when this test runs, not whether the test passes or fails."
)

QUESTION = {
    "reaches": {
        "type": "noul",
        "instructions": "When this test runs, does the marked line execute?",
        "criteria": {
            "true": "The marked line runs at least once during the test.",
            "false": "The marked line never runs during the test.",
        },
    }
}


def marked_code(case) -> str:
    """The mutated hunk with every edited line marked."""
    # By position, not by text: the replacement text can also occur elsewhere
    # in the hunk (3 tuning cases), while the original's position is unique
    # (`prompts.mutated_hunk` refuses a hunk where it is not).
    code = prompts.mutated_hunk(case).splitlines()
    original = [o.strip() for o in case.edit.original.splitlines()]
    lines = case.implementation_hunk.splitlines()
    start = next(
        i
        for i in range(len(lines) - len(original) + 1)
        if [ln.strip() for ln in lines[i : i + len(original)]] == original
    )
    for i in range(start, start + len(case.edit.replacement.splitlines())):
        code[i] += MARK
    return "\n".join(code)


def body(case) -> dict:
    return {
        "model": "jev-latest",
        "state": {
            "situation": SITUATION,
            "test_source": case.test_source,
            "code": marked_code(case),
        },
        "questions": QUESTION,
    }


def main() -> int:
    prefix = sys.argv[1]
    tuning = set(load_split()["tuning"])
    case = next(c for c in cases() if c.case_id in tuning and c.case_id.startswith(prefix))
    print(json.dumps(body(case), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
