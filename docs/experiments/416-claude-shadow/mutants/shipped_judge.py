"""Arm 1 of #416's mutant slice: the shipped judge of #379, with only the model swapped.

#379's "shipped judge (Mini, batched)" row was produced by
``docs/experiments/jev/m52/run_judge_a.py::judge_all`` (via ``score_heldout.py``),
which called ``defects/pair_mapping.py``'s own ``_batches`` and ``_ask``. That
batched judge was removed by #385, so the module as it stood then is kept here
verbatim as ``pair_mapping_fc9defc.py`` (``git show fc9defc:...``; unchanged
until #385, so it is the version #379 scored). ``judge_all`` is re-implemented
below line for line from ``run_judge_a.py``, importing that old module instead.

``--model openai/gpt-5.4-mini --mode replay`` against the default transcript
store reproduces #379's recorded calls, which proves the requests are
byte-identical to the ones #379 sent (the transcript key hashes the whole
request). ``--model anthropic/claude-sonnet-5-5`` is the new arm; it records
into its own store under ``.acceptance/cache/416-mutants/``.

Run from the repo root:
    .venv/bin/python docs/experiments/416-claude-shadow/mutants/shipped_judge.py \
        --model anthropic/claude-sonnet-5-5 --mode record --side held_out [--limit 5]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
M52 = HERE.parents[1] / "jev" / "m52"
sys.path.insert(0, str(M52))
sys.path.insert(0, str(HERE))

import pair_mapping_fc9defc as old
import prompts
from metrics import summary
from split import cases, load_split

from acceptance.config import RunConfig
from acceptance.defects.reachability import Pair
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import Mode
from acceptance.review_state import Defect, DefectType
from acceptance.usage import render, summarize

STORE = Path(".acceptance/cache/416-mutants/transcripts")


def _mutant_id(case_id: str) -> str:
    return case_id.split("/")[2]


def judge_all(usable, client) -> dict[str, bool | None]:
    """As ``run_judge_a.judge_all``: batched per BugsInPy bug, no reachability prefilter."""
    by_bug = defaultdict(list)
    for c in usable:
        by_bug[(c.project, c.bug_id)].append(c)

    def judge_bug(bug_cases):
        defects, tests, pairs, case_of = {}, {}, [], {}
        for c in bug_cases:
            mid = _mutant_id(c.case_id)
            defects.setdefault(
                mid,
                Defect(
                    id=mid,
                    obligation_id="O1",
                    type=DefectType.OTHER,
                    description=c.defect_description,
                ),
            )
            tests.setdefault(
                c.test_id,
                DiscoveredTest(
                    test_id=c.test_id, file=c.test_id.split("::")[0], source=c.test_source
                ),
            )
            pair = Pair(defects[mid], tests[c.test_id])
            pairs.append(pair)
            case_of[pair.key] = c.case_id
        out = {}
        for batch in old._batches(pairs, old.DEFAULT_PAIR_BATCH_SIZE, old.DEFAULT_TESTS_PER_BATCH):
            answered, _unusable, _ = old._ask(list(batch.items), batch, client)
            for pair in batch.items:
                cid = case_of[pair.key]
                out[cid] = answered[pair.key][0] if pair.key in answered else None
        return out

    verdicts: dict[str, bool | None] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for out in pool.map(judge_bug, by_bug.values()):
            verdicts.update(out)
    return verdicts


def usable(side: str):
    ids = set(load_split()[side])
    out = []
    for c in cases():
        if c.case_id in ids:
            try:
                prompts.mutated_hunk(c)
                out.append(c)
            except prompts.CannotBuild:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--mode", choices=["record", "replay"], default="replay")
    ap.add_argument("--side", choices=["held_out", "tuning"], default="held_out")
    ap.add_argument("--store", default=None, help="transcript root; default per model")
    ap.add_argument("--limit", type=int, default=None, help="first N bugs only (cost probe)")
    ap.add_argument("--batch", action="store_true", help="Anthropic Message Batches API")
    args = ap.parse_args()

    cs = usable(args.side)
    if args.limit:
        keep = sorted({(c.project, c.bug_id) for c in cs})[: args.limit]
        cs = [c for c in cs if (c.project, c.bug_id) in keep]
    update = {"transcript_root": Path(args.store)} if args.store else {}
    if not args.store and args.model.startswith("anthropic/"):
        update["transcript_root"] = STORE
    config = RunConfig(
        model=args.model,
        mode=Mode.RECORD if args.mode == "record" else Mode.REPLAY,
        batch=args.batch,
        **update,
    )
    client = config.build_client()
    verdicts = judge_all(cs, client)
    usage = summarize(client.observed_calls)
    print(render(usage), file=sys.stderr)

    y = [c.killed for c in cs]
    said = [verdicts.get(c.case_id) for c in cs]
    cost = usage.evidence_cost_usd
    result = {
        "model": args.model,
        "side": args.side,
        "design": "shipped judge (batched pair judge as of fc9defc)",
        "cases": len(cs),
        "killed": sum(y),
        "survived": len(y) - sum(y),
        "calls": len(client.observed_calls),
        "total_cost_usd": round(cost, 4),
        "anthropic_run_spend_usd": round(usage.anthropic_run_spend_usd, 4),
        **summary(said, y, cost_total=cost),
        "per_case": {c.case_id: v for c, v in zip(cs, said, strict=True)},
    }
    if not args.limit:
        name = f"shipped-{args.side}-{args.model.replace('/', '_')}.json"
        (HERE / name).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_case"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
