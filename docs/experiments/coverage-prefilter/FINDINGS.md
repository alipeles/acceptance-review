# Coverage-context prefilter — findings

**The rule that saves money fails the kill-recall bar, and the rule that keeps
kills saves nothing.** Ignoring import-only lines, coverage reachability
excludes 61.3% of the 23,808 pairs (which would have cut the pair stage from
$6.02 to roughly $2.35) but excludes 43 of the 268 recorded kills, 84.0%
recall. The conservative variant keeps 267 of 268 kills and excludes 3.5%.
Neither clears the bar `defects/reachability.py` sets for a silent prefilter:
a wrong exclusion silently un-covers a defect, which is the failure #312
exists to remove.

Measured on the #316 Gate 2 review: **23,808 pairs, 268 kills, a 1.1% kill
rate**, 48 defects against 496 tests, head `3e1d3a9`. Coverage recorded from
one instrumented suite run at that revision (5m15s). Method and traps are in
`README.md`; raw numbers, including every lost kill with the judge's stated
reason, in `findings.json`; the scorer is `score.py`.

## The headline

| rule | pairs excluded | kill recall | lost kills |
|---|---|---|---|
| conservative (import-time line keeps every test) | 3.5% | 99.6% | 1 |
| ignore import-only lines | **61.3%** | **84.0%** | 43 |
| + expand to enclosing function bodies | 61.3% | 84.0% | 43 (same 43) |

Fallback (judge everything) fired for 9 of 48 defects under the usable rules:
7 module-level regions, 1 non-Python ref, 1 region whose lines never execute.

## Why the exclusion rate is not higher

The median filtered defect is reachable by 137 of the 496 judged tests. The
suite is pipeline-level, so most tests execute most of the changed code, and
coverage overlap is broad. On this corpus, coverage alone is a 2.6x lever, not
a 10x one.

## The 43 disagreements, and why they are the real product of this experiment

Function-body expansion recovering nothing means the 43 killing tests never
execute the implicated code at all. Three distinct things hide in that:

1. **Data dependencies coverage cannot see.** Tests asserting on README and
   decision-record text kill `docs-update/*` and the benchmark-warning defects
   through file reads, not execution. A real filter needs a file-read channel
   or a fallback for defects in non-code artifacts.
2. **Absence defects.** For `not_wired` / `documented_not_implemented` /
   `missing_case` defects, the implicated lines are where behavior *should*
   be, and a test can fail on the absence through code that lives elsewhere.
   Line reachability of the named region is the wrong question for these.
3. **Suspect verdicts.** Several lost kills look wrong as verdicts: the
   `deterministic-runs-byte-identical` kills credited to
   `tests/test_determinism.py` require the unusable-answer path to execute,
   and the replay fixtures never drive it. Coverage says the test cannot fail
   there; the judge said it would. The cleanest example is the one kill even
   the conservative rule loses:
   `no-recording-or-judging-failures/pair-mapping-judges-defects-against-tests`
   x `test_summary_pass.py::test_a_span_decided_twice_is_refused`, judged a
   kill because the test "asserts duplicate span dispositions are rejected",
   a summary-pass behavior with no path to pair mapping.

Classes 1 and 2 are filter blind spots; class 3 is judge error. Nothing static
separates 2 from 3, which is exactly M8.4's question: inject the defect, run
the test, see who was right.

## What this licenses

- **Not** shipping coverage reachability as a silent prefilter for the static
  judge at 84% recall.
- **Using the coverage map as M8.4's test selection.** Under injection the
  exclusion becomes sound for runtime defects: a test that never executes a
  line cannot fail on a mutation of it, and doc/absence defects stay on the
  judge-everything fallback (9 of 48 here). At the suite's measured ~0.2s per
  test, 48 injections times a median 137 candidate tests is on the order of 20
  CPU-minutes and zero tokens, against $6.02 of static judging per run.
- **The 43 disagreement pairs as the injection pilot's case list**, plus a
  sample of retained kills. Adjudicating them measures pair-verdict accuracy
  against ground truth for the first time (#315's labels are the only current
  proxy).
- **Scoring coverage as a third voter in `pair-prefilter`'s
  reject-only-when-all-reject rule**, on one shared corpus. Unrun; the two
  filters' failure surfaces (wording vs data dependencies) suggest the
  conjunction keeps kills the way the embedding pair did while excluding more
  than its 22.0%.
