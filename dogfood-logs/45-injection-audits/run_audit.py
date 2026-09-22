"""Run one defect-injection audit and write it out for judging.

Why this exists: audits v1 to v8 were produced by a harness that was never
committed, so every rate in `docs/DR-171-mutation-targeting.md` was recomputed
by hand from a Markdown file nobody could regenerate. This script is that
harness, kept beside the audits it produces.

It is NOT part of the review pipeline and nothing in `src/` imports it. It
calls the same functions `pipeline.py::_run_execution_tier` calls, in the same
order, over a FIXED defect list read from disk instead of an enumerated one —
that fixed list is what makes one audit comparable with another.

    .venv/bin/python dogfood-logs/45-injection-audits/run_audit.py \
        --repo ../45-audit-head --base 61c5a3c --head 518f876 \
        --audit v9 --out dogfood-logs/45-injection-audits/injection-audit-v9.md

`--repo` is a worktree checked out at `--head`: the code under review. This
script runs from the current checkout, so the mutation code being measured is
the one in this branch, not the one at the audited revision.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from acceptance.change.context import retrieve_context
from acceptance.change.diff import extract_change_set
from acceptance.config import RunConfig
from acceptance.evidence.discovery import discover_tests
from acceptance.llm import SERVED_FROM_PROVIDER, Mode
from acceptance.mutation.attempt import MutationAttempt
from acceptance.mutation.baseline import establish_baseline
from acceptance.mutation.descriptor import LiveDescriptorBuilder
from acceptance.mutation.region import regions_for
from acceptance.mutation.runner import run_mutations
from acceptance.mutation.settings import ExecutionSettings
from acceptance.mutation.verification import verify_attempts
from acceptance.review_state import Defect, DefectSet

#: The three criteria left out of v7 and v8 while they were under human
#: adjudication. Kept here so a fresh audit uses the same 22 as v7/v8 by
#: default and the comparison is like for like.
CONTESTED = (
    "candidate-tests-run-once-before-changes",
    "recorded-at-strongest-evidence-tier",
    "stop-review-on-failing-candidate-test",
)

#: The edit-building stage, and verification's two questions, as `llm.py` names
#: them. Used both to route stages onto their own model and to attribute spend.
EDIT_STAGE = "mutation descriptor"
VERIFY_STAGES = (
    "mutation verification: behaviour change",
    "mutation verification: defect match",
)


def load_defect_sets(path: Path, skip: tuple[str, ...]) -> list[DefectSet]:
    """The stored defect list, minus the criteria named in `skip`.

    The file is a plain list of `DefectSet` dumps — not a ledger entry — so it
    is read directly rather than through the carry path in
    `enumerate_defects(prior=...)`, whose key folds in a stage-logic version
    that has moved since the file was written.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [DefectSet.from_dict(entry) for entry in raw if entry["obligation_id"] not in skip]


def _first(defect_sets: list[DefectSet], limit: int) -> list[DefectSet]:
    """The first `limit` defects, with their sets kept intact around them.

    For a smoke run only. A truncated audit is not comparable with v7 or v8 and
    must never be labelled as one.
    """
    kept: list[DefectSet] = []
    remaining = limit
    for entry in defect_sets:
        if remaining <= 0:
            break
        take = entry.defects[:remaining]
        remaining -= len(take)
        kept.append(entry.model_copy(update={"defects": take}))
    return kept


def _diff_lines(descriptor) -> list[str]:
    """The edit as a diff block, in the shape the v6-v8 audits use."""
    if descriptor is None:
        return []
    lines = ["```diff"]
    for line in (descriptor.original or "").splitlines():
        lines.append(f"-{line}")
    for line in (descriptor.replacement or "").splitlines():
        lines.append(f"+{line}")
    lines.append("```")
    return lines


def render(
    attempts: list[MutationAttempt],
    defects: dict[str, Defect],
    *,
    audit: str,
    head: str,
    note: str,
    usable_tests: int,
) -> str:
    """The per-defect Markdown the judging pass reads.

    Deliberately the same section shape as `injection-audit-v8.md`, so a
    judging pass written against the protocol reads either without adjustment.
    Everything here comes off the attempt and its defect; nothing is recomputed.
    """
    by_outcome: dict[str, int] = defaultdict(int)
    for attempt in attempts:
        by_outcome[attempt.outcome.value] += 1

    out = [f"# Defect injection audit {audit} — #45, head {head}", ""]
    out += [note, ""]
    out += [f"{len(attempts)} defects, {usable_tests} usable candidate tests.", ""]
    for kind in sorted(by_outcome):
        out.append(f"- **{kind}:** {by_outcome[kind]}")
    out.append("")

    for attempt in attempts:
        defect = defects.get(attempt.defect_id)
        out.append(f"## `{attempt.outcome.value}` — {attempt.defect_id}")
        out.append("")
        if defect is not None:
            out.append(f"- **type:** `{defect.type}`")
            out.append(f"- **defect:** {defect.description}")
            out.append(f"- **expected:** {defect.expected_behavior}")
            out.append(f"- **defective:** {defect.defective_behavior}")
        if attempt.reason:
            out.append(f"- **reason:** {attempt.reason}")
        if attempt.candidates_asked:
            out.append(f"- **candidates asked:** {attempt.candidates_asked}")
            out.append(f"- **candidate used:** {attempt.candidate_used}")
        for index, candidate in enumerate(attempt.set_aside_candidates, start=1):
            out.append(
                f"- **candidate {index} set aside:** `{candidate.cause.value}` — {candidate.reason}"
            )
        if attempt.killing_tests:
            out.append(f"- **tests failing:** {len(attempt.killing_tests)}")
        # Verification's answer is recorded but MUST NOT steer the judge: the
        # judging pass is the ground truth the verifier is measured against, so
        # it is written to the JSON only, never to the Markdown the judge reads.
        out.append("")
        if attempt.descriptor is not None:
            where = (
                f"`{attempt.descriptor.path}` lines "
                f"{attempt.descriptor.start_line}-{attempt.descriptor.end_line}"
            )
            out.append(f"**edit** — {where}")
            out.append("")
            out += _diff_lines(attempt.descriptor)
            out.append("")
        if attempt.repair is not None:
            out.append(f"- **repair corroboration:** {attempt.repair_corroboration}")
            out.append(f"- **tests failing on the repair:** {len(attempt.repair_failing_tests)}")
            out.append("")
            out.append(
                f"**repair** — `{attempt.repair.path}` lines "
                f"{attempt.repair.start_line}-{attempt.repair.end_line}"
            )
            out.append("")
            out += _diff_lines(attempt.repair)
            out.append("")
    return "\n".join(out) + "\n"


def spend(client) -> dict:
    """What the run cost and how long it took, per stage.

    Live calls only for time — a replayed call took no provider time this run —
    but cost is reported for both, since `observed_calls` keeps what a replayed
    answer cost when it was recorded.
    """
    per_stage: dict[str, dict] = {}
    for call in client.observed_calls:
        row = per_stage.setdefault(
            call["stage"], {"calls": 0, "live": 0, "cost_usd": 0.0, "seconds": 0.0}
        )
        row["calls"] += 1
        row["cost_usd"] += float(call["usage"].get("cost_usd") or 0.0)
        # The constant, not the string "live": `llm.py` says `provider` and
        # `recording`, and comparing against a word it never emits reported a
        # live run as fully replayed — a bill of $0.00 on a run that spent.
        if call["served_from"] == SERVED_FROM_PROVIDER:
            row["live"] += 1
            row["seconds"] += float(call["seconds"] or 0.0)
    return per_stage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="worktree at the audited head")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--audit", required=True, help="the audit's name, e.g. v9")
    parser.add_argument(
        "--defects",
        type=Path,
        default=Path(__file__).parent / "injection-audit-v6.defects.json",
    )
    parser.add_argument("--skip", nargs="*", default=list(CONTESTED))
    parser.add_argument(
        "--limit",
        type=int,
        help="keep only the first N defects: a cheap live smoke run, not an audit",
    )
    parser.add_argument("--model", default="openai/gpt-5.4-mini", help="builds the edits")
    parser.add_argument(
        "--verifier-model",
        default="openai/gpt-5.4",
        help="runs verification's two questions; 'same' uses --model",
    )
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--no-verify", action="store_true")
    parser.add_argument("--mode", choices=["record", "replay"], default="replay")
    parser.add_argument("--out", type=Path, required=True, help="the audit Markdown")
    parser.add_argument("--attempts", type=Path, help="JSON dump; defaults beside --out")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve inputs and print what would be run, without a single model call",
    )
    parser.add_argument(
        "--control-only",
        action="store_true",
        help="stop after the control run: exercises the test-running half, still no model call",
    )
    args = parser.parse_args(argv)

    defect_sets = load_defect_sets(args.defects, tuple(args.skip))
    if args.limit:
        defect_sets = _first(defect_sets, args.limit)
    defects = {defect.id: defect for entry in defect_sets for defect in entry.defects}
    change_set = extract_change_set(args.repo, args.base, args.head)
    discovered = discover_tests(args.repo, change_set)
    regions_by_defect = {defect.id: regions_for(defect, change_set) for defect in defects.values()}
    editable = sum(1 for regions in regions_by_defect.values() if regions)

    print(f"criteria: {len(defect_sets)}")
    print(f"defects: {len(defects)} ({editable} with a region)")
    print(f"tests discovered: {len(discovered.tests)}")
    if args.dry_run:
        print("dry run: no control run, no model call")
        return 0

    execution = ExecutionSettings(
        verify_edits=not args.no_verify, max_candidates=args.max_candidates
    )
    stage_models = {}
    if not args.no_verify and args.verifier_model != "same":
        stage_models = {stage: args.verifier_model for stage in VERIFY_STAGES}
    config = RunConfig(
        model=args.model,
        stage_models=stage_models,
        mode=Mode.RECORD if args.mode == "record" else Mode.REPLAY,
    )
    client = config.build_client()

    started = time.monotonic()
    baseline = establish_baseline(
        [test.test_id for test in discovered.tests], args.repo, execution.sandbox
    )
    print(f"control run: {len(baseline.usable_tests)} usable, {len(baseline.set_aside)} set aside")
    for test in baseline.set_aside:
        print(f"  set aside: {test.test_id} — {test.kind.value}")
    if not baseline.usable_tests:
        print("no usable test: every edit would be paid for and thrown away", file=sys.stderr)
        return 1
    if args.control_only:
        print("control run only: no model call made")
        return 0

    sources = {}
    for regions in regions_by_defect.values():
        for region in regions:
            target = args.repo / region.path
            if region.path not in sources and target.is_file():
                sources[region.path] = target.read_text(encoding="utf-8")
    surrounding = retrieve_context(args.repo, change_set)

    builder = LiveDescriptorBuilder(client, surrounding)
    attempts = run_mutations(
        defect_sets,
        change_set,
        args.repo,
        baseline,
        builder,
        execution.sandbox,
        execution.max_edit_lines,
        max_failing_fraction=execution.max_failing_fraction,
        breadth_floor=execution.breadth_floor,
        max_candidates=execution.max_candidates,
    )
    if execution.verify_edits:
        attempts = verify_attempts(attempts, list(defects.values()), sources, client, surrounding)
    elapsed = time.monotonic() - started

    note = (
        f"Audit v6's defects for {len(defect_sets)} criteria "
        f"(left out: {', '.join(args.skip) if args.skip else 'none'}). "
        f"Edits on {args.model}, up to {args.max_candidates} candidates each; "
        f"verification {'off' if args.no_verify else 'on, ' + (args.model if args.verifier_model == 'same' else args.verifier_model)}."
    )
    args.out.write_text(
        render(
            attempts,
            defects,
            audit=args.audit,
            head=args.head,
            note=note,
            usable_tests=len(baseline.usable_tests),
        ),
        encoding="utf-8",
    )

    attempts_path = args.attempts or args.out.with_suffix(".attempts.json")
    attempts_path.write_text(
        json.dumps(
            {
                "audit": args.audit,
                "revision": args.head,
                "base": args.base,
                "descriptor_model": args.model,
                "verifier_model": None if args.no_verify else args.verifier_model,
                "max_candidates": args.max_candidates,
                "criteria": len(defect_sets),
                "usable_tests": len(baseline.usable_tests),
                "wall_clock_seconds": round(elapsed, 1),
                "spend": spend(client),
                "attempts": [attempt.to_dict() for attempt in attempts],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"wrote {args.out} and {attempts_path}")
    for stage, row in sorted(spend(client).items()):
        print(
            f"  {stage}: {row['calls']} calls ({row['live']} live), "
            f"${row['cost_usd']:.4f}, {row['seconds']:.0f}s"
        )
    print(f"wall clock: {elapsed:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
