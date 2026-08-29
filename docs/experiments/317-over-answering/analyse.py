"""Does a decompose batch answer only for the requirements it was asked for?

Reads `.acceptance/cache/transcripts/` and classifies every obligation in every
batched decompose response by where its `source_quote` lands: inside the
requirement it was filed under (`own`), inside another requirement the call was
asked to answer for (`batch`), inside one shown only as context (`foreign`), or
nowhere in the registry (`unplaced`).

Everything it needs is inside the transcript — the registry text and the
answer-for list are both in the request — so it needs no repo state and no live
call. Run from the repo root.
"""

from __future__ import annotations

import collections
import json
import os
import re
from math import comb

TRANSCRIPTS = ".acceptance/cache/transcripts"
ID_LINE = re.compile(r"^\[([^\]]+)\] \((\w+)\) \[(ANSWER FOR THIS|context only)\] ", re.MULTILINE)
ASKED = re.compile(
    r"Return exactly one disposition for each of these requirement ids, "
    r"and for no others:\n\n(.+?)\n"
)


def normalise(text: str) -> str:
    return " ".join(text.split())


def registry_texts(subject: str) -> dict[str, str]:
    """Each requirement id mapped to its text, as the request carried it."""
    marks = list(ID_LINE.finditer(subject))
    tail = subject.find("\nReturn exactly one disposition")
    texts = {}
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else tail
        texts[mark.group(1)] = normalise(subject[mark.end() : end])
    return texts


def obligations_of(entry: dict) -> list[dict]:
    if entry.get("disposition") != "yielded":
        return []
    head = [entry["obligation"]] if entry.get("obligation") else []
    return head + (entry.get("more_obligations") or [])


def classify(quote: str, filed_under: str, asked: set[str], texts: dict[str, str]) -> str:
    quote = normalise(quote)
    if not quote:
        return "unplaced"
    if quote in texts.get(filed_under, ""):
        return "own"
    if any(quote in texts.get(rid, "") for rid in asked):
        return "batch"
    if any(quote in text for rid, text in texts.items() if rid not in asked):
        return "foreign"
    return "unplaced"


def calls() -> list[dict]:
    found = []
    for name in sorted(os.listdir(TRANSCRIPTS)):
        path = os.path.join(TRANSCRIPTS, name)
        try:
            with open(path) as handle:
                record = json.load(handle)
        except (ValueError, OSError):
            continue
        request = record.get("request", {})
        schema = request.get("response_schema") or {}
        if not isinstance(schema, dict) or schema.get("name") != "_Decomposition":
            continue
        subject = request["messages"][-1]["content"]
        match = ASKED.search(subject)
        if match is None:  # pre-partitioning recording
            continue
        asked = {value.strip() for value in match.group(1).split(",")}
        texts = registry_texts(subject)
        try:
            body = json.loads(record["response"])
        except (ValueError, KeyError):
            continue
        dispositions = body.get("requirement_dispositions", [])

        tally = collections.Counter()
        per_entry = []
        for entry in dispositions:
            kinds = [
                classify(item["source_quote"], entry["requirement_id"], asked, texts)
                for item in obligations_of(entry)
            ]
            tally.update(kinds)
            per_entry.append((entry["requirement_id"], entry["disposition"], kinds))

        returned = [entry["requirement_id"] for entry in dispositions]
        counted = collections.Counter(returned)
        found.append(
            {
                "id": name[:8],
                "asked": sorted(asked),
                "registry": len(texts),
                "dispositions": len(dispositions),
                "duplicates": sum(n - 1 for n in counted.values() if n > 1),
                "obligations": sum(tally.values()),
                "foreign": tally["foreign"],
                "unplaced": tally["unplaced"],
                "has_task": any(rid.startswith("task-") for rid in asked),
                "entries": per_entry,
            }
        )
    return found


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    total, row, col = a + b + c + d, a + b, a + c
    return sum(
        comb(row, k) * comb(c + d, col - k) / comb(total, col) for k in range(a, min(row, col) + 1)
    )


def main() -> None:
    rows = calls()
    bad = [row for row in rows if row["foreign"]]
    print(f"batched decompose calls: {len(rows)}    over-answering: {len(bad)}\n")

    print(f"{'call':9} {'reg':>3} {'ask':>3} {'disp':>4} {'dup':>3} {'obl':>3} {'fgn':>3}  asked")
    for row in sorted(bad, key=lambda r: -r["foreign"]):
        print(
            f"{row['id']:9} {row['registry']:>3} {len(row['asked']):>3} "
            f"{row['dispositions']:>4} {row['duplicates']:>3} {row['obligations']:>3} "
            f"{row['foreign']:>3}  {','.join(row['asked'])[:64]}"
        )

    task = [row for row in rows if row["has_task"]]
    rest = [row for row in rows if not row["has_task"]]
    a, c = len([r for r in task if r["foreign"]]), len([r for r in rest if r["foreign"]])
    b, d = len(task) - a, len(rest) - c
    print(f"\nbatch contains a task-* requirement : {a:>3} / {len(task)}")
    print(f"batch contains no task-* requirement: {c:>3} / {len(rest)}")
    print(f"Fisher exact, one-sided            : p = {fisher_one_sided(a, b, c, d):.5f}")

    print("\nper-disposition breakdown of the over-answering calls:")
    for row in sorted(bad, key=lambda r: -r["foreign"]):
        print(f"--- {row['id']}  asked={row['asked']}")
        for index, (rid, disposition, kinds) in enumerate(row["entries"]):
            print(f"   [{index:>2}] {rid:16} {disposition:13} {dict(collections.Counter(kinds))}")


if __name__ == "__main__":
    main()
