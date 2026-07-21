"""`acceptance` CLI entrypoint.

Parses `check --task --base --head` plus the M0.5 determinism controls
(`--model`, `--mode`, `--seed`, `--temperature`), validates its inputs, and
runs the M0.6 walking-skeleton pipeline: ingest task + revisions → write an
empty but well-formed Review to the state store → render the §16 report.
Requirement interpretation, real diffing, and test analysis land in later
milestones; the sections render present-and-empty until then.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from acceptance.config import DEFAULT_MODEL, RunConfig
from acceptance.llm import LLMError, Mode
from acceptance.report import render_report
from acceptance.requirement.obligations import Decomposition, decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import ChangeSet, Review
from acceptance.review_store import ReviewStore


class CliError(Exception):
    """A user-facing CLI failure (bad input), not a bug."""


def _resolve_revision(revision: str, repo: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo,
        )
    except FileNotFoundError as exc:
        raise CliError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        raise CliError(f"revision not found: {revision!r}") from exc
    return result.stdout.strip()


def _read_task(task_path: str, repo: Path | None = None) -> str:
    path = Path(task_path)
    if repo is not None and not path.is_absolute():
        path = repo / path
    if not path.is_file():
        raise CliError(f"task file not found: {task_path!r}")
    return path.read_text()


def run_check(
    task: str,
    base: str,
    head: str,
    config: RunConfig,
    store: ReviewStore,
    repo: Path | None = None,
) -> Review:
    """Walking-skeleton pipeline: ingest → build empty Review → persist.

    `repo` is the git working tree to run against; it defaults to the current
    directory (the CLI's own §16 invocation has no --repo flag and always
    means "here"). The benchmark runner (M-B0.2) passes each case's own repo
    explicitly instead, since it processes many cases without changing the
    process's working directory.

    The obligation/coverage/test analysis that consumes config.build_client()
    lands in M1+. What is real here is the end-to-end shape: a task and a
    revision range in, a well-formed persisted Review out.
    """
    _read_task(task, repo=repo)
    base_sha = _resolve_revision(base, repo=repo)
    head_sha = _resolve_revision(head, repo=repo)
    review = Review(
        mode="local",
        reviewed_revision=head_sha,
        provenance=config.provenance(),
        # Diff endpoints only; real change extraction (files, diffs) is M2.
        change_set=ChangeSet(base_revision=base_sha, head_revision=head_sha),
    )
    store.write(review)
    return review


def run_decompose(task: str, config: RunConfig) -> Decomposition:
    """Parse a task file and decompose it into obligations + open questions.

    Uses a live model call (in RECORD mode) — the dogfooding path for M1.2/M1.3.
    """
    parsed = parse_task_file(_read_task(task))
    return decompose(parsed, config.build_client())


def render_decomposition(result: Decomposition) -> str:
    lines = ["Obligations:"]
    if result.obligations:
        for o in result.obligations:
            flag = "explicit" if o.explicit else "inferred"
            lines.append(f"  [{o.type.value}/{flag}] {o.id}: {o.description}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Open questions:")
    if result.open_questions:
        for q in result.open_questions:
            lines.append(f"  ? {q.id}: {q.question}")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def _add_model_flags(parser: argparse.ArgumentParser, default_mode: str) -> None:
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to route via LiteLLM (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in Mode],
        default=default_mode,
        help="record (live call on cache miss) or replay (transcripts only).",
    )
    parser.add_argument("--seed", type=int, default=None, help="Model seed (determinism).")
    parser.add_argument(
        "--temperature", type=float, default=0.0, help="Model temperature (default: 0.0)."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acceptance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run a local completion check.")
    check.add_argument("--task", required=True, help="Path to the task file.")
    check.add_argument("--base", required=True, help="Base Git revision.")
    check.add_argument("--head", required=True, help="Head Git revision.")
    _add_model_flags(check, default_mode=Mode.REPLAY.value)  # never call live unbidden
    check.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured Review as JSON instead of the §16 report.",
    )

    dec = subparsers.add_parser(
        "decompose", help="Decompose a task file into obligations + open questions (live)."
    )
    dec.add_argument("--task", required=True, help="Path to the task file.")
    _add_model_flags(dec, default_mode=Mode.RECORD.value)  # dogfood: live call on cache miss
    dec.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured Decomposition as JSON.",
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
            review = run_check(args.task, args.base, args.head, config, ReviewStore())
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(review.to_dict(), indent=2))
        else:
            print(render_report(review))
        return 0

    if args.command == "decompose":
        config = RunConfig(
            model=args.model,
            mode=Mode(args.mode),
            seed=args.seed,
            temperature=args.temperature,
        )
        try:
            result = run_decompose(args.task, config)
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        except LLMError as exc:
            print(f"acceptance: model error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(render_decomposition(result))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
