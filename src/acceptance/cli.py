"""`acceptance` CLI entrypoint.

`check --task --base --head` runs the M0.6 walking-skeleton pipeline: ingest
task + revisions → write an empty but well-formed Review → render the §16
report. Its sections render present-and-empty until the capabilities that
fill them (M1-M7) are assembled into the pipeline.

`decompose` and `diff` are standalone dogfooding entry points for those
capabilities as they land — `decompose` runs the real M1.2/M1.3 obligation
decomposition against a task file (live model call); `diff` runs the real
M2.1 change-set extraction against two revisions. Neither is wired into
`check` yet; that assembly happens later (M7).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from acceptance.change.diff import extract_change_set, extract_working_tree_change_set
from acceptance.config import DEFAULT_MODEL, RunConfig
from acceptance.coverage.classify import ImplementationCoverage, classify_coverage
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.unrequested import detect_unrequested_changes
from acceptance.llm import LLMError, Mode
from acceptance.report import render_report
from acceptance.requirement.obligations import Decomposition, Obligation, decompose
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
        # Diff endpoints only; real extraction exists (change/diff.py, dogfooded
        # via `acceptance diff`) but isn't wired into this pipeline yet (M7).
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


def run_diff(repo: str, base: str, head: str | None) -> ChangeSet:
    """Extract the structural change set (M2.1), or against the working tree
    when `head` is omitted (M2.3, §5.1 — works before a PR/commit exists)."""
    repo_path = Path(repo)
    base_sha = _resolve_revision(base, repo=repo_path)
    if head is None:
        return extract_working_tree_change_set(repo_path, base_sha)
    head_sha = _resolve_revision(head, repo=repo_path)
    return extract_change_set(repo_path, base_sha, head_sha)


def render_change_set(change_set: ChangeSet) -> str:
    lines = [
        f"Base: {change_set.base_revision}  Head: {change_set.head_revision}",
        f"Files changed ({len(change_set.files)}):",
    ]
    if not change_set.files:
        lines.append("  (none)")
    for f in change_set.files:
        origin = f" (from {f.old_path})" if f.old_path else ""
        hunk_count = len(f.hunks)
        lines.append(
            f"  [{f.category}/{f.status}] {f.path}{origin}  "
            f"({hunk_count} hunk{'' if hunk_count == 1 else 's'})"
        )
    if change_set.ignored_paths:
        lines.append(f"Ignored by .acceptance/ignore ({len(change_set.ignored_paths)}):")
        for path in change_set.ignored_paths:
            lines.append(f"  {path}")
    return "\n".join(lines)


def run_classify(
    task: str, base: str, head: str | None, config: RunConfig, repo: str = "."
) -> tuple[list[Obligation], list[ImplementationCoverage], list[DispositionedChange]]:
    """Decompose a task, extract its change set, classify each obligation against
    the diff, flag unrequested changes and classify their dispositions — a live
    end-to-end dogfood of M1 + M2 + M3.1 + M3.2 + M3.5.3."""
    repo_path = Path(repo)
    parsed = parse_task_file(_read_task(task))
    obligations = decompose(parsed, config.build_client()).obligations

    base_sha = _resolve_revision(base, repo=repo_path)
    if head is None:
        change_set = extract_working_tree_change_set(repo_path, base_sha)
    else:
        head_sha = _resolve_revision(head, repo=repo_path)
        change_set = extract_change_set(repo_path, base_sha, head_sha)

    coverages = classify_coverage(obligations, change_set, config.build_client())
    unrequested = detect_unrequested_changes(obligations, change_set, config.build_client())
    dispositioned = classify_dispositions(
        unrequested, obligations, coverages, change_set,
        config.scope_expansion_policy, config.build_client(),
    )
    return obligations, coverages, dispositioned


def render_classify(
    obligations: list[Obligation],
    coverages: list[ImplementationCoverage],
    dispositioned: list[DispositionedChange],
) -> str:
    descriptions = {o.id: o.description for o in obligations}
    lines = ["Implementation coverage (code only — not test evidence):"]
    if not coverages:
        lines.append("  (none)")
    for cov in coverages:
        refs = ", ".join(f"{r.file}" for r in cov.diff_refs) or "no corresponding change"
        lines.append(f"  [{cov.status.value}] {cov.obligation_id}: {descriptions.get(cov.obligation_id, '')}")
        lines.append(f"      -> {refs}")
    lines.append("")
    lines.append("Unrequested changes (no obligation calls for these — your call):")
    if not dispositioned:
        lines.append("  (none)")
    for item in dispositioned:
        change = item.change
        refs = ", ".join(f"{r.file}" for r in change.diff_refs) or "?"
        lines.append(f"  [{item.disposition.value}] ({change.kind.value}) {change.rationale}")
        lines.append(f"      -> {refs}")
        if item.recommendation:
            lines.append(f"      recommendation: {item.recommendation}")
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

    diff = subparsers.add_parser(
        "diff", help="Extract the structural change set between two revisions."
    )
    diff.add_argument("--repo", default=".", help="Path to the Git repo (default: here).")
    diff.add_argument("--base", required=True, help="Base Git revision.")
    diff.add_argument(
        "--head",
        default=None,
        help="Head Git revision. Omit to diff against the working tree (§5.1).",
    )
    diff.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured ChangeSet as JSON.",
    )

    classify = subparsers.add_parser(
        "classify",
        help="Decompose a task, diff a change, and classify each obligation "
        "against the diff (implementation coverage, live).",
    )
    classify.add_argument("--task", required=True, help="Path to the task file.")
    classify.add_argument("--repo", default=".", help="Path to the Git repo (default: here).")
    classify.add_argument("--base", required=True, help="Base Git revision.")
    classify.add_argument(
        "--head",
        default=None,
        help="Head Git revision. Omit to use the working tree (§5.1).",
    )
    _add_model_flags(classify, default_mode=Mode.RECORD.value)
    classify.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured coverage classifications as JSON.",
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

    if args.command == "diff":
        try:
            change_set = run_diff(args.repo, args.base, args.head)
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(change_set.to_dict(), indent=2))
        else:
            print(render_change_set(change_set))
        return 0

    if args.command == "classify":
        config = RunConfig(
            model=args.model,
            mode=Mode(args.mode),
            seed=args.seed,
            temperature=args.temperature,
        )
        try:
            obligations, coverages, dispositioned = run_classify(
                args.task, args.base, args.head, config, args.repo
            )
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        except LLMError as exc:
            print(f"acceptance: model error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(
                json.dumps(
                    {
                        "coverage": [c.to_dict() for c in coverages],
                        "unrequested_changes": [d.to_dict() for d in dispositioned],
                    },
                    indent=2,
                )
            )
        else:
            print(render_classify(obligations, coverages, dispositioned))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
