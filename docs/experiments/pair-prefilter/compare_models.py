"""Compare embedding configurations, and check the headline is not one outlier.

`best lossless` — the most a filter excludes while keeping every recorded kill —
is a minimum statistic. It is set by the single lowest-scoring kill, so one
unlucky pair drags a configuration to near zero even when the rest of its
distribution separates cleanly. That makes it the right bar for *adopting* a
filter, because one skipped kill is the failure mode #312 exists to remove, and
the wrong bar for *comparing models*, because it throws away everything except
the worst case.

So this prints both: the lossless figure the decision turns on, and the figure
at one and at three kills lost, which says whether a low score is a bad model or
a single awkward pair.

Reads `findings.json`; makes no call.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def at_most_lost(curve: list[dict], allowed: int, kills: int) -> dict | None:
    """The most a filter excludes while losing no more than `allowed` kills."""
    feasible = [point for point in curve if kills - point["kills_kept"] <= allowed]
    return max(feasible, key=lambda point: point["excluded_share"]) if feasible else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, default=HERE / "findings.json")
    args = parser.parse_args()
    findings = json.loads(args.findings.read_text())
    kills = findings["kills"]

    configurations = [
        (label, block)
        for label, block in findings.items()
        if isinstance(block, dict) and "union" in block
    ]

    print(f"{findings['pairs']:,} pairs, {kills} kills, run {findings['run_id']}\n")
    print("union, rejecting a pair only when every filter rejects it:")
    for label, block in sorted(configurations, key=lambda row: -row[1]["union"]["excluded_share"]):
        print(f"  {label:<32} {block['union']['excluded_share']:6.1%}")

    for allowed in (0, 1, 3):
        print(f"\nsingle filters, losing at most {allowed} of {kills} kills:")
        header = f"  {'configuration':<32} {'description':>12} {'code region':>12}"
        print(header)
        for label, block in configurations:
            cells = []
            for kind in ("description", "region"):
                point = at_most_lost(block[kind]["curve"], allowed, kills)
                cells.append(f"{point['excluded_share']:11.1%}" if point else "          -")
            print(f"  {label:<32} {cells[0]:>12} {cells[1]:>12}")

    print("\nmodels behind each configuration:")
    for label, block in configurations:
        print(
            f"  {label:<32} defects {block['defect_model']}/{block['defect_input_type']}"
            f"  code {block['code_model']}/{block['code_input_type']}"
        )


if __name__ == "__main__":
    main()
