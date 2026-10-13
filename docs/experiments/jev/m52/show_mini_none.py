"""Count what Mini's first token was when it gave neither yes nor no.

Replays recordings only.  Run:  .venv/bin/python docs/experiments/jev/m52/show_mini_none.py
"""

from __future__ import annotations

import sys
from collections import Counter

import prompts
import recorder
from split import cases, load_split


def main() -> int:
    tuning = set(load_split()["tuning"])
    firsts: Counter = Counter()
    contents: Counter = Counter()
    for c in cases():
        if c.case_id not in tuning:
            continue
        try:
            prompts.mutated_hunk(c)
        except prompts.CannotBuild:
            continue
        for v in prompts.VARIANTS:
            rec = recorder.mini(
                recorder.mini_request(prompts.mini_messages(c, v)), replay_only=True
            )
            if recorder.mini_p_yes(rec) is None:
                toks = rec["response"]["tokens"]
                firsts[repr(toks[0]["top"]) if toks else "<no tokens>"] += 1
                contents[repr(rec["response"]["content"])] += 1
                if sum(contents.values()) == 1:
                    print("finish:", rec["response"]["finish_reason"])
                    print("usage:", rec["response"]["usage"])
    print("content:", contents.most_common(10))
    for k, n in firsts.most_common(8):
        print(n, k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
