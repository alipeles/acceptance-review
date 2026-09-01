"""Committee scoring on the #316 corpus, plus cross-corpus threshold transfer.

Same three voters as committee314.py: locality, coverage reachability, and the
code-4 embedding pair (description + region), joined by reject-only-when-all-
reject. Embeddings for this corpus are fresh Voyage calls through the
experiment's own recorded client (paced, cached content-addressed).
"""

import json

import paths

paths.on_path()

import corpus316
import coverage as coverage_lib
import locality
import score as score_module

WORKTREE = paths.head316()

corpus = corpus316.load()
print(
    f"corpus: {len(corpus.defects)} defects x {len(corpus.tests)} tests = "
    f"{len(corpus.judged)} pairs, {len(corpus.kills)} kills",
    flush=True,
)

# ---- voter 1: locality ------------------------------------------------------
touched = locality.touched_files(corpus, WORKTREE)


def keeps_locally(pair):
    defect = corpus.defects_by_id[pair[0]]
    if not defect.files:
        return True
    return bool(touched[pair[1]].all & defect.files)


local = score_module.apply(
    "locality (all signals)",
    corpus,
    lambda defect, test_id: True if not defect.files else bool(touched[test_id].all & defect.files),
)
print(local.line(), flush=True)

# ---- voter 2: coverage reachability -----------------------------------------
cov = coverage_lib.CoverageData(basename=str(WORKTREE / ".coverage"))
cov.read()
root = str(WORKTREE) + "/"
file_lines = {}
for f in cov.measured_files():
    rel = f.removeprefix(root)
    file_lines[rel] = {
        ln: {c.split("|", 1)[0] for c in ctxs if c}
        for ln, ctxs in cov.contexts_by_lineno(f).items()
    }

hunk_ranges = {}
for fc in corpus.change_set.files:
    for i, h in enumerate(fc.hunks):
        hunk_ranges[f"{fc.path}#{i}"] = (fc.path, h.new_start, h.new_start + max(h.new_lines, 0))

judged_tests = {t.test_id for t in corpus.tests}
cov_candidates, cov_fallback = {}, {}
for defect in corpus.defects:
    cand = set()
    for ref in defect.code_refs:
        if ref not in hunk_ranges:
            continue
        path, lo, hi = hunk_ranges[ref]
        lines = file_lines.get(path, {})
        for ln in range(lo, hi):
            if lines.get(ln):
                cand |= lines[ln]
    if not cand:
        cov_fallback[defect.id] = True
        cand = set(judged_tests)
    cov_candidates[defect.id] = cand

cov_alone = score_module.apply(
    "coverage reachability (binary)",
    corpus,
    lambda defect, test_id: test_id in cov_candidates[defect.id],
)
print(cov_alone.line(), flush=True)


def keeps_by_coverage(pair):
    return pair[1] in cov_candidates[pair[0]]


# ---- voters 3+4: embeddings (fresh Voyage, cached) --------------------------
sims = score_module.similarities(corpus, "voyage-code-4", "query", "voyage-code-4", "document")
print("embeddings ready", flush=True)

for kind in ("description", "region"):
    top = score_module.best_lossless(
        score_module.sweep(f"{kind} vs test source", corpus, sims[kind])
    )
    print(f"{kind:<12} best lossless: {top.line()}", flush=True)

# ---- unions -----------------------------------------------------------------
baseline = score_module.best_lossless_union(
    corpus, keeps_locally, sims["description"], sims["region"]
)
print("\nheld-out union (locality + embeddings):")
print(baseline.line())


def keeps_locally_or_covered(pair):
    return keeps_locally(pair) or keeps_by_coverage(pair)


committee = score_module.best_lossless_union(
    corpus, keeps_locally_or_covered, sims["description"], sims["region"]
)
print("committee (locality + coverage + embeddings):")
print(committee.line())


# ---- cross-corpus transfer --------------------------------------------------
def at_thresholds(name, keeps_base, t_desc, t_region):
    out = score_module.apply(
        name,
        corpus,
        lambda defect, test_id: (
            keeps_base((defect.id, test_id))
            or sims["description"][(defect.id, test_id)] >= t_desc
            or sims["region"][(defect.id, test_id)] >= t_region
        ),
    )
    print(out.line())
    if out.lost:
        for defect_id, test_id in out.lost[:6]:
            print(f"    lost: {test_id}  vs  {defect_id}")
    return out


print("\n#314-tuned thresholds applied here (the held-out test):")
tuned314 = json.loads(paths.result("committee314.json").read_text())


def _parse(name):
    import re

    m = re.search(r"description ([0-9.]+), region ([0-9.]+)", name)
    return float(m.group(1)), float(m.group(2))


t_d_u, t_r_u = _parse(tuned314["union_replication"]["name"])
t_d_c, t_r_c = _parse(tuned314["committee"]["name"])
x_union = at_thresholds(
    f"union @314 thresholds ({t_d_u:.3f}/{t_r_u:.3f})", keeps_locally, t_d_u, t_r_u
)
x_comm = at_thresholds(
    f"committee @314 thresholds ({t_d_c:.3f}/{t_r_c:.3f})", keeps_locally_or_covered, t_d_c, t_r_c
)

paths.result("committee316.json").write_text(
    json.dumps(
        {
            "corpus": {
                "pairs": len(corpus.judged),
                "kills": len(corpus.kills),
                "defects": len(corpus.defects),
                "tests": len(corpus.tests),
                "head": corpus.head_revision,
            },
            "locality_alone": local.as_dict(),
            "coverage_alone": cov_alone.as_dict(),
            "coverage_fallback_defects": sorted(cov_fallback),
            "union_tuned_here": baseline.as_dict() | {"name": baseline.name},
            "committee_tuned_here": committee.as_dict() | {"name": committee.name},
            "union_at_314_thresholds": x_union.as_dict(),
            "committee_at_314_thresholds": x_comm.as_dict(),
        },
        indent=2,
    )
)
print("\nwrote committee316.json")
