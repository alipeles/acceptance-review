"""Show the start of requirement_text for tuning cases lacking a diff separator.

Run:  .venv/bin/python docs/experiments/jev/m52/show_requirements.py
"""

from __future__ import annotations

import sys
from collections import Counter

from split import cases, load_split


def main() -> int:
    tuning = set(load_split()["tuning"])
    odd = [c for c in cases() if c.case_id in tuning and "\n---\n" not in c.requirement_text]
    print(f"tuning cases without separator: {len(odd)}")
    print("by project:", dict(Counter(c.project for c in odd)))
    seen = set()
    for c in odd:
        if (c.project, c.bug_id) in seen:
            continue
        seen.add((c.project, c.bug_id))
        text = c.requirement_text
        print(f"=== {c.project}/{c.bug_id}  ({len(text)} chars)")
        print(text[:400])
        if len(seen) >= 3:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
