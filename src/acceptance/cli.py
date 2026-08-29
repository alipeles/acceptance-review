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
import textwrap
from pathlib import Path

from acceptance.change.diff import extract_change_set, extract_working_tree_change_set
from acceptance.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LINK_DISTANCE_THRESHOLD,
    DEFAULT_MAPPING_BATCH_SIZE,
    DEFAULT_MODEL,
    DEFAULT_SEED,
    RunConfig,
)
from acceptance.coverage.classify import ImplementationCoverage, classify_coverage
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.open_questions import (
    apply_open_question_resolutions,
    resolve_open_questions,
)
from acceptance.coverage.unrequested import detect_unrequested_changes
from acceptance.llm import LLMError, Mode, ModelClient
from acceptance.pipeline import run_review
from acceptance.recommendation import lookup as lookup_recommendation
from acceptance.recommendation import render as render_recommendation
from acceptance.report import render_report
from acceptance.requirement.ledger import LedgerStore, new_run_id
from acceptance.requirement.linking import link_duplicate_obligations
from acceptance.requirement.obligations import (
    Decomposition,
    Obligation,
    build_ledger_entry,
    decompose,
)
from acceptance.requirement.task_file import parse_task_file
from acceptance.rerun import find_prior_review, task_digest
from acceptance.review_state import ChangeSet, OpenQuestion, Review
from acceptance.review_store import ReviewStore
from acceptance.supplied_ids import UnusableAnswerLog
from acceptance.usage import render as render_usage
from acceptance.usage import summarize as summarize_usage


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
    continue_from: str | None = None,
    ledger: LedgerStore | None = None,
    run_id: str | None = None,
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

    # A `check` decomposes too, so it mints a run id and records what it derived
    # on the same terms `decompose` does — otherwise the two entry points would
    # disagree about what a run is, and only one of them could be continued.
    run_id = run_id or new_run_id()
    sink: list = []

    review = run_review(
        task_text=task_text,
        change_set=change_set,
        repo=repo_path,
        client=client if client is not None else config.build_client(),
        reviewed_revision=reviewed_revision,
        declaration_text=declaration_text,
        policy=config.scope_expansion_policy,
        mapping_batch_size=config.mapping_batch_size,
        link_pair_batch_size=config.link_pair_batch_size,
        link_distance_threshold=config.link_distance_threshold,
        task_identifier=task,
        prior=prior,
        ledger_prior=ledger.read_if_present(continue_from) if ledger is not None else None,
        ledger_sink=sink,
    )
    store.write(review)
    if ledger is not None and sink:
        derived, linked = sink[0]
        ledger.write(
            build_ledger_entry(
                derived,
                run_id=run_id,
                parent_run_id=continue_from,
                task_digest=task_digest(task_text),
                linked=linked,
            )
        )
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


def run_decompose(
    task: str,
    config: RunConfig,
    continue_from: str | None = None,
    ledger: LedgerStore | None = None,
    client: ModelClient | None = None,
) -> tuple[Decomposition, UnusableAnswerLog, str]:
    """Parse a task file and decompose it into obligations + open questions.

    Uses a live model call (in RECORD mode) — the dogfooding path for M1.2/M1.3.

    Returns this run's identifier alongside the result. Every run mints one and
    records what it derived, so a later run can name it with `--continue` and keep
    the obligations of every requirement it did not change (#269). `continue_from`
    naming an unknown run is not an error: carry-forward defaults to fresh, and
    the failure mode of that default is lost work rather than imported work.
    """
    text = _read_task(task)
    parsed = parse_task_file(text)
    # Accepted rather than always built here so the caller can read back what the
    # run cost — `main` prints the per-stage footer off this client (#264).
    client = client if client is not None else config.build_client()
    store = ledger if ledger is not None else LedgerStore()
    prior = store.read_if_present(continue_from)
    run_id = new_run_id()
    # The log is created HERE and rendered below. Linking can reject a whole
    # group of obligations as self-contradictory, and that rejection is the
    # difference between "nothing looked like a duplicate" and "the answers
    # could not be reconciled, so nothing was merged" (#144). Dropping the log
    # would make a decompose silently report the former while the latter
    # happened — the exact silence this project exists to remove.
    unusable = UnusableAnswerLog()
    derived = decompose(parsed, client, unusable, prior=prior)
    # De-duplication runs here too, not only in `check` (#144). Obligation
    # determination is two stages, and `decompose` reports the OUTPUT of that
    # determination — a decompose that skipped linking would show a different
    # obligation set from the one `check` reviews, so the Gate 1 breakdown a
    # reader confirms would not be the set every later stage judges.
    linked = link_duplicate_obligations(
        derived,
        client,
        unusable,
        pair_batch_size=config.link_pair_batch_size,
        distance_threshold=config.link_distance_threshold,
        prior=prior,
    )
    # Written from the DERIVED decomposition, not the linked one. What a later
    # run carries forward is what this stage derived per requirement; linking is
    # a separate decision over that set, and laundering a post-merge obligation
    # back into the ledger would let one run's merge become the next run's
    # premise (DR-204: derivation performs no linking).
    store.write(
        build_ledger_entry(
            derived,
            run_id=run_id,
            parent_run_id=continue_from,
            task_digest=task_digest(text),
            linked=linked,
        )
    )
    return linked, unusable, run_id


def _report_usage(client: ModelClient) -> None:
    """Print what the run cost, by stage, on STDERR.

    stderr for the same reason the run id is on stderr: two runs over the same
    input must produce byte-identical STDOUT, and cost is not reproducible — a
    replayed run spends nothing where the run that recorded it spent money. The
    §16 report and the persisted review never see this (#264).
    """
    print(render_usage(summarize_usage(client.observed_calls)), file=sys.stderr)


def _report_run(run_id: str, continued_from: str | None, result: Decomposition) -> None:
    """What this run was, on stderr — its id, what it carried, what disappeared.

    The removals are the part that must not be silent. A requirement that vanished
    between two task files took its obligations with it, and a review that simply
    stops mentioning them is indistinguishable from one where they were never
    written.
    """
    carried = sum(1 for entry in result.derivations if entry.derivation.value == "carried")
    revised = sum(1 for entry in result.derivations if entry.derivation.value == "revised")
    derived = sum(1 for entry in result.derivations if entry.derivation.value == "derived")
    print(f"run {run_id}", file=sys.stderr)
    if continued_from:
        print(f"  continuing {continued_from}", file=sys.stderr)
    print(
        f"  requirements: {derived} derived, {carried} carried, {revised} revised; "
        f"{result.calls_issued} decompose call(s)",
        file=sys.stderr,
    )
    for removal in result.removed_requirements:
        print(
            f"  REMOVED {removal.requirement_id}: {removal.text.strip()} "
            f"({len(removal.obligations)} obligation(s) dropped)",
            file=sys.stderr,
        )
    print(f"  continue this run with: --continue {run_id}", file=sys.stderr)


_WIDTH = 88


def render_decomposition(result: Decomposition) -> str:
    """Render the decomposition requirement-major — as the mapping it is.

    Organised by requirement rather than by obligation because that is the
    question a reader has at Gate 1: *did my mandate survive?* An
    obligation-major list answers "what did the tool produce", which a reader can
    only turn into the first question by reconciling it against the task file by
    hand — which is exactly the manual step #202 exists to remove.

    Every requirement appears, including the ones that produced nothing.
    """
    requirement_map = result.requirement_map
    obligations = {o.id: o for o in result.obligations}
    questions = {q.id: q for q in result.open_questions}

    total = len(requirement_map.requirements)
    if not total:
        return _render_flat(result)

    lines = [_summary(requirement_map, total), ""]

    for requirement in requirement_map.requirements:
        entry = requirement_map.disposition_for(requirement.id)
        lines.extend(
            _requirement_block(requirement, entry, obligations, questions, requirement_map)
        )
        lines.append("")

    lines.extend(_orphan_obligations(result, requirement_map))
    lines.extend(_unraised_questions(result, requirement_map))
    lines.extend(_unread_source(requirement_map))
    return "\n".join(lines).rstrip() + "\n"


def _unread_source(requirement_map) -> list[str]:
    """Task-file text that became no requirement, so the model never saw it.

    Loud, because this is the one failure on this page the reader cannot fix by
    arguing with the tool: text that was never parsed produced no obligation, no
    disposition, and no question, and nothing else in the output would hint that
    it exists. It is also the reader's own fix — usually a section the format
    does not recognise.
    """
    unread = requirement_map.unread_source
    if not unread:
        return []
    lines = [
        f"!! NOT READ AS ANY REQUIREMENT: {len(unread)} block(s) of the task file",
        "   These were parsed but matched no §7.1 section, so the decomposer",
        "   never saw them. Move them under a recognised heading if they state",
        "   a requirement.",
    ]
    for span in unread:
        lines.extend(_wrap(_flatten(span.text), indent="     - ", hang="       "))
    lines.append("")
    return lines


def _summary(requirement_map, total: int) -> str:
    """The header counts, with the three ways of yielding no obligation kept
    apart.

    A single "yielding none" figure reads as a defect count, and only one of its
    three components is one. A requirement the decomposer deliberately declined
    with a reason (a bare section marker) and one it raised a question about are
    both correct outcomes; a requirement it never accounted for is the recall
    failure this whole stage exists to surface. Collapsing them would put the
    defect back behind a number that looks the same either way — a smaller
    version of the flat list's own problem.

    There is no "unaccounted for" count. It used to be printed even when zero,
    as the assurance a reader wants — but the assurance is now structural: a
    response that leaves a requirement unaccounted for does not parse, so a
    rendered map cannot contain one (M1.2.r2). A line reporting zero every time
    is noise that reads as a check being performed.
    """
    declined = questioned = 0
    for entry in requirement_map.dispositions:
        if entry.obligation_ids:
            continue
        if entry.open_question_ids:
            questioned += 1
        else:
            declined += 1

    parts = [f"Requirements: {total}", f"with obligations: {total - declined - questioned}"]
    if questioned:
        parts.append(f"raised a question: {questioned}")
    if declined:
        parts.append(f"deliberately none: {declined}")
    return "   ".join(parts)


def _requirement_block(
    requirement, entry, obligations: dict, questions: dict, requirement_map
) -> list[str]:
    """One requirement and everything it produced."""
    lines = _wrap(f"[{requirement.id}] {_flatten(requirement.text)}", indent="", hang="    ")

    if entry is None:  # defensive: the map always disposes every requirement
        lines.append("    (no disposition recorded)")
        return lines

    for obligation_id in entry.obligation_ids:
        obligation = obligations.get(obligation_id)
        if obligation is None:
            lines.append(f"    -> {obligation_id}  (obligation not found)")
            continue
        flag = "explicit" if obligation.explicit else "inferred"
        # Naming the other requirements an obligation serves is what makes the
        # relation legible as many-to-many rather than looking like the same
        # obligation duplicated under several headings (DR-202 decision 2).
        shared = [
            other
            for other in requirement_map.requirements_for_obligation(obligation_id)
            if other != requirement.id
        ]
        also = f"   (also serves {', '.join(shared)})" if shared else ""
        lines.append(f"    -> {obligation_id}  [{obligation.type.value}/{flag}]{also}")
        lines.extend(_wrap(obligation.description, indent="       ", hang="       "))

    for question_id in entry.open_question_ids:
        question = questions.get(question_id)
        text = question.question if question is not None else question_id
        lines.append(f"    ?  {question_id}")
        lines.extend(_wrap(text, indent="       ", hang="       "))

    if not entry.obligation_ids and not entry.open_question_ids:
        # A deliberate decline is a correct outcome and reads as one. The
        # failure case it used to be distinguished from no longer reaches here.
        lines.append("    -- no obligation, deliberately")
        if entry.reason:
            lines.extend(_wrap(entry.reason, indent="       ", hang="       "))

    return lines


def _orphan_obligations(result: Decomposition, requirement_map) -> list[str]:
    """Obligations no requirement claims.

    Rendered rather than dropped: an obligation traceable to no requirement is
    either an invention or a mapping failure, and both are findings. Silently
    omitting it would reintroduce, on the other axis, the exact invisibility
    this command was restructured to remove.
    """
    orphans = [
        o for o in result.obligations if not requirement_map.requirements_for_obligation(o.id)
    ]
    if not orphans:
        return []
    lines = ["Obligations mapped to no requirement:"]
    for obligation in orphans:
        lines.append(f"  ! {obligation.id}  [{obligation.type.value}]")
        lines.extend(_wrap(obligation.description, indent="     ", hang="     "))
    lines.append("")
    return lines


def _unraised_questions(result: Decomposition, requirement_map) -> list[str]:
    """Open questions no requirement's disposition accounts for."""
    claimed = {qid for entry in requirement_map.dispositions for qid in entry.open_question_ids}
    loose = [q for q in result.open_questions if q.id not in claimed]
    if not loose:
        return []
    lines = ["Open questions not tied to a requirement:"]
    for question in loose:
        lines.append(f"  ? {question.id}")
        lines.extend(_wrap(question.question, indent="     ", hang="     "))
    lines.append("")
    return lines


def _render_flat(result: Decomposition) -> str:
    """Fallback for a task file with no parseable §7.1 requirements — there is
    no mapping to show, so the obligations are all there is to say."""
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


def _flatten(text: str) -> str:
    """Collapse a requirement's own line breaks and list marker.

    `task_file.py`'s span fallback keeps a wrapped bullet verbatim, marker and
    all, because a citation's offsets must satisfy `source[start:end] ==
    span.text`. That is right for the data and wrong for a heading line, so the
    flattening happens here, at the point of display.
    """
    collapsed = " ".join(text.split())
    return collapsed.removeprefix("- ")


def _wrap(text: str, indent: str, hang: str) -> list[str]:
    wrapped = textwrap.wrap(text, width=_WIDTH, initial_indent=indent, subsequent_indent=hang)
    return wrapped or [indent + text]


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
    client = config.build_client()
    decomposition = link_duplicate_obligations(
        decompose(parsed, client),
        client,
        pair_batch_size=config.link_pair_batch_size,
        distance_threshold=config.link_distance_threshold,
    )
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
        unrequested,
        obligations,
        coverages,
        change_set,
        config.scope_expansion_policy,
        config.build_client(),
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
        lines.append(
            f"  [{cov.status.value}] {cov.obligation_id}: {descriptions.get(cov.obligation_id, '')}"
        )
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
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=(
            "Model used to embed obligations for the linking prefilter "
            f"(determinism; default: {DEFAULT_EMBEDDING_MODEL}). Changing it "
            "invalidates recorded linking transcripts, and the distance "
            "threshold is calibrated to it."
        ),
    )
    parser.add_argument(
        "--link-distance-threshold",
        type=float,
        default=DEFAULT_LINK_DISTANCE_THRESHOLD,
        help=(
            "Cosine distance above which an obligation pair is not asked "
            f"about (determinism; default: {DEFAULT_LINK_DISTANCE_THRESHOLD}). "
            "Changing it invalidates recorded linking transcripts. Use 2.0 to "
            "ask about every pair."
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
    # Distinct from `--since`, and the two answer different questions. `--since`
    # names a stored REVIEW to build judgements on, selected over git ancestry.
    # `--continue` names a decompose RUN to carry the obligation set from. A
    # review can want either, both, or neither.
    check.add_argument(
        "--continue",
        dest="continue_from",
        default=None,
        metavar="RUN_ID",
        help="Run id to continue: carry forward each requirement whose text is unchanged.",
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
    # Naming the prior run is the ONLY way to continue one. There is deliberately
    # no bare `--continue` meaning "the last run here": that is implicit lineage
    # detection, and the default has to be fresh, because the failure mode of
    # defaulting to fresh is lost work while the failure mode of guessing is a
    # decomposition silently built on another task's obligations.
    dec.add_argument(
        "--continue",
        dest="continue_from",
        default=None,
        metavar="RUN_ID",
        help="Run id to continue: carry forward each requirement whose text is unchanged.",
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
            embedding_model=args.embedding_model,
            link_distance_threshold=args.link_distance_threshold,
        )
        # Built here, not inside run_check, so the per-stage cost footer can be
        # read back off the client that issued the calls (#264).
        client = config.build_client()
        try:
            run_id = new_run_id()
            review = run_check(
                args.task,
                args.base,
                args.head,
                config,
                ReviewStore(),
                declaration=args.declaration,
                client=client,
                since=args.since,
                continue_from=args.continue_from,
                ledger=LedgerStore(),
                run_id=run_id,
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
        # stderr in both modes, for the same reason the removal notice above is:
        # the run id must not appear on stdout, where it would make two reviews
        # over the same input differ in their bytes.
        print(f"run {run_id}", file=sys.stderr)
        if args.continue_from:
            print(f"  continuing {args.continue_from}", file=sys.stderr)
        print(f"  continue this run with: --continue {run_id}", file=sys.stderr)
        _report_usage(client)
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
            embedding_model=args.embedding_model,
            link_distance_threshold=args.link_distance_threshold,
        )
        client = config.build_client()
        try:
            result, unusable, run_id = run_decompose(
                args.task, config, args.continue_from, client=client
            )
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
            for answer in unusable.answers:
                print(f"\nUnreconciled linking answers: {answer.reason}")
                print(f"  affected: {answer.returned_id}")
        # The run id and what it carried go to STDERR, never stdout. Two runs
        # over the same input must produce byte-identical output, and a run id is
        # minted randomly — putting it on stdout would break that for every
        # consumer that captures the report, which is how the dogfood logs are
        # made. stderr is where the CLI already puts everything that is about the
        # run rather than about the review.
        _report_run(run_id, args.continue_from, result)
        _report_usage(client)
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
            embedding_model=args.embedding_model,
            link_distance_threshold=args.link_distance_threshold,
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
