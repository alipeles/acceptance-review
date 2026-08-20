# Judgement — #291 Gate 2, run 2

Run `fea8e0fd30dd6f0d`, continuing run 1 (`11c05b7b8cb69f67`). Base `bcf2779`,
head `0bd5f307`. 6 live calls, $0.0551.

## Verdict: not clean, and not cleanable by any further round.

`Task completion: INCOMPLETE`. **8** obligations with non-discriminating test
evidence, up from 5 in run 1 — the run got worse after a correction that was
itself correct.

## The correction worked; the re-run damaged three untouched obligations

Run 1 rated obligations 1 and 3 (*"the reuse rule is stated in one place that
names no stage"*) **unsupported, no mapped test**. That was right, and run 2
confirms the fix landed: both now map the two new tests and rose to *partially
supported*.

But appending those two tests to `tests/test_carry.py` moved three obligations
**down** a tier, none of which had a mapped test edited:

| # | criterion | run 1 | run 2 | its own mapped tests |
|---|---|---|---|---|
| 2 | `reuse-decision-reaches-answer-through-shared-rule` | **strongly supported** | partially supported | *identical* — same single test, byte-identical |
| 16 | `reuse-refusal-carries-reason` | **strongly supported** | partially supported | *identical* — same single test, byte-identical |
| 6 | `reuse-refusal-carries-reason-2` | **strongly supported** (5 tests) | partially supported (1 test) | lost 4, none of them edited |

Obligations 2 and 16 are the clean case: requirement text unchanged, mapped test
set unchanged, mapped test contents unchanged. The **only** thing that changed is
that two unrelated tests were appended to the same file. The rating fell anyway.

**This is #293's thesis, measured.** #293's Acceptance says *"adding a test to a
file that already holds a mapped test leaves unchanged the rating of a criterion
whose own mapped tests were not edited."* That is exactly what failed here, on a
9-line append. It is #269's Gate 2 (37 strongly supported → 4) in miniature, and
it reproduces on demand.

**And #292's enforcement did not stop it — as designed.** No rejected judgement
is reported anywhere in the output. `build_anchors` names dependency changes at
**file** granularity, so `mapped-test-file:tests/test_carry.py` was a genuine
supplied change and the judge could name it to license the downgrade. The
file-level ids were a deliberate, human-approved interim precisely because #293
was not built; this run is the evidence of what that interim costs. Sharpening
`build_anchors` to content level closes it — the anchor for obligations 2 and 16
would then name no change at all, and #292's existing rejection would hold the
stored rating.

## Why no further round was run

Every remaining fix would edit `tests/test_carry.py`, which re-triggers the same
cascade on every obligation mapped to that file. The gate is not merely
unchased — it is **unreachable by iteration**, because the act of correcting a
finding causes new ones. #292 tried three rounds and the bare obligation moved
between twins; this is the same trap with a mechanism now named.

## Disposition of every negative finding

| # | criterion | disposition |
|---|---|---|
| 2, 16, 6 | the three downgrades above | **tool defect** — #293 (file- vs content-level staleness) and #182 (mapping instability, obligation 6's 5→1 churn). Queued. |
| 4 | `reuse-rule-four-conditions` — partially supported on 5 tests | **tool defect** — #242 twin-split. Its twin #14 (`reuse-refusal-on-any-failed-check`) is *strongly supported on the same five tests*. Same rule, same evidence, two ratings. Queued. |
| 9 | `reuse-rule-applies-only-to-decomposition` — unsupported | **tool defect** — scope exclusions are treated inconsistently: of five exclusions, #10 and #12 got *"test evidence: not required — settled by the source change itself"*, while #9 and #11 got *unsupported* plus a recommendation to prove a negative across stages. Queued. |
| 11 | `merits-correctness-not-part-of-reuse-rule` — unsupported | same as #9. The recommendation asks for a case where the reuse checks pass but the stored result is "bad on merits" — the rule takes no merits input, so the test it asks for cannot be written. Queued. |
| 1, 3 | now partially supported | **addressed** in run 2 by the two new tests; the residual recommendation asks for a repo-wide docstring-duplication scan, which would be text-matching rather than behaviour. Not pursued. |
| unrequested #3 | the new tests flagged `[separable]` | advisory disposition, not a gap. Disagree on the merits — the tests are the evidence for obligations 1 and 3 — but nothing to act on. |

## What I claim, and how it is evidenced

Every substantive rule in the mandate has a test that fails if the rule is
absent. The two added in this round were verified by injection: adding a
`requirement_text` parameter to `decide` fails
`test_no_name_in_the_shared_rule_s_api_names_a_stage`, and adding an
`acceptance.evidence` import to `carry.py` fails
`test_the_shared_rule_imports_nothing_from_a_stage`; reverting both passes.
`ruff` clean on 0.16.2, `1466 passed`.

The recommendation is therefore the same call #292 got and got approved: merge
with Gate 2 not clean, deliberately, on the record above — not because the
findings are unimportant, but because every one of them is a tool defect that no
change in this PR can fix, and three of them are the defect the **next** issue
exists to remove.
