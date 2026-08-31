"""Does normalising each pair's score against its own test's distribution help?

## The hypothesis

A single global cosine cut asks a different question of every test. Each test
has its own typical similarity against the 75 defects — driven by length,
boilerplate share and vocabulary — so one constant sits at a different place in
each test's distribution. Worse, a broad end-to-end test kills defects all over
the review while scoring low against every one of them, and its kill pairs then
clamp the global lossless threshold for every other test too.

Normalising per test should remove both effects, if the effects are real.

## Prior evidence pointing the other way

**DR-259, the decision record for the obligation-linking prefilter, measured
these same corrections and found all of them degrade** — z-score against each
endpoint's profile, CSLS, and mutual rank. That is trap 6 in
`docs/experiments/obligation-dedup/README.md`, which also records why: the merge
hubs there were not geometric hubs, so raw distance worked *because* it was
uncorrelated with the failure mode.

It is measured again here rather than assumed to carry, because the question is
different. That one asked whether two obligations state the same requirement, a
semantic-equivalence judgement between two objects of the same kind. This asks
whether a test is about a defect, across two kinds of text, where the
per-test-baseline effect the hypothesis names has no analogue.

## What normalisation would cost in production

The statistics are per test over the defects of one run. In a real review the
defect set differs every run, so `mean_t` and `std_t` would be recomputed each
time from the embeddings the filter already needs — no extra call, which is why
this stays cheap. It also means **a fitted threshold does not transfer as a
constant**: the units move when the defect set moves. That is a strictly worse
position than a raw cosine cut, which at least has a fixed scale, and it has to
be weighed against whatever the normalisation buys.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import corpus as corpus_module
import score

HERE = Path(__file__).resolve().parent

#: Both the configuration the hypothesis was written against and the best one
#: measured since. Running only the first would test the claim on a model the
#: findings no longer recommend; running only the second would not answer it.
CONFIGURATIONS = [
    ("code-3 asymmetric", "voyage-code-3", "query", "voyage-code-3", "document"),
    ("code-4 both sides", "voyage-code-4", "query", "voyage-code-4", "document"),
]

TOP_K = 10


def _by_test(scores: dict) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for (_, test_id), value in scores.items():
        grouped[test_id].append(value)
    return grouped


def _by_defect(scores: dict) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for (defect_id, _), value in scores.items():
        grouped[defect_id].append(value)
    return grouped


def z_per_test(scores: dict) -> dict:
    """(s - mean_t) / std_t, over the scores of one test across all defects.

    A test whose scores have no spread contributes no information either way, so
    it maps to 0.0 — the middle of the normalised scale — rather than being
    dropped or made infinite. Excluding it would silently shrink the pair set.
    """
    grouped = _by_test(scores)
    stats = {
        test_id: (statistics.fmean(values), statistics.pstdev(values))
        for test_id, values in grouped.items()
    }
    out = {}
    for key, value in scores.items():
        mean, deviation = stats[key[1]]
        out[key] = 0.0 if deviation == 0 else (value - mean) / deviation
    return out


def rank_per_test(scores: dict) -> dict:
    """The pair's percentile rank within its own test's scores, in [0, 1]."""
    grouped = _by_test(scores)
    ordered = {test_id: sorted(values) for test_id, values in grouped.items()}
    out = {}
    for key, value in scores.items():
        values = ordered[key[1]]
        below = sum(1 for other in values if other < value)
        out[key] = below / (len(values) - 1) if len(values) > 1 else 0.5
    return out


def csls(scores: dict) -> dict:
    """s - mean of the test's top-K - mean of the defect's top-K.

    The hubness correction from the bilingual-lexicon literature: a point that
    is close to everything has its closeness discounted from both sides.
    """
    test_top = {
        test_id: statistics.fmean(sorted(values, reverse=True)[:TOP_K])
        for test_id, values in _by_test(scores).items()
    }
    defect_top = {
        defect_id: statistics.fmean(sorted(values, reverse=True)[:TOP_K])
        for defect_id, values in _by_defect(scores).items()
    }
    return {key: value - test_top[key[1]] - defect_top[key[0]] for key, value in scores.items()}


VARIANTS = {
    "raw": lambda scores: scores,
    "z per test": z_per_test,
    "rank per test": rank_per_test,
    "csls": csls,
}


def lowest_kills(corpus, scores: dict, limit: int = 6) -> list[tuple[str, str, float]]:
    """The kills that set the ceiling, lowest first — the ones a cut meets first."""
    ranked = sorted(corpus.kills, key=lambda pair: scores[pair])
    return [(pair[1], pair[0], scores[pair]) for pair in ranked[:limit]]


def defect_level(corpus, scores: dict, steps: int = 201) -> dict:
    """A different loss model: a defect is lost only when ALL its kills go.

    Separate from the headline because it means something different. Under the
    headline model one skipped kill is a loss; under this one a defect survives
    as long as any one of its killing tests is still judged. The second is
    closer to what the product cares about — a defect no test covers at all —
    but it is a weaker guarantee, and it is not what `best_lossless` reports.

    Swept in its own right rather than read off the pair-level threshold. At
    that threshold no kill is dropped at all, so no defect can have lost its
    last one, and the answer is 0 by construction — which says nothing. The
    question worth asking is how much further the cut goes before some defect
    loses every kill it had.
    """
    kills_by_defect: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for pair in corpus.kills:
        kills_by_defect[pair[0]].append(pair)

    values = sorted(scores.values())
    low, high = values[0], values[-1]
    best = {"threshold": low, "excluded_share": 0.0, "kills_lost": 0}
    for step in range(steps):
        threshold = low + (high - low) * step / (steps - 1)
        if any(
            all(scores[pair] < threshold for pair in pairs) for pairs in kills_by_defect.values()
        ):
            break
        best = {
            "threshold": threshold,
            "excluded_share": sum(1 for value in values if value < threshold) / len(values),
            "kills_lost": sum(1 for pair in corpus.kills if scores[pair] < threshold),
        }
    best["defects_with_kills"] = len(kills_by_defect)
    return best


def baseline_spread(corpus, scores: dict) -> list[tuple[str, float, float]]:
    """Per-test mean and standard deviation, so the premise can be checked."""
    grouped = _by_test(scores)
    rows = [
        (test_id, statistics.fmean(values), statistics.pstdev(values))
        for test_id, values in grouped.items()
    ]
    return sorted(rows, key=lambda row: -row[1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--findings", type=Path, default=HERE / "findings-normalized.json")
    args = parser.parse_args()

    worktree = args.worktree.resolve()
    corpus = corpus_module.load(worktree)
    _, touched = score.locality_outcomes(corpus, worktree)

    def keeps_locally(pair):
        defect = corpus.defects_by_id[pair[0]]
        if not defect.files:
            return True
        return bool(touched[pair[1]].all & defect.files)

    print(
        f"corpus: {len(corpus.defects)} defects x {len(corpus.tests)} tests "
        f"= {len(corpus.judged)} pairs, {len(corpus.kills)} kills\n"
    )

    findings: dict = {
        "run_id": corpus.run_id,
        "pairs": len(corpus.judged),
        "kills": len(corpus.kills),
        "top_k": TOP_K,
        "configurations": {},
    }

    for label, defect_model, left, code_model, right in CONFIGURATIONS:
        print(f"\n{'=' * 72}\n== {label} ==")
        raw = score.similarities(corpus, defect_model, left, code_model, right)
        block: dict = {}

        spread = baseline_spread(corpus, raw["description"])
        print("\nper-test similarity baselines, description filter (raw cosine):")
        print("  highest mean:")
        for test_id, mean, deviation in spread[:5]:
            print(f"    mean {mean:6.3f}  sd {deviation:5.3f}  {test_id}")
        print("  lowest mean:")
        for test_id, mean, deviation in spread[-5:]:
            print(f"    mean {mean:6.3f}  sd {deviation:5.3f}  {test_id}")
        means = [mean for _, mean, _ in spread]
        print(f"  spread of per-test means: {min(means):.3f} to {max(means):.3f}")
        block["baseline_spread"] = {
            "highest": [list(row) for row in spread[:5]],
            "lowest": [list(row) for row in spread[-5:]],
            "min_mean": min(means),
            "max_mean": max(means),
        }

        for variant, transform in VARIANTS.items():
            scores = {kind: transform(raw[kind]) for kind in ("description", "region")}
            entry: dict = {}
            print(f"\n-- {variant} --")
            for kind in ("description", "region"):
                curve = score.sweep(f"{kind} vs test source", corpus, scores[kind])
                top = score.best_lossless(curve)
                print(f"  {kind:<12} {top.line()}")
                entry[kind] = {
                    "best_lossless": top.as_dict(),
                    "curve": [o.as_dict() | {"lost": []} for o in curve],
                }

            union = score.best_lossless_union(
                corpus, keeps_locally, scores["description"], scores["region"]
            )
            print(f"  {union.line()}")
            entry["union"] = union.as_dict()

            print("  kills setting the ceiling (description filter), lowest first:")
            ceiling = lowest_kills(corpus, scores["description"])
            for test_id, defect_id, value in ceiling:
                print(f"    {value:8.4f}  {test_id}")
                print(f"              vs {defect_id}")
            entry["ceiling_kills"] = [
                {"test_id": t, "defect_id": d, "score": s} for t, d, s in ceiling
            ]

            weaker = defect_level(corpus, scores["description"])
            print(
                f"  weaker loss model (a defect is lost only when every one of its kills "
                f"goes): excludes {weaker['excluded_share']:.1%} while dropping "
                f"{weaker['kills_lost']} of {len(corpus.kills)} kills, "
                f"{weaker['defects_with_kills']} defects all still covered"
            )
            entry["defect_level"] = weaker

            block[variant] = entry

        findings["configurations"][label] = block

    print(f"\n{'=' * 72}\nunion, every variant, all 127 kills kept:")
    for label, block in findings["configurations"].items():
        print(f"  {label}")
        for variant in VARIANTS:
            print(f"    {variant:<16} {block[variant]['union']['excluded_share']:6.1%}")

    args.findings.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {args.findings}")


if __name__ == "__main__":
    main()
