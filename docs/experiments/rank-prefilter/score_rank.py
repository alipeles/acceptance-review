"""Per-defect ranking of tests by description similarity: where do kills sit?

For each corpus, rank every defect's judged tests by voyage-code-4
description-to-test cosine (the pair-prefilter measurement, reused as a ranking
rather than a threshold) and report:
  - kills-per-defect distribution (the sparsity question)
  - rank of the FIRST kill per killed defect (the decision metric: one credible
    kill covers a defect, so what matters is how deep the judge must read in
    rank order before hitting one)
  - defect-coverage@k: share of killed defects with a kill in the top k
  - kill-recall@k: share of all killed pairs in the top k
  - judgements-to-stop: how many pairs a judge walking the ranking issues before
    it has seen `stop` kills for a defect (or the whole list, if it never does)
#340 also scores the executed oracle: ranks of tests that actually failed under
a mutant (mutation_attempts.killing_tests), overall and for verified attempts.

Run:

    ACCEPTANCE_HEAD314=... ACCEPTANCE_HEAD316=... ACCEPTANCE_REVIEW316=... \\
    ACCEPTANCE_HEAD340=... ACCEPTANCE_REVIEW340=... \\
    .venv/bin/python docs/experiments/rank-prefilter/score_rank.py [--symmetric]

The five inputs are two-to-three worktrees at the reviewed heads and two review
JSONs, none of which belong in the repo; `prefilter-committee/paths.py` explains
why. The #314 corpus is rebuilt from `pair-prefilter/verdicts.json.gz` and needs
only its worktree.

Vectors come from the `pair-prefilter` embedding cache under `.acceptance/`;
only uncached ones are fetched, with VOYAGE_API_KEY taken from the environment
or, failing that, from the repo's gitignored keys file.

`--symmetric` sends no `input_type` on either side, which is the only form
`llm.py::build_embedding_request` can send. The default is the asymmetric form
(description as `query`, test as `document`) the first measurement used.
"""

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(EXPERIMENTS / "pair-prefilter"))
sys.path.insert(0, str(EXPERIMENTS / "prefilter-committee"))

import corpus as corpus_module
import corpus316
import embeddings

MODEL = "voyage-code-4"
KS = [5, 10, 20, 40, 80]
STOPS = [1, 2]


def _load_voyage_key():
    """Take VOYAGE_API_KEY from the repo's gitignored keys file if it is unset.

    Only that one variable, and only when the environment lacks it. Vectors
    already in the cache never need it.
    """
    if os.environ.get("VOYAGE_API_KEY"):
        return
    keys = EXPERIMENTS.parents[1] / ".env"
    if not keys.exists():
        return
    for line in keys.read_text().splitlines():
        name, _, value = line.strip().removeprefix("export ").partition("=")
        if name.strip() == "VOYAGE_API_KEY" and value:
            os.environ["VOYAGE_API_KEY"] = value.strip().strip("'\"")
            return


def _required(name, what):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is not set; point it at {what}.")
    path = Path(value)
    if not path.exists():
        raise SystemExit(f"{name}={value} does not exist; it should be {what}.")
    return path


def shim_from_review(review_path, worktree):
    d = json.loads(Path(review_path).read_text())
    defects, dtype = {}, {}
    for ds in d["defect_sets"]:
        for df in ds["defects"]:
            defects[df["id"]] = SimpleNamespace(
                id=df["id"], description=df["description"], code_refs=tuple(df["code_refs"])
            )
            dtype[df["id"]] = df["type"]
    verdicts = d["pair_verdicts"]
    judged = [(v["defect_id"], v["test_id"]) for v in verdicts]
    kills = {(v["defect_id"], v["test_id"]) for v in verdicts if v["kills"]}
    root = Path(worktree)
    digests = {v["test_id"]: v["test_digest"] for v in verdicts}

    def src(test_id):
        path = test_id.split("::", 1)[0]
        parts = test_id.split("::")[1:]
        text = (root / path).read_text()
        tree = ast.parse(text)
        body = tree.body
        for i, name in enumerate(parts):
            found = next(
                n
                for n in body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.name == name
            )
            if i == len(parts) - 1:
                lines = text.splitlines()
                return "\n".join(
                    lines[found.lineno - 1 : getattr(found, "end_lineno", found.lineno)]
                )
            body = found.body

    tests = []
    for tid in sorted(digests):
        s = src(tid)
        assert hashlib.sha256(s.encode()).hexdigest() == digests[tid], tid
        tests.append(SimpleNamespace(test_id=tid, source=s))
    judged_defects = {d_ for d_, _ in judged}
    return (
        SimpleNamespace(
            tests=tuple(tests),
            defects=tuple(df for df in defects.values() if df.id in judged_defects),
            judged=tuple(judged),
        ),
        kills,
        dtype,
        d,
    )


def description_similarities(corpus, left_type, right_type):
    """Description-to-test cosine for every judged pair.

    The same computation as `pair-prefilter/score.py::similarities`'s
    `description` view, without the region view this experiment never reads —
    so a symmetric re-score does not pay to embed regions it would discard.
    """
    tests = list(corpus.tests)
    test_vectors = embeddings.embed([t.source for t in tests], MODEL, right_type, "test sources")
    by_test = {t.test_id: v for t, v in zip(tests, test_vectors, strict=True)}
    defects = list(corpus.defects)
    desc_vectors = embeddings.embed(
        [d.description for d in defects], MODEL, left_type, "defect descriptions"
    )
    by_desc = {d.id: v for d, v in zip(defects, desc_vectors, strict=True)}
    return {(d_, t_): embeddings.cosine(by_desc[d_], by_test[t_]) for d_, t_ in corpus.judged}


def q(xs, p):
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def rank_report(name, corpus, kills, types):
    desc = description_similarities(corpus, *types)
    by_defect = {}
    for d_, t_ in corpus.judged:
        by_defect.setdefault(d_, []).append(t_)
    kills_per = {d_: sum(1 for t_ in ts if (d_, t_) in kills) for d_, ts in by_defect.items()}
    hist = {}
    for n in kills_per.values():
        b = (
            "0"
            if n == 0
            else "1"
            if n == 1
            else "2"
            if n == 2
            else "3-5"
            if n <= 5
            else "6-10"
            if n <= 10
            else ">10"
        )
        hist[b] = hist.get(b, 0) + 1
    first_ranks, all_kill_ranks, n_tests = [], [], []
    to_stop = {s: [] for s in STOPS}
    for d_, ts in by_defect.items():
        # Ties broken by test id so the ranking, and every figure below, is
        # deterministic rather than dependent on verdict order.
        ranked = sorted(ts, key=lambda t_: (-desc[(d_, t_)], t_))
        kr = [i + 1 for i, t_ in enumerate(ranked) if (d_, t_) in kills]
        for s in STOPS:
            to_stop[s].append(kr[s - 1] if len(kr) >= s else len(ranked))
        if not kr:
            continue
        n_tests.append(len(ranked))
        first_ranks.append(kr[0])
        all_kill_ranks.extend(kr)
    first_ranks.sort()
    all_kill_ranks.sort()
    print(
        f"\n== {name}: {len(by_defect)} defects x ~{max(n_tests or [0])} tests, "
        f"{len(all_kill_ranks)} kills over {len(first_ranks)} killed defects =="
    )
    print(f"kills per defect: {dict(sorted(hist.items()))}")
    if not first_ranks:
        return desc, by_defect
    print(
        f"first-kill rank: median {q(first_ranks, 0.5)}, p75 {q(first_ranks, 0.75)}, "
        f"p90 {q(first_ranks, 0.9)}, max {first_ranks[-1]}"
    )
    for k in KS:
        cov = sum(1 for r in first_ranks if r <= k) / len(first_ranks)
        rec = sum(1 for r in all_kill_ranks if r <= k) / len(all_kill_ranks)
        share = sum(min(k, n) for n in n_tests) / sum(n_tests)
        print(
            f"  top-{k:<3} defect-coverage {cov:6.1%}  kill-recall {rec:6.1%}  "
            f"(judging {share:.0%} of killed-defect pairs)"
        )
    total = len(corpus.judged)
    for s in STOPS:
        issued = sum(to_stop[s])
        covered = [n for (d_, n) in zip(by_defect, to_stop[s]) if kills_per[d_] >= s]
        print(
            f"  stop after {s} kill(s): {issued} of {total} judgements ({issued / total:.1%}); "
            f"{len(covered)} defects stop early, mean {sum(covered) / max(1, len(covered)):.1f} "
            f"/ median {q(sorted(covered), 0.5) if covered else '-'} judgements each"
        )
    return desc, by_defect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symmetric",
        action="store_true",
        help="send no input_type on either side, as build_embedding_request does",
    )
    args = parser.parse_args()
    _load_voyage_key()
    types = (None, None) if args.symmetric else ("query", "document")
    print(f"input_type: description={types[0]}, test={types[1]}")

    # ---- #314 ---------------------------------------------------------------
    c314 = corpus_module.load(_required("ACCEPTANCE_HEAD314", "a worktree at 2945551").resolve())
    rank_report("#314 (judge kills)", c314, set(c314.kills), types)

    # ---- #316 ---------------------------------------------------------------
    c316 = corpus316.load()
    rank_report("#316 (judge kills)", c316, set(c316.kills), types)

    # ---- #340 ---------------------------------------------------------------
    c340, kills340, _dtype340, d340 = shim_from_review(
        _required("ACCEPTANCE_REVIEW340", "the #340 Gate 2 review JSON (head 07d61a8)"),
        _required("ACCEPTANCE_HEAD340", "a worktree at 07d61a8"),
    )
    desc, by_defect = rank_report("#340 (judge kills)", c340, kills340, types)

    # executed oracle on #340
    attempts = d340.get("mutation_attempts") or []
    for label, keep in [
        ("executed kills (all killed attempts)", lambda a: a["outcome"] == "killed"),
        (
            "executed kills (verified only)",
            lambda a: a["outcome"] == "killed" and a.get("verified"),
        ),
    ]:
        ranks = []
        for a in attempts:
            if not keep(a):
                continue
            d_ = a["defect_id"]
            ts = by_defect.get(d_)
            if not ts:
                continue
            ranked = sorted(ts, key=lambda t_: (-desc[(d_, t_)], t_))
            killing = set(a.get("killing_tests") or [])
            pos = [i + 1 for i, t_ in enumerate(ranked) if t_ in killing]
            if pos:
                ranks.append(min(pos))
        ranks.sort()
        if ranks:
            print(
                f"\n{label}: {len(ranks)} defects; first-kill rank median {q(ranks, 0.5)}, "
                f"p90 {q(ranks, 0.9)}, max {ranks[-1]}"
            )
            for k in KS:
                print(
                    f"  top-{k:<3} defect-coverage "
                    f"{sum(1 for r in ranks if r <= k) / len(ranks):6.1%}"
                )
        else:
            print(f"\n{label}: no scoreable attempts")


if __name__ == "__main__":
    main()
