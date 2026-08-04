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
from acceptance.config import (
    DEFAULT_MAPPING_BATCH_SIZE,
    DEFAULT_MODEL,
    DEFAULT_SEED,
    RunConfig,
)
from acceptance.coverage.classify import ImplementationCoverage, classify_coverage
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.open_questions import apply_open_question_resolutions, resolve_open_questions
from acceptance.coverage.unrequested import detect_unrequested_changes
from acceptance.llm import LLMError, Mode, ModelClient
from acceptance.pipeline import run_review
from acceptance.recommendation import lookup as lookup_recommendation
from acceptance.recommendation import render as render_recommendation
from acceptance.report import render_report
from acceptance.rerun import find_prior_review
from acceptance.requirement.obligations import Decomposition, Obligation, decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import ChangeSet, OpenQuestion, Review
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


def _read_declaration(declaration: str | None, repo: Path | None = None) -> str | None:
    """The optional §7.4 builder declaration's text, or None when not supplied.
    Optional by default in local mode (§7.4) — its absence is recorded as a
    minor finding by the pipeline, never an error."""
    if declaration is None:
        return None
    return _read_task(declaration, repo=repo)


def _task_ignore_pattern(task_path: str, repo: Path) -> str | None:
    """The `--task` file's path relative to `repo`, as a root-anchored
    gitignore pattern, if the file lives inside the repo — `None` otherwise
    (e.g. the benchmark runner's temp task files, which live outside any
    reviewed repo and can never appear in its diff regardless).

    The task is the specification being reviewed against, not part of the
    reviewed deliverable, so it must never appear in its own diff — not as
    a coverage claim, and never as an "unrequested change" (it always
    changes; that would be absurd to flag)."""
    resolved = Path(task_path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved
    try:
        relative = resolved.resolve().relative_to(repo.resolve())
    except ValueError:
        return None
    return "/" + relative.as_posix()


def run_check(
    task: str,
    base: str,
    head: str | None,
    config: RunConfig,
    store: ReviewStore,
    repo: Path | None = None,
    declaration: str | None = None,
    client: ModelClient | None = None,
    since: str | None = None,
) -> Review:
    """Walking-skeleton pipeline: ingest → build empty Review → persist.

    `repo` is the git working tree to run against; it defaults to the current
    directory (the CLI's own §16 invocation has no --repo flag and always
    means "here"). The benchmark runner (M-B0.2) passes each case's own repo
    explicitly instead, since it processes many cases without changing the
    process's working directory.

    Since M7.4 this runs the full shared pipeline (`pipeline.run_review`) —
    the same one the benchmark scores — so the §16 report shows real
    obligation coverage, test evidence with tiers, unrequested changes, and
    the computed verdict. `head=None` reviews the working tree (§5.1), so a
    check can run before a commit exists.
    """
    repo_path = repo if repo is not None else Path(".")
    task_text = _read_task(task, repo=repo)
    base_sha = _resolve_revision(base, repo=repo)

    # The task file is the specification, not part of the reviewed deliverable —
    # it must never appear in its own diff (same rule as run_classify).
    task_ignore = _task_ignore_pattern(task, repo_path)
    extra_patterns = [task_ignore] if task_ignore else []

    if head is None:
        change_set = extract_working_tree_change_set(
            repo_path, base_sha, extra_ignore_patterns=extra_patterns
        )
        reviewed_revision = "<working-tree>"
    else:
        reviewed_revision = _resolve_revision(head, repo=repo)
        change_set = extract_change_set(
            repo_path, base_sha, reviewed_revision, extra_ignore_patterns=extra_patterns
        )

    declaration_text = _read_declaration(declaration, repo=repo)
    # M7.5: build on the nearest prior review of an ancestor of this head, so the
    # revision cycle (§13.5 #9) re-derives only what the new work could affect.
    # `since` names one explicitly; otherwise git ancestry finds it.
    if since is not None:
        prior = store.read(_resolve_revision(since, repo=repo))
        if prior is None:
            raise CliError(f"no stored review for --since revision: {since!r}")
    else:
        # A working-tree review has no revision git can resolve, so ancestry is
        # measured against HEAD, which it descends from (§5.1).
        anchor = None if head is not None else _resolve_revision("HEAD", repo=repo)
        prior = find_prior_review(
            store, reviewed_revision, repo_path, task_text, ancestry_ref=anchor
        )

    review = run_review(
        task_text=task_text,
        change_set=change_set,
        repo=repo_path,
        client=client if client is not None else config.build_client(),
        reviewed_revision=reviewed_revision,
        declaration_text=declaration_text,
        policy=config.scope_expansion_policy,
        mapping_batch_size=config.mapping_batch_size,
        task_identifier=task,
        prior=prior,
    )
    store.write(review)
    return review


# The artifact M7.3 used to write. Nothing writes it now (M7.3.r1) — a run only
# clears one left behind by an older version.
_LEGACY_INSTRUCTION_PATH = Path(".acceptance") / "next-instruction.md"


def remove_legacy_instruction_file(repo: Path) -> Path | None:
    """Delete a `next-instruction.md` left by an older version; return its path.

    Migration, run once per repo in effect: nothing recreates the file, so the
    second run finds nothing. Deleting rather than leaving it is the point of the
    task — the file is stale by construction, and a stale file that still asserts
    gaps while the report says none contradicts the review. Both cannot be true
    and only the report is entitled to speak.

    Safe to delete without asking: it sits in `.acceptance/`, which the tool owns
    and gitignores, and it was never authored by the user. The caller reports the
    removal so it is visible rather than silent.
    """
    path = repo / _LEGACY_INSTRUCTION_PATH
    if not path.is_file():
        return None
    path.unlink()
    return _LEGACY_INSTRUCTION_PATH


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
) -> tuple[
    list[Obligation], list[OpenQuestion], list[ImplementationCoverage], list[DispositionedChange]
]:
    """Decompose a task, extract its change set, classify each obligation against
    the diff, flag unrequested changes and classify their dispositions — a live
    end-to-end dogfood of M1 + M2 + M3.1 + M3.2 + M3.5.3.

    Open questions from decomposition are carried through (not dropped at
    `.obligations`) so a reviewer sees them here too, not only when running
    `decompose` standalone (#113)."""
    repo_path = Path(repo)
    parsed = parse_task_file(_read_task(task))
    decomposition = decompose(parsed, config.build_client())
    obligations = decomposition.obligations

    task_ignore = _task_ignore_pattern(task, repo_path)
    extra_patterns = [task_ignore] if task_ignore else []

    base_sha = _resolve_revision(base, repo=repo_path)
    if head is None:
        change_set = extract_working_tree_change_set(
            repo_path, base_sha, extra_ignore_patterns=extra_patterns
        )
    else:
        head_sha = _resolve_revision(head, repo=repo_path)
        change_set = extract_change_set(
            repo_path, base_sha, head_sha, extra_ignore_patterns=extra_patterns
        )

    coverages = classify_coverage(obligations, change_set, config.build_client())
    unrequested = detect_unrequested_changes(obligations, change_set, config.build_client())
    dispositioned = classify_dispositions(
        unrequested, obligations, coverages, change_set,
        config.scope_expansion_policy, config.build_client(),
    )
    resolutions = resolve_open_questions(
        decomposition.open_questions, change_set, config.build_client()
    )
    open_questions = apply_open_question_resolutions(decomposition.open_questions, resolutions)
    return obligations, open_questions, coverages, dispositioned


def render_classify(
    obligations: list[Obligation],
    open_questions: list[OpenQuestion],
    coverages: list[ImplementationCoverage],
    dispositioned: list[DispositionedChange],
) -> str:
    descriptions = {o.id: o.description for o in obligations}
    lines = ["Open questions:"]
    if open_questions:
        for q in open_questions:
            if q.resolved:
                lines.append(f"  [resolved] {q.id}: {q.question}")
                lines.append(f"      answer: {q.resolution_rationale}")
                refs = ", ".join(link.ref for link in q.resolution_refs)
                if refs:
                    lines.append(f"      -> {refs}")
            else:
                lines.append(f"  [open] {q.id}: {q.question}")
                if q.resolution_rationale:
                    lines.append(f"      {q.resolution_rationale}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Implementation coverage (code only — not test evidence):")
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
    # Defaulted to the configured seed, not to None. argparse always supplies a
    # value and every command passes it straight into RunConfig, so a `None`
    # default here silently overrode DEFAULT_SEED and left every CLI run
    # unseeded — half the determinism strategy #154 wired up was dead on the
    # only path users invoke (#160).
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Model seed (determinism; default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Send no seed, letting the provider sample freely (variance runs).",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.0, help="Model temperature (default: 0.0)."
    )
    parser.add_argument(
        "--mapping-batch-size",
        type=int,
        default=DEFAULT_MAPPING_BATCH_SIZE,
        help=(
            "Candidate tests per mapping call (determinism; default: "
            f"{DEFAULT_MAPPING_BATCH_SIZE}). Changing it invalidates recorded "
            "mapping transcripts."
        ),
    )


def _seed_from(args: argparse.Namespace) -> int | None:
    """`--no-seed` is the deliberate way to run unpinned; absence means pinned."""
    return None if args.no_seed else args.seed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acceptance")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run a local completion check.")
    check.add_argument("--task", required=True, help="Path to the task file.")
    check.add_argument("--base", required=True, help="Base Git revision.")
    check.add_argument(
        "--head",
        default=None,
        help="Head Git revision. Omit to review the working tree (§5.1).",
    )
    check.add_argument(
        "--since",
        default=None,
        help="Revision whose stored review to build on (default: nearest ancestor with one).",
    )
    check.add_argument(
        "--declaration",
        default=None,
        help="Path to an optional §7.4 builder declaration (absence is a minor finding).",
    )
    _add_model_flags(check, default_mode=Mode.REPLAY.value)  # never call live unbidden
    rec = subparsers.add_parser(
        "recommendation",
        help="Retrieve a criterion's §9.5 test recommendation from stored review state.",
    )
    rec.add_argument("--criterion", required=True, help="The obligation id to look up.")
    rec.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output form (default: json, for pickup by a coding agent).",
    )
    rec.add_argument(
        "--revision",
        default=None,
        help="Reviewed revision to read (default: the most recently stored review).",
    )

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
            seed=_seed_from(args),
            temperature=args.temperature,
            mapping_batch_size=args.mapping_batch_size,
        )
        try:
            review = run_check(
                args.task, args.base, args.head, config, ReviewStore(),
                declaration=args.declaration, since=args.since,
            )
        except CliError as exc:
            print(f"acceptance: error: {exc}", file=sys.stderr)
            return 1
        except LLMError as exc:
            print(f"acceptance: model error: {exc}", file=sys.stderr)
            return 1
        # The CLI's §16 invocation has no --repo flag and always means "here".
        removed = remove_legacy_instruction_file(Path("."))
        if removed is not None:
            # On stderr, and so in BOTH modes. Deleting a file in the user's repo
            # must never be silent, and the first version reported it only in
            # text mode — `--json` deleted and said nothing. stderr keeps stdout
            # parseable for the agent consuming the JSON.
            print(
                f"Removed a stale {removed} left by an earlier version; "
                "recommendations are now retrieved with\n"
                "  acceptance recommendation --criterion <id>",
                file=sys.stderr,
            )
        if args.json:
            print(json.dumps(review.to_dict(), indent=2))
        else:
            print(render_report(review))
        return 0

    if args.command == "recommendation":
        store = ReviewStore()
        review = store.read(args.revision) if args.revision else store.latest()
        if review is None:
            where = f"revision {args.revision}" if args.revision else "the review store"
            print(f"acceptance: error: no stored review found for {where}", file=sys.stderr)
            return 1
        # A criterion with no recommendation is an ordinary answer, not an
        # error: a strongly-supported obligation earns none, and asking is a
        # reasonable thing for an agent to do.
        print(render_recommendation(lookup_recommendation(review, args.criterion), args.format))
        return 0

    if args.command == "decompose":
        config = RunConfig(
            model=args.model,
            mode=Mode(args.mode),
            seed=_seed_from(args),
            temperature=args.temperature,
            mapping_batch_size=args.mapping_batch_size,
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
            seed=_seed_from(args),
            temperature=args.temperature,
            mapping_batch_size=args.mapping_batch_size,
        )
        try:
            obligations, open_questions, coverages, dispositioned = run_classify(
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
                        "open_questions": [q.to_dict() for q in open_questions],
                        "coverage": [c.to_dict() for c in coverages],
                        "unrequested_changes": [d.to_dict() for d in dispositioned],
                    },
                    indent=2,
                )
            )
        else:
            print(render_classify(obligations, open_questions, coverages, dispositioned))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
