"""Score a coverage-context reachability prefilter against recorded pair verdicts.

Usage:
    python score.py <review.json> [--coverage-file .coverage] [--repo-root .]

Inputs: a stored review holding defect sets (code_refs as `path#hunk`), the
change set (hunks with `new_start`/`new_lines`), and pair verdicts; plus a
coverage.py data file recorded at the SAME revision with per-test dynamic
contexts (`pytest --cov=acceptance --cov-context=test`).

Scores three rules and writes findings.json beside this script:

  conservative     a defect region containing any line that executes only at
                   import time keeps every test (a `def` line executes at
                   import, so this fires on almost every hunk)
  default          candidates come from lines with test contexts only; a defect
                   with no such line anywhere falls back to every test
  function-expanded  default, with each hunk range widened to the enclosing
                   function bodies before intersecting with coverage

The baseline labels are the review's own pair verdicts. They are model
predictions, not ground truth, so every figure here is agreement with a noisy
oracle: a "lost kill" is a disagreement to adjudicate (M8.4 injection is the
adjudicator), not a proven filter error.
"""
from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path

import coverage


def load(review_path: Path, repo_root: Path):
    d = json.loads(review_path.read_text())
    hunks = {}
    for fc in d["change_set"]["files"]:
        for i, h in enumerate(fc["hunks"]):
            lo, n = h["new_start"], max(h["new_lines"], 0)
            hunks[f"{fc['path']}#{i}"] = (fc["path"], lo, lo + n)
    defects = {}
    for ds in d["defect_sets"]:
        for df in ds["defects"]:
            defects[df["id"]] = df
    return d, hunks, defects


def per_test_lines(cov_file: Path, repo_root: Path):
    cov = coverage.CoverageData(basename=str(cov_file))
    cov.read()
    root = str(repo_root.resolve()) + "/"
    out = {}
    for f in cov.measured_files():
        rel = f[len(root):] if f.startswith(root) else f
        out[rel] = {
            ln: {c.split("|", 1)[0] for c in ctxs if c}
            for ln, ctxs in cov.contexts_by_lineno(f).items()
        }
    return out


def function_spans(repo_root: Path, path: str, cache: dict):
    if path not in cache:
        spans = []
        try:
            tree = ast.parse((repo_root / path).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    spans.append((node.lineno, node.end_lineno + 1))
        except Exception:
            pass
        cache[path] = spans
    return cache[path]


def candidates_for(defect, hunks, lines_by_file, mode, repo_root, ast_cache, judged_tests):
    cand, import_only, saw_line, touches_py = set(), False, False, False
    for ref in defect["code_refs"]:
        if ref not in hunks:
            continue
        path, lo, hi = hunks[ref]
        touches_py |= path.endswith(".py")
        spans = [(lo, hi)]
        if mode == "function-expanded":
            for blo, bhi in function_spans(repo_root, path, ast_cache):
                if blo < hi and bhi > lo:
                    spans.append((blo, bhi))
        lines = lines_by_file.get(path, {})
        for slo, shi in spans:
            for ln in range(slo, shi):
                if ln in lines:
                    saw_line = True
                    if lines[ln]:
                        cand |= lines[ln]
                    else:
                        import_only = True
    fallback = None
    if mode == "conservative" and import_only:
        fallback = "import_time_line_in_region"
    elif not cand:
        fallback = (
            "no_python_ref" if not touches_py
            else "import_time_lines_only" if saw_line and import_only
            else "implicated_lines_never_executed"
        )
    if fallback:
        cand = set(judged_tests)
    return cand, fallback


def score(mode, d, hunks, defects, lines_by_file, repo_root):
    verdicts = d["pair_verdicts"]
    judged_tests = {v["test_id"] for v in verdicts}
    judged_defects = {v["defect_id"] for v in verdicts}
    ast_cache: dict = {}
    cands, fallbacks = {}, {}
    for did in judged_defects:
        cands[did], fb = candidates_for(
            defects[did], hunks, lines_by_file, mode, repo_root, ast_cache, judged_tests
        )
        if fb:
            fallbacks[did] = fb
    kills = [v for v in verdicts if v["kills"]]
    surviving = sum(1 for v in verdicts if v["test_id"] in cands[v["defect_id"]])
    lost = [v for v in kills if v["test_id"] not in cands[v["defect_id"]]]
    sizes = sorted(
        len(cands[d_] & judged_tests) for d_ in cands if d_ not in fallbacks
    )
    return {
        "mode": mode,
        "pairs": len(verdicts),
        "pairs_surviving": surviving,
        "surviving_share": round(surviving / len(verdicts), 4),
        "kills": len(kills),
        "kills_retained": len(kills) - len(lost),
        "kill_recall": round((len(kills) - len(lost)) / len(kills), 4),
        "defects_judged": len(cands),
        "defects_on_fallback": dict(Counter(fallbacks.values())),
        "candidate_tests_per_filtered_defect": {
            "median": sizes[len(sizes) // 2] if sizes else None,
            "min": sizes[0] if sizes else None,
            "max": sizes[-1] if sizes else None,
        },
        "lost_kills": [
            {"defect_id": v["defect_id"], "test_id": v["test_id"], "reason": v["reason"]}
            for v in lost
        ],
    }


def main():
    args = sys.argv[1:]
    review = Path(args[0])
    cov_file = Path(args[args.index("--coverage-file") + 1]) if "--coverage-file" in args else Path(".coverage")
    repo_root = Path(args[args.index("--repo-root") + 1]) if "--repo-root" in args else Path(".")
    d, hunks, defects = load(review, repo_root)
    lines_by_file = per_test_lines(cov_file, repo_root)
    results = {
        "reviewed_revision": d["reviewed_revision"],
        "modes": [score(m, d, hunks, defects, lines_by_file, repo_root)
                  for m in ("conservative", "default", "function-expanded")],
    }
    out = Path(__file__).parent / "findings.json"
    out.write_text(json.dumps(results, indent=2) + "\n")
    for r in results["modes"]:
        print(f"{r['mode']:20s} surviving {r['surviving_share']:.1%}  "
              f"kill recall {r['kill_recall']:.1%}  "
              f"({r['kills_retained']}/{r['kills']} kills, "
              f"{r['pairs_surviving']}/{r['pairs']} pairs)")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
