"""Score prefilter candidates against #314's 12,450 recorded pair verdicts.

The question for every candidate is the same one: **at a threshold that excludes
X% of pairs, how many of the 127 recorded kills does it exclude?** A filter that
loses a kill at any useful threshold is rejected. A wrong exclusion silently
un-covers a defect and re-creates the failure #312 exists to remove — a
recommendation prescribing a test that already exists (#250, #287) — while a
filter that excludes too little only costs money.

**The 127 kills are the judge's own answers, not ground truth.** This measures
agreement with ourselves. For a prefilter that is the right target: its only job
is to avoid skipping a pair the judge would have called a kill. It is still not
a measure of whether the judge is right.

Run:

    set -a; . ./.env; set +a          # only the embedding filters need a key
    .venv/bin/python docs/experiments/pair-prefilter/score.py \\
        --worktree /path/to/checkout-of-head

`--no-embeddings` runs the free baseline alone and makes no network call.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import corpus as corpus_module
import embeddings
import locality

HERE = Path(__file__).resolve().parent

#: What gets embedded, pinned here because changing it moves every distance and
#: invalidates any threshold read off this run — DR-259's trap 7, which cost
#: that analysis real time.
#:
#: Both sides are what the *judge* was shown: the defect's description as the
#: pair question states it, and the test function's source as `DiscoveredTest`
#: carries it. Embedding something the judge never saw would measure a filter
#: for a question nobody asked.
DEFECT_TEXT = "the defect's `description`, alone"
TEST_TEXT = "the test function's source, alone"
REGION_TEXT = (
    "each implicated `path#hunk` region's diff content, embedded once and scored by best match"
)


@dataclass
class Outcome:
    """What one filter, at one threshold, did to the whole pair set."""

    name: str
    kept: int
    total: int
    kills_kept: int
    kills_total: int
    threshold: float | None = None
    lost: list[tuple[str, str]] = field(default_factory=list)

    @property
    def excluded_share(self) -> float:
        return 1 - self.kept / self.total

    @property
    def kill_recall(self) -> float:
        return self.kills_kept / self.kills_total

    def line(self) -> str:
        at = "" if self.threshold is None else f" @ {self.threshold:.3f}"
        return (
            f"{self.name + at:<34} excludes {self.excluded_share:6.1%} "
            f"({self.total - self.kept:>5} of {self.total}), "
            f"keeps {self.kills_kept:>3}/{self.kills_total} kills "
            f"({self.kill_recall:6.1%})"
        )

    def as_dict(self) -> dict:
        return {
            "name": self.name.strip(),
            "threshold": self.threshold,
            "kept": self.kept,
            "excluded_share": self.excluded_share,
            "kills_kept": self.kills_kept,
            "kill_recall": self.kill_recall,
            "lost": [list(pair) for pair in self.lost],
        }


def apply(name: str, corpus, keeps, threshold: float | None = None) -> Outcome:
    """Run a keep-predicate over every judged pair and count what it cost."""
    defects = corpus.defects_by_id
    kept = 0
    kills_kept = 0
    lost: list[tuple[str, str]] = []
    for pair in corpus.judged:
        defect_id, test_id = pair
        survives = keeps(defects[defect_id], test_id)
        kept += survives
        if pair in corpus.kills:
            if survives:
                kills_kept += 1
            else:
                lost.append(pair)
    return Outcome(name, kept, len(corpus.judged), kills_kept, len(corpus.kills), threshold, lost)


# --------------------------------------------------------------------------
# The free baseline


def locality_outcomes(corpus, worktree: Path) -> tuple[list[Outcome], dict]:
    """The free baseline whole, then one signal at a time.

    The parts are measured because the whole is a union: if it excludes too
    little the answer is which signal admits everything, and if it loses kills
    the answer is which signal failed to fire. Neither is visible from the
    union's own number.
    """
    touched = locality.touched_files(corpus, worktree)
    parts = {
        "locality (all signals)": lambda t: t.all,
        "  own file": lambda t: t.own_file,
        "  called names": lambda t: t.called,
        "  referenced names": lambda t: t.referenced,
        "  imported modules": lambda t: t.imported,
        "  name match": lambda t: t.name_match,
    }
    outcomes = [
        apply(
            name,
            corpus,
            lambda defect, test_id, select=select: (
                True if not defect.files else bool(select(touched[test_id]) & defect.files)
            ),
        )
        for name, select in parts.items()
    ]
    return outcomes, touched


# --------------------------------------------------------------------------
# The embedding filters


def similarities(
    corpus,
    defect_model: str,
    left_type: str | None,
    code_model: str,
    right_type: str | None,
) -> dict:
    """Cosine similarity for every pair, under two embedding views of a defect.

    `left_type` and `right_type` are Voyage's `input_type`. The asymmetric form
    — description as `query`, code as `document` — is the shape a code-retrieval
    model is trained for; passing `None` for both is the symmetric fallback that
    works on any provider.

    **`defect_model` and `code_model` may differ**, which is what makes a mixed
    configuration measurable — a general model on the prose side and a code
    model on the code side. Voyage states that 4-series embeddings are
    compatible with one another. `probe`-style checks in this experiment's
    findings show identical text landing at cosine 0.53–0.80 across two 4-series
    models rather than the ~0.99 a shared space implies, so **a mixed
    configuration is measured, never assumed**. Comparing across two models from
    different series is meaningless: `voyage-4-large` against `voyage-code-3` on
    identical text scores about 0.00.

    **Each implicated region is embedded once and a defect scores as the best of
    its own regions**, rather than as one concatenation of them. Two reasons,
    and the first is the one that matters: a defect implicating eleven hunks —
    which one here does — would have its signal averaged away by concatenation,
    while the question being asked is whether the test relates to *any* region
    the defect touches. The second is cost: 75 defects name only 23 distinct
    regions between them, so embedding regions rather than defects is 18,000
    tokens instead of 291,000.
    """
    tests = list(corpus.tests)
    test_vectors = embeddings.embed(
        [test.source for test in tests], code_model, right_type, "test sources"
    )
    by_test = {test.test_id: vector for test, vector in zip(tests, test_vectors, strict=True)}

    defects = list(corpus.defects)
    description_vectors = embeddings.embed(
        [defect.description for defect in defects], defect_model, left_type, "defect descriptions"
    )
    by_description = {d.id: v for d, v in zip(defects, description_vectors, strict=True)}

    refs = sorted({ref for defect in defects for ref in defect.code_refs if ref in corpus.regions})
    ref_vectors = embeddings.embed(
        [corpus.regions[ref] for ref in refs], code_model, right_type, "code regions"
    )
    by_ref = dict(zip(refs, ref_vectors, strict=True))

    widths = {len(description_vectors[0]), len(test_vectors[0]), len(ref_vectors[0])}
    if len(widths) > 1:
        raise SystemExit(
            f"{defect_model} and {code_model} return different vector widths {sorted(widths)}; "
            "their cosines would be undefined, not merely unreliable."
        )

    description_sim: dict[tuple[str, str], float] = {}
    region_sim: dict[tuple[str, str], float] = {}
    for defect_id, test_id in corpus.judged:
        defect = corpus.defects_by_id[defect_id]
        test_vector = by_test[test_id]
        description_sim[(defect_id, test_id)] = embeddings.cosine(
            by_description[defect_id], test_vector
        )
        # A defect whose refs all fell out of the change set scores 1.0: nothing
        # is known about where it lives, so no threshold may exclude it. That is
        # the same branch `reachability.py` takes on an empty file set.
        scores = [
            embeddings.cosine(by_ref[ref], test_vector) for ref in defect.code_refs if ref in by_ref
        ]
        region_sim[(defect_id, test_id)] = max(scores) if scores else 1.0
    return {"description": description_sim, "region": region_sim}


def sweep(name: str, corpus, scores: dict, steps: int = 41) -> list[Outcome]:
    """The whole trade-off curve, not one chosen point.

    A single threshold hides the shape, and the shape is the finding: DR-259's
    calibration looked like a clean separator until a held-out case landed on
    the wrong side of it.
    """
    values = sorted(scores.values())
    low, high = values[0], values[-1]
    outcomes = []
    for step in range(steps):
        threshold = low + (high - low) * step / (steps - 1)
        outcomes.append(
            apply(
                name,
                corpus,
                lambda defect, test_id, t=threshold: scores[(defect.id, test_id)] >= t,
                threshold,
            )
        )
    return outcomes


def best_lossless(outcomes: list[Outcome]) -> Outcome:
    """The most a filter can exclude while losing no recorded kill.

    This is the number the decision turns on. A filter whose best lossless
    exclusion is near zero has nothing to offer, however good its curve looks
    once it is allowed to drop a kill.
    """
    lossless = [o for o in outcomes if o.kills_kept == o.kills_total]
    return max(lossless, key=lambda o: o.excluded_share)


def best_lossless_union(corpus, keeps_locally, description: dict, region: dict) -> Outcome:
    """The best the three filters do together, under the union rule.

    The standing instruction of 2026-08-30: **reject a pair only when every
    filter rejects it.** That is not the same as running each filter at its own
    best lossless threshold and intersecting the results, and it is strictly
    better: a kill only needs *one* filter to save it, so each threshold can be
    pushed past the point where it would be lossless alone.

    Solved rather than grid-searched. Only pairs the locality baseline rejects
    can be excluded at all, so the kills at risk are exactly the ones it loses.
    Sweeping the description threshold over those kills' own scores fixes, for
    each, the highest region threshold that still saves every kill the
    description threshold has given up on — one pass per candidate instead of a
    two-dimensional grid.
    """
    at_risk = [pair for pair in corpus.kills if not keeps_locally(pair)]
    excludable = [pair for pair in corpus.judged if not keeps_locally(pair)]

    best: Outcome | None = None
    # A description threshold at or below every at-risk kill's own score saves
    # them all on its own, so it is always feasible and anchors the sweep.
    candidates = sorted({description[pair] for pair in at_risk} | {min(description.values())})
    for t_description in candidates:
        given_up = [pair for pair in at_risk if description[pair] < t_description]
        # Every kill the description threshold no longer saves must be saved by
        # the region threshold, so it can rise no higher than the weakest of them.
        # With nothing given up, the description threshold saves every at-risk
        # kill by itself and the region threshold is unconstrained — so it goes
        # just above the highest score, where it excludes on its own account
        # rather than stopping one pair short at the maximum.
        t_region = min((region[pair] for pair in given_up), default=max(region.values()) + 1e-9)
        excluded = sum(
            1
            for pair in excludable
            if description[pair] < t_description and region[pair] < t_region
        )
        kept = len(corpus.judged) - excluded
        outcome = Outcome(
            "union (locality + both)",
            kept,
            len(corpus.judged),
            len(corpus.kills),
            len(corpus.kills),
            t_description,
        )
        if best is None or outcome.excluded_share > best.excluded_share:
            best = outcome
            best.name = f"union @ description {t_description:.3f}, region {t_region:.3f}"
            best.threshold = None
    assert best is not None
    return best


# --------------------------------------------------------------------------


def report_losses(corpus, outcome: Outcome, limit: int = 8) -> None:
    """Every kill a filter would have skipped, named.

    Printed rather than counted because the count alone cannot be acted on: a
    filter losing three kills that all belong to one defect is a different
    problem from one losing three spread across the review.
    """
    if not outcome.lost:
        print(f"  loses no kill — {outcome.kills_total}/{outcome.kills_total} kept")
        return
    by_defect = Counter(defect_id for defect_id, _ in outcome.lost)
    print(f"  loses {len(outcome.lost)} kills across {len(by_defect)} defects:")
    for defect_id, test_id in outcome.lost[:limit]:
        print(f"    {test_id}")
        print(f"      vs {defect_id}")
        print(f"      defect files: {sorted(corpus.defects_by_id[defect_id].files)}")
    if len(outcome.lost) > limit:
        print(f"    ... and {len(outcome.lost) - limit} more")


#: Each configuration is (label, defect model, defect input_type, code model,
#: code input_type). The single-model rows are the controls that make the mixed
#: row interpretable — without them a poor mixed score cannot be told apart from
#: a poor model.
#:
#: **On mixing two models.** Voyage's 4-series announcement says "All four
#: models produce compatible embeddings, meaning embeddings generated from
#: different models can be used interchangeably", and names `voyage-4-large`,
#: `voyage-4`, `voyage-4-lite` and `voyage-4-nano`. It does not name
#: `voyage-code-4`. Measured on identical text: the two named models sit at
#: cosine 0.89–0.93 of each other, while `voyage-code-4` against
#: `voyage-4-large` sits at 0.72 on prose and 0.56 on code. So the mixed row is
#: outside the band Voyage's own claim covers, and is measured on that basis
#: rather than dropped — ordering, not absolute agreement, is what a filter
#: needs.
CONFIGURATIONS = [
    ("code-3 asymmetric", "voyage-code-3", "query", "voyage-code-3", "document"),
    ("code-3 symmetric", "voyage-code-3", None, "voyage-code-3", None),
    ("4-large both sides", "voyage-4-large", "query", "voyage-4-large", "document"),
    ("code-4 both sides", "voyage-code-4", "query", "voyage-code-4", "document"),
    ("4-large defects, code-4 code", "voyage-4-large", "query", "voyage-code-4", "document"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--findings", type=Path, default=HERE / "findings.json")
    parser.add_argument(
        "--only",
        action="append",
        help="run just these configuration labels (repeatable); default runs all",
    )
    parser.add_argument("--no-embeddings", action="store_true")
    args = parser.parse_args()

    worktree = args.worktree.resolve()
    corpus = corpus_module.load(worktree)
    print(
        f"corpus: {len(corpus.defects)} defects x {len(corpus.tests)} tests "
        f"= {len(corpus.judged)} pairs, {len(corpus.kills)} kills "
        f"({len(corpus.kills) / len(corpus.judged):.2%})\n"
    )

    findings: dict = {
        "run_id": corpus.run_id,
        "base_revision": corpus.base_revision,
        "head_revision": corpus.head_revision,
        "pairs": len(corpus.judged),
        "kills": len(corpus.kills),
        "embedded": {"defect": DEFECT_TEXT, "test": TEST_TEXT, "region": REGION_TEXT},
    }

    print("== the free baseline ==")
    local, touched = locality_outcomes(corpus, worktree)
    for outcome in local:
        print(outcome.line())
    print("\nkills the full locality baseline would skip:")
    report_losses(corpus, local[0])
    findings["locality"] = [outcome.as_dict() for outcome in local]

    if args.no_embeddings:
        _write(args.findings, findings)
        return

    # The standing instruction of 2026-08-30: reject a pair only when every
    # filter rejects it. Solved jointly rather than by running each filter at
    # its own best lossless threshold — see `best_lossless_union`.
    def keeps_locally(pair):
        defect = corpus.defects_by_id[pair[0]]
        if not defect.files:
            return True
        return bool(touched[pair[1]].all & defect.files)

    summary: list[tuple[str, float]] = []
    for label, defect_model, left, code_model, right in CONFIGURATIONS:
        if args.only and label not in args.only:
            continue
        print(f"\n== {label}: {defect_model}/{left or 'none'} -> {code_model}/{right or 'none'} ==")
        scores = similarities(corpus, defect_model, left, code_model, right)
        block: dict = {
            "defect_model": defect_model,
            "defect_input_type": left,
            "code_model": code_model,
            "code_input_type": right,
        }
        curves = {}
        for kind in ("description", "region"):
            name = f"{kind} vs test source"
            curve = sweep(name, corpus, scores[kind])
            curves[kind] = scores[kind]
            top = best_lossless(curve)
            print(f"{name:<26} best lossless: {top.line()}")
            block[kind] = {
                "best_lossless": top.as_dict(),
                "curve": [o.as_dict() | {"lost": []} for o in curve],
            }

        union = best_lossless_union(corpus, keeps_locally, curves["description"], curves["region"])
        print(union.line())
        block["union"] = union.as_dict()
        findings[label] = block
        summary.append((label, union.excluded_share))

    print("\n== union, every configuration, all 127 kills kept ==")
    for label, share in sorted(summary, key=lambda row: -row[1]):
        print(f"  {label:<32} excludes {share:6.1%}")

    _write(args.findings, findings)


def _write(path: Path, findings: dict) -> None:
    path.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
