"""Score the edit verifier on the hand-labelled injection audits, for one model.

#416: run Claude beside GPT-5.4 on the existing labels before any routing
change. The edit verifier is `mutation/verification.py`: one model call per
injected edit, asking whether the edit really puts its named defect into the
code. Its GPT-5.4 figures in DR-171 are 27 of 35 bad edits refused and 8 of 31
good edits refused on audit v6, and 16 of 21 and 5 of 31 on audit v10.

Both audits edited revision 518f876, and both used the defect list stored in
`injection-audit-v6.defects.json`. v6's edits survive only as diffs in its
Markdown, so they are parsed back into descriptors and each one is checked
against the source at 518f876 before it is asked about. v10's edits are in its
attempts dump. The verifier prompt has changed since both figures were taken,
so a fair comparison re-runs GPT-5.4 on today's prompt as well; `--model`
picks the arm.

Usage:
    .venv/bin/python docs/experiments/416-claude-shadow/score_verifier.py \
        --audit v6 --model anthropic/claude-sonnet-5-5 --mode record
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from acceptance.config import RunConfig
from acceptance.llm import Mode
from acceptance.mutation.attempt import MutationDescriptor
from acceptance.mutation.verification import verify_edits
from acceptance.review_state import Defect
from acceptance.usage import render, summarize

AUDITS = Path("dogfood-logs/45-injection-audits")
REVISION = "518f876"
HERE = Path(__file__).parent

#: v10's judging passes name what an edit did; only `injects` is a good edit.
GOOD_V10 = {"injects"}

_SECTION = re.compile(r"^## `(killed|survived)` — (\S+)\s*$")
_EDIT = re.compile(r"^\*\*edit\*\* — `([^`]+)` lines (\d+)-(\d+)\s*$")


def load_defects() -> dict[str, Defect]:
    sets = json.loads((AUDITS / "injection-audit-v6.defects.json").read_text())
    return {d["id"]: Defect.model_validate(d) for s in sets for d in s["defects"]}


def source_at(path: str, cache: dict[str, str]) -> str:
    if path not in cache:
        cache[path] = subprocess.run(
            ["git", "show", f"{REVISION}:{path}"], capture_output=True, text=True, check=True
        ).stdout
    return cache[path]


def v6_edits(sources: dict[str, str]) -> dict[tuple[str, str], MutationDescriptor]:
    """Each killed or survived edit in audit v6's Markdown, keyed by (defect, outcome)."""
    lines = (AUDITS / "injection-audit-v6.md").read_text().splitlines()
    edits: dict[tuple[str, str], MutationDescriptor] = {}
    key = None
    i = 0
    while i < len(lines):
        section = _SECTION.match(lines[i])
        if section:
            key = (section.group(2), section.group(1))
        elif lines[i].startswith("## "):
            key = None
        edit = _EDIT.match(lines[i])
        if edit and key:
            path, start, end = edit.group(1), int(edit.group(2)), int(edit.group(3))
            i += 1
            while not lines[i].startswith("```diff"):
                i += 1
            removed, added = [], []
            i += 1
            while not lines[i].startswith("```"):
                (removed if lines[i].startswith("-") else added).append(lines[i][1:])
                i += 1
            original = "".join(f"{line}\n" for line in removed)
            held = "".join(
                f"{line}\n" for line in source_at(path, sources).splitlines()[start - 1 : end]
            )
            if held != original:
                raise SystemExit(f"{key}: the diff does not match {path} at {REVISION}")
            edits[key] = MutationDescriptor(
                path=path,
                start_line=start,
                end_line=end,
                original=original,
                replacement="".join(f"{line}\n" for line in added),
                region_label=f"{path}#0",
            )
        i += 1
    return edits


def cases(audit: str, sources: dict[str, str]) -> list[tuple[str, bool, MutationDescriptor]]:
    """(defect id, edit is good, edit) for every labelled kill or survival."""
    labels = json.loads((AUDITS / "labels" / f"{audit}.json").read_text())["labels"]
    if audit == "v6":
        edits = v6_edits(sources)
        return [
            (
                label["defect_id"],
                label["edit"] == "good",
                edits[(label["defect_id"], label["outcome"])],
            )
            for label in labels
        ]
    attempts = json.loads((AUDITS / f"injection-audit-{audit}.attempts.json").read_text())
    by_id = {a["defect_id"]: a for a in attempts["attempts"]}
    return [
        (
            label["defect_id"],
            label["edit"] in GOOD_V10,
            MutationDescriptor.model_validate(by_id[label["defect_id"]]["descriptor"]),
        )
        for label in labels
        if label["outcome"] in {"killed", "survived"}
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", choices=["v6", "v10"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", choices=["record", "replay"], default="replay")
    args = parser.parse_args(argv)

    defects = load_defects()
    sources: dict[str, str] = {}
    labelled = cases(args.audit, sources)
    for _, _, descriptor in labelled:
        source_at(descriptor.path, sources)

    client = RunConfig(
        model=args.model, mode=Mode.RECORD if args.mode == "record" else Mode.REPLAY
    ).build_client()
    verdicts = verify_edits(
        [(defects[d], descriptor, sources[descriptor.path]) for d, _, descriptor in labelled],
        client,
    )

    bad = [(d, v) for (d, good, _), v in zip(labelled, verdicts, strict=True) if not good]
    good = [(d, v) for (d, good, _), v in zip(labelled, verdicts, strict=True) if good]
    caught = sum(1 for _, v in bad if not v.verified)
    false_alarms = sum(1 for _, v in good if not v.verified)
    result = {
        "audit": args.audit,
        "model": args.model,
        "bad_edits": len(bad),
        "bad_refused": caught,
        "good_edits": len(good),
        "good_refused": false_alarms,
        "cases": [
            {
                "defect_id": d,
                "edit": "good" if is_good else "bad",
                "verified": v.verified,
                "before_does": v.before_does,
                "after_does": v.after_does,
                "reason": v.reason,
            }
            for (d, is_good, _), v in zip(labelled, verdicts, strict=True)
        ],
    }
    name = f"{args.audit}-{args.model.replace('/', '_')}.json"
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / name).write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"{args.audit} {args.model}: bad edits refused {caught} of {len(bad)} "
        f"({caught / len(bad):.0%}); good edits refused {false_alarms} of {len(good)} "
        f"({false_alarms / len(good):.0%})"
    )
    print(render(summarize(client.observed_calls)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
