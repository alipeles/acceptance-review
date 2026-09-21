"""Replay a recorded review's pair verdicts through #348's ranked walk.

#348's first Acceptance item, as amended at its Gate 1: on a recorded corpus,
every per-criterion evidence class must be identical between the ranked walk
with an early stop and the full sweep that was actually run. A pipeline replay
cannot show this, because ranked rounds put different pairs in each request and
so produce request keys no transcript was recorded under. This replays the
ANSWERS instead: the product's own `rank_pairs` orders each defect's pairs, the
product's own `_walk_ranked` decides which to ask, and "asking" returns what the
full sweep recorded for that pair.

So everything here is product code except the judge, which is replaced by the
recording of the judge. The walk sees exactly the answers it would have been
given, provided the judge answers a pair the same way whatever else shares its
request — the premise DR-269's carry already rests on.

Run:

    .venv/bin/python docs/experiments/rank-prefilter/replay_stop_rule.py \\
        --review <review.json> --worktree <checkout of its head> [--stop 1] \\
        [--mode record]

The worktree supplies the test sources to embed; each is checked against the
digest the review recorded. Embeddings go through `ModelClient.embed`, so they
record into `.acceptance/cache/transcripts/` and replay after. `--mode record`
is needed only the first time.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

from acceptance.config import DEFAULT_EMBEDDING_MODEL, RunConfig
from acceptance.defects.pair_mapping import _STAGE, _walk_ranked
from acceptance.defects.pair_ranking import rank_pairs
from acceptance.defects.reachability import Pair
from acceptance.defects.support import derive_support
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import Mode
from acceptance.review_state import EvidenceTier, Review, UnjudgedCause


def _source(worktree: Path, test_id: str) -> str:
    """The test's own source, as `discovery._node_source` extracts it."""
    parts = test_id.split("::")
    text = (worktree / parts[0]).read_text()
    body = ast.parse(text).body
    for index, name in enumerate(parts[1:], start=1):
        node = next(
            n
            for n in body
            if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and n.name == name
        )
        if index == len(parts) - 1:
            lines = text.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
        body = node.body
    raise ValueError(test_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--stop", type=int, default=1)
    parser.add_argument("--tests-per-batch", type=int, default=4)
    parser.add_argument("--mode", default="replay", choices=["replay", "record"])
    args = parser.parse_args()

    review = Review.model_validate(json.loads(args.review.read_text()))
    defects = {d.id: d for s in review.defect_sets for d in s.defects}

    # What the full sweep put to the model: every static verdict, and every pair
    # it offered and got no answer for. Executed verdicts, prefiltered pairs and
    # #340's routed pairs never reached the judge, so they are kept as they were.
    static = {
        (v.defect_id, v.test_id): v for v in review.pair_verdicts if v.tier is EvidenceTier.STATIC
    }
    executed = [v for v in review.pair_verdicts if v.tier is not EvidenceTier.STATIC]
    unanswered = {
        (u.defect_id, u.test_id): u
        for u in review.unjudged_pairs
        if u.cause is UnjudgedCause.UNANSWERED
    }
    untouched = [u for u in review.unjudged_pairs if u.cause is not UnjudgedCause.UNANSWERED]

    digests = {v.test_id: v.test_digest for v in static.values()}
    tests: dict[str, DiscoveredTest] = {}
    for test_id in sorted({t for _, t in list(static) + list(unanswered)}):
        source = _source(args.worktree, test_id)
        if digests.get(test_id):
            assert hashlib.sha256(source.encode()).hexdigest() == digests[test_id], test_id
        tests[test_id] = DiscoveredTest(
            test_id=test_id, file=test_id.split("::")[0], reasons=[], source=source
        )
    pairs = [Pair(defects[d], tests[t]) for d, t in sorted(list(static) + list(unanswered))]

    client = RunConfig(mode=Mode(args.mode), embedding_model=DEFAULT_EMBEDDING_MODEL).build_client()
    ranks = rank_pairs(pairs, client, _STAGE)

    asked_log: list[int] = []

    def recorded(round_pairs: list[Pair]):
        asked_log.append(len(round_pairs))
        return (
            [static[p.key] for p in round_pairs if p.key in static],
            [unanswered[p.key] for p in round_pairs if p.key in unanswered],
        )

    walked, skipped = _walk_ranked(pairs, ranks, args.stop, args.tests_per_batch, recorded)

    obligations = review.obligation_map
    full = derive_support(
        obligations, review.defect_sets, executed + list(static.values()), review.unjudged_pairs
    )
    ranked = derive_support(
        obligations,
        review.defect_sets,
        executed + [v for v in walked],
        untouched + skipped,
    )

    by_id = {r.obligation_id: r for r in ranked}
    differing = [
        (r.obligation_id, r.evidence_class, by_id[r.obligation_id].evidence_class)
        for r in full
        if (r.evidence_class, r.covered, r.unknown)
        != (
            by_id[r.obligation_id].evidence_class,
            by_id[r.obligation_id].covered,
            by_id[r.obligation_id].unknown,
        )
    ]

    covered_skips = [s for s in skipped if s.cause is UnjudgedCause.DEFECT_ALREADY_COVERED]
    judged_by_defect: dict[str, int] = {}
    for p in pairs:
        judged_by_defect.setdefault(p.defect.id, 0)
    for v in walked:
        judged_by_defect[v.defect_id] += 1
    for u in skipped:
        if u.cause is UnjudgedCause.UNANSWERED:
            judged_by_defect[u.defect_id] += 1
    stopped = {s.defect_id for s in covered_skips}
    killed = {v.defect_id for v in walked if v.kills}
    per_covered = [judged_by_defect[d] for d in killed]

    print(f"review {review.reviewed_revision[:9]}, stop after {args.stop} kill(s)")
    print(
        f"  criteria: {len(full)}; evidence class, covered and unknown differ on {len(differing)}"
    )
    for row in differing:
        print(f"    {row}")
    print(
        f"  pairs the full sweep asked: {len(pairs)}; the walk asked "
        f"{len(pairs) - len(covered_skips)} ({(len(pairs) - len(covered_skips)) / len(pairs):.1%}), "
        f"skipped {len(covered_skips)}"
    )
    print(f"  rounds: {len(asked_log)}, pairs per round {asked_log}")
    print(
        f"  defects: {len(judged_by_defect)}; covered {len(killed)}, of which {len(stopped)} "
        f"stopped early; mean {sum(per_covered) / max(1, len(per_covered)):.1f} judgements "
        f"per covered defect"
    )


if __name__ == "__main__":
    main()
