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
#340 also scores the executed oracle: ranks of tests that actually failed under
a mutant (mutation_attempts.killing_tests), overall and for verified attempts.
"""
import ast
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/root/exp/docs/experiments/pair-prefilter")
import corpus as corpus_module
import score as score_module
import corpus316

KS = [5, 10, 20, 40, 80]


def shim_from_review(review_path, worktree):
    d = json.loads(Path(review_path).read_text())
    defects, dtype = {}, {}
    for ds in d["defect_sets"]:
        for df in ds["defects"]:
            defects[df["id"]] = SimpleNamespace(
                id=df["id"], description=df["description"],
                code_refs=tuple(df["code_refs"]))
            dtype[df["id"]] = df["type"]
    regions = {}
    for fc in d["change_set"]["files"]:
        for i, h in enumerate(fc["hunks"]):
            regions[f"{fc['path']}#{i}"] = h["content"]
    verdicts = d["pair_verdicts"]
    judged = [(v["defect_id"], v["test_id"]) for v in verdicts]
    kills = {(v["defect_id"], v["test_id"]) for v in verdicts if v["kills"]}
    root = Path(worktree)

    def src(test_id):
        path = test_id.split("::", 1)[0]
        parts = test_id.split("::")[1:]
        text = (root / path).read_text()
        tree = ast.parse(text)
        body = tree.body
        for i, name in enumerate(parts):
            found = next(n for n in body
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                         and n.name == name)
            if i == len(parts) - 1:
                lines = text.splitlines()
                return "\n".join(lines[found.lineno - 1:getattr(found, "end_lineno", found.lineno)])
            body = found.body

    test_ids = sorted({t for _, t in judged})
    tests = []
    for tid in test_ids:
        s = src(tid)
        dig = next(v["test_digest"] for v in verdicts if v["test_id"] == tid)
        assert hashlib.sha256(s.encode()).hexdigest() == dig, tid
        tests.append(SimpleNamespace(test_id=tid, source=s))
    judged_defects = {d_ for d_, _ in judged}
    return SimpleNamespace(
        tests=tuple(tests),
        defects=tuple(df for df in defects.values() if df.id in judged_defects),
        defects_by_id={k: v for k, v in defects.items() if k in judged_defects},
        regions=regions, judged=tuple(judged),
    ), kills, dtype, d


def rank_report(name, corpus, kills):
    sims = score_module.similarities(corpus, "voyage-code-4", "query", "voyage-code-4", "document")
    desc = sims["description"]
    by_defect = {}
    for d_, t_ in corpus.judged:
        by_defect.setdefault(d_, []).append(t_)
    kills_per = {d_: sum(1 for t_ in ts if (d_, t_) in kills) for d_, ts in by_defect.items()}
    hist = {}
    for n in kills_per.values():
        b = "0" if n == 0 else "1" if n == 1 else "2" if n == 2 else "3-5" if n <= 5 else "6-10" if n <= 10 else ">10"
        hist[b] = hist.get(b, 0) + 1
    first_ranks, all_kill_ranks, n_tests = [], [], []
    for d_, ts in by_defect.items():
        if kills_per[d_] == 0:
            continue
        ranked = sorted(ts, key=lambda t_: -desc[(d_, t_)])
        n_tests.append(len(ranked))
        kr = [i + 1 for i, t_ in enumerate(ranked) if (d_, t_) in kills]
        first_ranks.append(kr[0])
        all_kill_ranks.extend(kr)
    first_ranks.sort(); all_kill_ranks.sort()
    q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))]
    print(f"\n== {name}: {len(by_defect)} defects x ~{max(n_tests or [0])} tests, "
          f"{len(all_kill_ranks)} kills over {len(first_ranks)} killed defects ==")
    print(f"kills per defect: {dict(sorted(hist.items()))}")
    if not first_ranks:
        return
    print(f"first-kill rank: median {q(first_ranks,0.5)}, p75 {q(first_ranks,0.75)}, "
          f"p90 {q(first_ranks,0.9)}, max {first_ranks[-1]}")
    for k in KS:
        cov = sum(1 for r in first_ranks if r <= k) / len(first_ranks)
        rec = sum(1 for r in all_kill_ranks if r <= k) / len(all_kill_ranks)
        share = sum(min(k, n) for n in n_tests) / sum(n_tests)
        print(f"  top-{k:<3} defect-coverage {cov:6.1%}  kill-recall {rec:6.1%}  "
              f"(judging {share:.0%} of killed-defect pairs)")
    return desc, by_defect


# ---- #314 -------------------------------------------------------------------
c314 = corpus_module.load(Path("/root/head314"))
rank_report("#314 (judge kills)", c314, set(c314.kills))

# ---- #316 -------------------------------------------------------------------
c316 = corpus316.load()
rank_report("#316 (judge kills)", c316, set(c316.kills))

# ---- #340 -------------------------------------------------------------------
c340, kills340, dtype340, d340 = shim_from_review("/root/exp/review340.json", "/root/head340")
out = rank_report("#340 (judge kills)", c340, kills340)

# executed oracle on #340
desc, by_defect = out
attempts = d340.get("mutation_attempts") or []
for label, keep in [("executed kills (all killed attempts)", lambda a: a["outcome"] == "killed"),
                    ("executed kills (verified only)", lambda a: a["outcome"] == "killed" and a.get("verified"))]:
    ranks = []
    for a in attempts:
        if not keep(a):
            continue
        d_ = a["defect_id"]
        ts = by_defect.get(d_)
        if not ts:
            continue
        ranked = sorted(ts, key=lambda t_: -desc[(d_, t_)])
        pos = [i + 1 for i, t_ in enumerate(ranked) if t_ in set(a.get("killing_tests") or [])]
        if pos:
            ranks.append(min(pos))
    ranks.sort()
    if ranks:
        q = lambda xs, p: xs[min(len(xs) - 1, int(p * len(xs)))]
        print(f"\n{label}: {len(ranks)} defects; first-kill rank median {q(ranks,0.5)}, "
              f"p90 {q(ranks,0.9)}, max {ranks[-1]}")
        for k in KS:
            print(f"  top-{k:<3} defect-coverage {sum(1 for r in ranks if r <= k)/len(ranks):6.1%}")
    else:
        print(f"\n{label}: no scoreable attempts")
