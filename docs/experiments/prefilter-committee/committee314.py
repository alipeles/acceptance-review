"""Committee scoring on the #314 corpus: locality + embeddings + coverage.

Reuses the pair-prefilter experiment's own corpus, locality and similarity code
(recorded Voyage vectors served from the content-addressed cache), and adds a
coverage-reachability voter built from an instrumented suite run at the corpus
head. Rule: reject a pair only when every voter rejects it, solved with the
experiment's own best_lossless_union.
"""

import json

import paths

paths.on_path()

import corpus as corpus_module
import coverage as coverage_lib
import locality
import score as score_module

WORKTREE = paths.head314()

corpus = corpus_module.load(WORKTREE)
print(
    f"corpus: {len(corpus.defects)} defects x {len(corpus.tests)} tests = "
    f"{len(corpus.judged)} pairs, {len(corpus.kills)} kills"
)

# ---- voter 1: locality ------------------------------------------------------
touched = locality.touched_files(corpus, WORKTREE)


def keeps_locally(pair):
    defect = corpus.defects_by_id[pair[0]]
    if not defect.files:
        return True
    return bool(touched[pair[1]].all & defect.files)


# ---- voter 2: coverage reachability (default rule from coverage-prefilter) --
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
cov_candidates = {}
cov_fallback = {}
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


def keeps_by_coverage(pair):
    return pair[1] in cov_candidates[pair[0]]


cov_alone = score_module.apply(
    "coverage reachability (binary)",
    corpus,
    lambda defect, test_id: test_id in cov_candidates[defect.id],
)
print(cov_alone.line())
print(f"  ({len(cov_fallback)} of {len(corpus.defects)} defects on keep-all fallback)")
score_module.report_losses(corpus, cov_alone)

# ---- voter 3+4: embeddings (code-4 both sides, from the recorded cache) -----
sims = score_module.similarities(corpus, "voyage-code-4", "query", "voyage-code-4", "document")

# ---- baseline replication: locality + embeddings (the shipped 22.0%) --------
baseline = score_module.best_lossless_union(
    corpus, keeps_locally, sims["description"], sims["region"]
)
print("\nreplication of pair-prefilter union (locality + embeddings):")
print(baseline.line())


# ---- committee: locality OR coverage OR embeddings --------------------------
def keeps_locally_or_covered(pair):
    return keeps_locally(pair) or keeps_by_coverage(pair)


committee = score_module.best_lossless_union(
    corpus, keeps_locally_or_covered, sims["description"], sims["region"]
)
committee.name = "committee " + committee.name.split("union ", 1)[-1]
print("\ncommittee (locality + coverage + embeddings):")
print(committee.line())

paths.result("committee314.json").write_text(
    json.dumps(
        {
            "corpus": {
                "pairs": len(corpus.judged),
                "kills": len(corpus.kills),
                "defects": len(corpus.defects),
                "tests": len(corpus.tests),
                "head": corpus.head_revision,
            },
            "coverage_alone": cov_alone.as_dict(),
            "coverage_fallback_defects": sorted(cov_fallback),
            "union_replication": baseline.as_dict() | {"name": baseline.name},
            "committee": committee.as_dict() | {"name": committee.name},
        },
        indent=2,
    )
)
print("\nwrote committee314.json")
