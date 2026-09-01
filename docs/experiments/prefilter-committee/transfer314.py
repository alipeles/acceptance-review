"""Apply #316-tuned thresholds to the #314 corpus (reverse transfer).

The direction `committee316.py` cannot measure: it tunes on #316 and tests those
thresholds on #314. Run `committee316.py` first — this reads the thresholds it
wrote.
"""

import json
import re

import paths

paths.on_path()

import corpus as corpus_module
import coverage as coverage_lib
import locality
import score as score_module

WORKTREE = paths.head314()
corpus = corpus_module.load(WORKTREE)
touched = locality.touched_files(corpus, WORKTREE)


def keeps_locally(pair):
    defect = corpus.defects_by_id[pair[0]]
    if not defect.files:
        return True
    return bool(touched[pair[1]].all & defect.files)


cov = coverage_lib.CoverageData(basename=str(WORKTREE / ".coverage"))
cov.read()
root = str(WORKTREE) + "/"
file_lines = {
    f.removeprefix(root): {
        ln: {c.split("|", 1)[0] for c in ctxs if c}
        for ln, ctxs in cov.contexts_by_lineno(f).items()
    }
    for f in cov.measured_files()
}
hunks = {
    f"{fc.path}#{i}": (fc.path, h.new_start, h.new_start + max(h.new_lines, 0))
    for fc in corpus.change_set.files
    for i, h in enumerate(fc.hunks)
}
judged_tests = {t.test_id for t in corpus.tests}
cand = {}
for defect in corpus.defects:
    reachable = set()
    for ref in defect.code_refs:
        if ref not in hunks:
            continue
        path, lo, hi = hunks[ref]
        lines = file_lines.get(path, {})
        for ln in range(lo, hi):
            if lines.get(ln):
                reachable |= lines[ln]
    cand[defect.id] = reachable or set(judged_tests)


def keeps_by_coverage(pair):
    return pair[1] in cand[pair[0]]


sims = score_module.similarities(corpus, "voyage-code-4", "query", "voyage-code-4", "document")
t316 = json.loads(paths.result("committee316.json").read_text())


def parse(name):
    m = re.search(r"description ([0-9.]+), region ([0-9.]+)", name)
    return float(m.group(1)), float(m.group(2))


def scored(label, key, base):
    """One transferred filter, evaluated at #316's thresholds.

    A function rather than a loop body: the predicate below closes over `base`,
    `t_d` and `t_r`, and closing over a loop variable binds it late. It happens
    to be harmless while `score_module.apply` consumes the predicate before the
    next iteration, but the correctness of the printed numbers should not rest
    on that, so the values are bound as arguments instead.
    """
    t_d, t_r = parse(t316[key]["name"])
    out = score_module.apply(
        f"{label} @316 thresholds ({t_d:.3f}/{t_r:.3f})",
        corpus,
        lambda defect, test_id: (
            base((defect.id, test_id))
            or sims["description"][(defect.id, test_id)] >= t_d
            or sims["region"][(defect.id, test_id)] >= t_r
        ),
    )
    print(out.line())
    for defect_id, test_id in out.lost[:6]:
        print(f"    lost: {test_id}  vs  {defect_id}")
    return out


scored("union", "union_tuned_here", keeps_locally)
scored(
    "committee",
    "committee_tuned_here",
    lambda pair: keeps_locally(pair) or keeps_by_coverage(pair),
)
