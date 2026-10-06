"""`python -m acceptance.benchmark.mutants <command>` — build #372's label set.

    prepare   fetch pinned bugs and build project environments (needs network)
    build     run every test against every mutant, offline, and write labels.json
    sample    draw the survivor sample for a person to check
    report    print counts and rates (committable; nothing from BugsInPy itself)

Everything is read from and written to `.acceptance/mutant-labels/` (gitignored).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from acceptance.benchmark.mutants.bugsinpy import load_pinned_bugs
from acceptance.benchmark.mutants.build import build, write_labels
from acceptance.benchmark.mutants.labels import load_mutant_labels, load_survivor_sample
from acceptance.benchmark.mutants.prepare import LabelPaths, prepare
from acceptance.benchmark.mutants.survivors import (
    draw_survivor_sample,
    render_sample,
    summarise,
)
from acceptance.serialization import canonical_json

DEFAULT_ROOT = Path(".acceptance/mutant-labels")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m acceptance.benchmark.mutants")
    parser.add_argument("command", choices=["prepare", "build", "sample", "report"])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--size", type=int, default=30, help="survivor sample size")
    parser.add_argument("--seed", type=int, default=372, help="survivor sample seed")
    args = parser.parse_args(argv)

    pins = load_pinned_bugs()
    paths = LabelPaths(args.root)

    if args.command == "prepare":
        return 1 if prepare(pins, paths) else 0
    if args.command == "build":
        labels = build(pins, paths)
        write_labels(labels, paths.labels)
        print(json.dumps(summarise(labels), indent=2))
        return 0

    labels = load_mutant_labels(paths.labels)
    if args.command == "sample":
        if paths.sample.exists():
            print(f"{paths.sample} exists; delete it to draw again", file=sys.stderr)
            return 1
        sample = draw_survivor_sample(labels, args.size, args.seed)
        paths.sample.write_text(canonical_json(sample.to_dict()) + "\n", encoding="utf-8")
        page = paths.root / "survivor-sample.md"
        page.write_text(render_sample(labels, sample), encoding="utf-8")
        print(f"wrote {paths.sample} and {page}")
        return 0

    sample = load_survivor_sample(paths.sample) if paths.sample.exists() else None
    print(json.dumps(summarise(labels, sample), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
