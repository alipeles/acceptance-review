# #358 — The reachability prefilter proves "no path" from a test that reads its subject from disk

At #348's Gate 2 run 3 (`dogfood-logs/348-gate2-run3/`), `tests/test_rank_prefilter_findings.py` — which opens `docs/experiments/rank-prefilter/FINDINGS.md` and the replay logs by path and asserts on their content — was `[prefiltered]` against both defects of the criterion about that file, with the reason "the test's module imports no first-party module, the test takes no fixture, and it references no name defined in docs/experiments/rank-prefilter/FINDINGS.md — no path to the defect exists". The criterion was rated `unsupported` (0 of 2), because a prefiltered pair is treated as a proven survival — worse than run 2's `indeterminate`, before the test existed. The test does discriminate: changing one figure in FINDINGS.md fails it. `tests/test_decision_records.py` was excluded the same way.

The prefilter follows imports, fixtures and Python names. A non-Python implicated file has none of those, so every test is "proved" unreachable from it — including the tests that read it. The prefilter's contract is that it excludes only what it can prove; here it proved something false. Any criterion about a document, a config file or a fixture read from disk is exposed.

## Deliverable

The prefilter proves no path only where it can: a defect whose implicated files are not Python modules is not prefiltered on import evidence (its pairs go to the judge), or a test whose source names the implicated file's path counts as reaching it.

## Acceptance

Replaying #348's Gate 2 run 3, no pair between `tests/test_rank_prefilter_findings.py` and a defect implicating `FINDINGS.md` is `prefiltered`.
