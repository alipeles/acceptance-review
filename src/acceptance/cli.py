"""`acceptance` CLI entrypoint.

Stage 1, M0.1: parses `check --task --base --head`, validates its inputs, and
exits cleanly with an empty structured Review. Requirement interpretation,
diffing, and reporting land in later M0/M1/M2 milestones.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from acceptance.review_state import Review


class CliError(Exception):
    """A user-facing CLI failure (bad input), not a bug."""


def _resolve_revision(revision: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise CliError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        raise CliError(f"revision not found: {revision!r}") from exc
    return result.stdout.strip()


def _read_task(task_path: str) -> str:
    path = Path(task_path)
    if not path.is_file():
        raise CliError(f"task file not found: {task_path!r}")
    return path.read_text()


def run_check(task: str, base: str, head: str) -> Review:
    _read_task(task)
    _resolve_revision(base)
    head_sha = _resolve_revision(head)
    return Review(mode="local", reviewed_revision=head_sha)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acceptance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run a local completion check.")
    check.add_argument("--task", required=True, help="Path to the task file.")
    check.add_argument("--base", required=True, help="Base Git revision.")
    check.add_argument("--head", required=True, help="Head Git revision.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            review = run_check(args.task, args.base, args.head)
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(review.to_dict(), indent=2))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
