"""Re-run only the edit verifier over a finished audit's stored edits.

Why this exists: measuring the verifier does not need new edits. An audit's
attempts JSON already holds every edit and what the tests did under it, and its
label file already holds the judged ground truth. So a verifier experiment is
just `verify_attempts` again over those stored edits, with one control changed.

What that buys: no control run, no test runs, and no edit-building call. The
edits are held FIXED, so the only thing that moves between the source audit and
this one is what you change here — which is the attribution the audits v9 and
v10 comparison could not give.

    .venv/bin/python dogfood-logs/45-injection-audits/reverify.py \
        --repo ../45-audit-head --base 61c5a3c --head 518f876 \
        --attempts dogfood-logs/45-injection-audits/injection-audit-v10.attempts.json \
        --reasoning "mutation verification: defect match=high" \
        --mode record --out /tmp/v10-reasoning.attempts.json

Score the result against the SOURCE audit's labels, which still apply because
the edits did not change:

    .venv/bin/python dogfood-logs/45-injection-audits/score_audit.py \
        --labels dogfood-logs/45-injection-audits/labels/v10.json \
        --attempts /tmp/v10-reasoning.attempts.json

With no `--reasoning`, every call replays from the source audit's transcripts and
the output must reproduce it exactly. That is the control, it is free, and it is
worth running first.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from acceptance.change.context import retrieve_context
from acceptance.change.diff import extract_change_set
from acceptance.config import RunConfig
from acceptance.llm import Mode
from acceptance.mutation.attempt import MutationAttempt
from acceptance.mutation.region import regions_for
from acceptance.mutation.verification import verify_attempts

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_audit import CONTESTED, VERIFY_STAGES, load_defect_sets, parse_reasoning, spend


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="worktree at the audited head")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--attempts", required=True, type=Path, help="the source audit's JSON")
    parser.add_argument("--out", required=True, type=Path, help="where to write the new JSON")
    parser.add_argument(
        "--defects",
        type=Path,
        default=Path(__file__).parent / "injection-audit-v6.defects.json",
    )
    parser.add_argument("--skip", nargs="*", default=list(CONTESTED))
    parser.add_argument(
        "--reasoning",
        action="append",
        default=[],
        metavar="STAGE=EFFORT",
        help="e.g. 'mutation verification: defect match=high'; omit for the free control",
    )
    parser.add_argument("--mode", choices=["record", "replay"], default="replay")
    args = parser.parse_args(argv)

    source = json.loads(args.attempts.read_text(encoding="utf-8"))
    attempts = [MutationAttempt.from_dict(entry) for entry in source["attempts"]]
    defect_sets = load_defect_sets(args.defects, tuple(args.skip))
    defects = [defect for entry in defect_sets for defect in entry.defects]

    # Rebuilt rather than stored: `verify_attempts` needs the file text at head
    # and M2.2's surrounding code, both of which are static reads of the audited
    # worktree and cost nothing.
    change_set = extract_change_set(args.repo, args.base, args.head)
    sources: dict[str, str] = {}
    for defect in defects:
        for region in regions_for(defect, change_set):
            target = args.repo / region.path
            if region.path not in sources and target.is_file():
                sources[region.path] = target.read_text(encoding="utf-8")
    surrounding = retrieve_context(args.repo, change_set)

    # Built exactly as the source audit built it, so that with no reasoning every
    # request key matches and every call replays. The model matters to the hash;
    # the stage override is how the source audit put verification on its own
    # model, and dropping it here would move the key for the wrong reason.
    stage_models = {
        stage: source["verifier_model"] for stage in VERIFY_STAGES if source.get("verifier_model")
    }
    config = RunConfig(
        model=source["descriptor_model"],
        stage_models=stage_models,
        stage_reasoning=parse_reasoning(args.reasoning),
        mode=Mode.RECORD if args.mode == "record" else Mode.REPLAY,
    )
    client = config.build_client()

    observed = [attempt for attempt in attempts if attempt.observed]
    print(f"source audit {source['audit']}: {len(attempts)} attempts, {len(observed)} observed")
    print(f"verifier model: {source.get('verifier_model')}")
    print(f"reasoning: {parse_reasoning(args.reasoning) or 'none (control)'}")

    started = time.monotonic()
    verified = verify_attempts(attempts, defects, sources, client, surrounding)
    elapsed = time.monotonic() - started

    was = sum(1 for attempt in attempts if attempt.verified)
    now = sum(1 for attempt in verified if attempt.verified)
    moved = [
        attempt.defect_id
        for attempt, after in zip(attempts, verified, strict=True)
        if attempt.verified != after.verified
    ]
    print(f"verified: {was} before, {now} after; {len(moved)} attempts changed verdict")
    for defect_id in moved:
        print(f"  moved: {defect_id}")

    out = dict(source)
    out["audit"] = f"{source['audit']}-reverified"
    out["reverified_from"] = source["audit"]
    # The key `score_audit.py` reads. Writing it under any other name makes a
    # reasoning run report "reasoning effort: none" beside its own reasoning
    # tokens — a false record of the control that produced the numbers.
    out["stage_reasoning"] = parse_reasoning(args.reasoning)
    out["stage_controls"] = client.stage_controls_in_force
    out["spend"] = spend(client)
    out["wall_clock_seconds"] = round(elapsed, 1)
    out["attempts"] = [attempt.to_dict() for attempt in verified]
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {args.out}")
    for stage, row in sorted(spend(client).items()):
        print(
            f"  {stage}: {row['calls']} calls ({row['live']} live), "
            f"${row['cost_usd']:.4f}, {row['seconds']:.0f}s"
        )
    print(f"wall clock: {elapsed:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
