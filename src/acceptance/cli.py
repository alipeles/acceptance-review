"""`acceptance` CLI entrypoint.

Parses `check --task --base --head` plus the M0.5 determinism controls
(`--model`, `--mode`, `--seed`, `--temperature`), validates its inputs, and
exits cleanly with an empty structured Review stamped with how it was produced.
Requirement interpretation, diffing, and the §16 report land in later
milestones; the pipeline that actually consumes the model client is M0.6.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from acceptance.config import DEFAULT_MODEL, RunConfig
from acceptance.llm import Mode
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


def run_check(task: str, base: str, head: str, config: RunConfig) -> Review:
    _read_task(task)
    _resolve_revision(base)
    head_sha = _resolve_revision(head)
    # No-op pipeline for now: the analysis that consumes config.build_client()
    # is M0.6+. What M0.5 delivers is that the review records how it was
    # produced, so two runs of the same input are provably reproducible.
    return Review(
        mode="local",
        reviewed_revision=head_sha,
        provenance=config.provenance(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acceptance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run a local completion check.")
    check.add_argument("--task", required=True, help="Path to the task file.")
    check.add_argument("--base", required=True, help="Base Git revision.")
    check.add_argument("--head", required=True, help="Head Git revision.")
    check.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to route via LiteLLM (default: {DEFAULT_MODEL}).",
    )
    check.add_argument(
        "--mode",
        choices=[m.value for m in Mode],
        default=Mode.REPLAY.value,
        help="record (live call on cache miss) or replay (transcripts only). "
        "Default: replay — never issues a live call.",
    )
    check.add_argument("--seed", type=int, default=None, help="Model seed (determinism).")
    check.add_argument(
        "--temperature", type=float, default=0.0, help="Model temperature (default: 0.0)."
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        config = RunConfig(
            model=args.model,
            mode=Mode(args.mode),
            seed=args.seed,
            temperature=args.temperature,
        )
        try:
            review = run_check(args.task, args.base, args.head, config)
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(review.to_dict(), indent=2))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
