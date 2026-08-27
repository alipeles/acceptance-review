"""How much of the obligation set comes from the `# Task` block, and how much of
that restates a bullet.

Reads the cached reviews in `.acceptance/cache/reviews/`, which carry both the
requirement map (requirement -> obligation ids) and the obligation list. Answers
two questions behind §10 of `findings.md`:

  1. what share of obligations `task-*` requirements produce;
  2. how close each task-derived obligation is to the nearest bullet-derived one.

(2) is a LEXICAL PROXY — Jaccard over content words — and it is weak evidence:
a paraphrase of the same requirement scores low. Read it as "does not support
the claim that the Task block only restates the bullets", never as a refutation
of the reverse. The real instrument is the linking stage's own merge judgement.

Run from the repo root.
"""

from __future__ import annotations

import collections
import glob
import json
import re

STOP = set(
    "the a an and or of to in is are be that this it for as with by on not no any "
    "each every its their from at than then when where which".split()
)


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(1, len(left | right))


def main() -> None:
    task_obligations = all_obligations = reviews = 0
    buckets = collections.Counter()
    scores = []

    for path in glob.glob(".acceptance/cache/reviews/*"):
        try:
            review = json.load(open(path))
        except (ValueError, OSError):
            continue
        dispositions = (review.get("requirement_map") or {}).get("dispositions") or []
        obligations = review.get("obligation_map") or []
        if not dispositions or not isinstance(obligations, list) or not obligations:
            continue
        reviews += 1
        described = {o["id"]: o.get("description", "") for o in obligations if isinstance(o, dict)}

        from_task, everything = set(), set()
        for entry in dispositions:
            ids = set(entry.get("obligation_ids") or [])
            everything |= ids
            if entry["requirement_id"].startswith("task-"):
                from_task |= ids
        task_obligations += len(from_task)
        all_obligations += len(everything)

        bullets = [content_words(described[i]) for i in everything - from_task if described.get(i)]
        for identifier in from_task:
            words = content_words(described.get(identifier, ""))
            if not words or not bullets:
                continue
            closest = max(jaccard(words, other) for other in bullets)
            scores.append(closest)
            buckets[">=0.5" if closest >= 0.5 else ">=0.35" if closest >= 0.35 else "<0.35"] += 1

    print(f"reviews carrying a requirement map: {reviews}")
    share = 100 * task_obligations / max(1, all_obligations)
    print(f"obligations from task-* requirements: {task_obligations} / {all_obligations} ({share:.0f}%)")
    print(f"\nnearest bullet-derived obligation, by lexical overlap (n={len(scores)}):")
    for bucket in (">=0.5", ">=0.35", "<0.35"):
        print(f"  {bucket:>6}: {buckets[bucket]}")
    if scores:
        scores.sort()
        print(f"  median: {scores[len(scores) // 2]:.2f}")


if __name__ == "__main__":
    main()
