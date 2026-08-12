# #191 Gate 2, round 2 — judgement

**Not clean.** INCOMPLETE: four obligations with non-discriminating test
evidence. No open questions.

The diff from round 1 is **added tests only** — the three tests closing round
1's findings (`8e49ead`) and nothing else.

## One of round 1's four survived, correctly

`test-verdict-call-carries-configured-bounded-obligations` is flagged again. The
recommendation this time asks for exactly the test `8e49ead` added
(`test_the_verdict_bound_counts_criteria_and_not_defects`: uneven defect counts,
more criteria than the batch size). Its `detects` clause is also garbled —
"the number of defects carried per call would be bounded by the number of
obligations instead of the configured defect-verdict batch size" inverts the two
dimensions, where round 1's statement of the same finding was coherent. No
action: the test the recommendation describes is present.

## Three obligations fell from `strongly supported` to non-discriminating

Nothing about their own evidence changed.

| obligation | round 1 | round 2 | real? |
|---|---|---|---|
| `test-editing-mapped-test-leaves-other-obligation-defects-unchanged` | strongly supported | non-discriminating | **yes** |
| `test-adding-mapped-test-leaves-obligation-defects-unchanged` | strongly supported | non-discriminating | no |
| `test-review-pipeline-uses-separated-defect-verdict-steps` | strongly supported | non-discriminating | no |

**The first is a real finding and the run deserves credit for it.** The test
called `enumerate_defects` twice with identical arguments and compared the
requests. That demonstrates the request is deterministic and says nothing
whatever about insensitivity to a *test edit* — the property the split exists to
provide. Fixed in `dbff85e`: ob-1's mapped test is now genuinely renamed, with
different inputs and a different assertion, and ob-2's enumeration request must
stay byte-identical.

**The other two recommend tests that already exist and that the same report
cites.** The recommendation for `test-adding-mapped-test-...` asks for a test
that adds a mapped test and observes the enumerated defects unchanged; that is
`test_adding_a_test_leaves_the_obligations_enumeration_request_unchanged`, cited
in that obligation's own evidence list. Same for the pipeline one, whose
recommendation asks for a client double recording every schema name and a result
that depends on the verdict stage — which is what
`test_the_pipeline_reaches_its_defect_verdicts_through_the_separated_steps`
does. #225-family: a recommendation making a checkable false claim about the
code. Queued as a filing against #225.

## Why this instance matters more than the previous ones

It is **post-change, on the branch that fixes the enumeration half.** #191
stabilises which defects are *named*; these three obligations moved anyway.

That is evidence the verdict half is a separate defect that #191 does not close
— which is what #192 is for — and it is the first time the separation could be
observed at all. Before #191 no defect wording ever repeated between runs (114
distinct keys over 3 runs, each seen once), so the verdict axis had nothing to
compare and reported zero differences by construction.

## Status

The gate is **re-armed by `dbff85e` and has not been re-run.** Each round so far
has produced one real gap plus two restatements of tests already present, so
round 3 is a deliberate decision, not a reflex.
