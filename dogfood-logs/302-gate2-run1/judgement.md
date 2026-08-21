# Judgement — #302 Gate 2, run 1

`acceptance check --task current-task.md --base 8cc8104 --mode record --continue 094ddce626d72e7f`
Base `8cc8104`, head `b6e672f`. **Verdict: INCOMPLETE. The gate did not pass.**

> 1 obligation(s) not fully implemented (exclude-measurement-harness-calls);
> 2 obligation(s) with non-discriminating test evidence
> (test-fails-on-inconsistent-answer-formats, test-fails-on-withheld-conclusion-condition).

16 of 18 obligations are addressed and strongly supported. Three findings below.

## Finding 1 — `exclude-measurement-harness-calls` is `not addressed` on evidence identical to three obligations that are `addressed`. TOOL DEFECT.

Four scope exclusions carry the **same** code evidence, verbatim:

| # | obligation | code evidence | status |
|---|---|---|---|
| 10 | does not alter request content order | examined 22 changes across 11 files; none breaches this boundary | `addressed` |
| 11 | does not alter the answer format of too-short-prefix calls | *(identical)* | `addressed` |
| 12 | does not alter reporting tokens, cost or reused-token share | *(identical)* | `addressed` |
| **13** | **excludes measurement-harness calls from the review run scope** | *(identical)* | **`not addressed`** |

Same sentence, opposite verdict. Nothing in the diff distinguishes them — the
review says so itself in the very line it then rules against.

**The cause is upstream, in decomposition, and it is visible at Gate 1.**
`obligations.py:218-246` contracts a scope exclusion to yield "EXACTLY ONE
obligation stating the ABSENCE of the excluded work", and names the wrong forms:
the excluded work restated as work to do, or asserted as a property to hold.
`exclusion-06` got exactly the first wrong form —

> `exclude-measurement-harness-calls` **[functional]**
> "The change **excludes** model calls issued by the measurement harness from the
> review run scope."

— a positive statement of work the change must *do*, where `exclusion-01…05` all
got `[regression]` obligations of the sanctioned "The change does not alter X"
form. The coverage classifier then looked for a change doing that work, found
none, and correctly reported `not addressed` for the obligation it was given.
The classifier is not the defect; the obligation is.

Reproducible: `exclusion-06` is typed `[functional]` in Gate 1 runs 4 and 5 while
its five siblings are `[regression]`.

Queued as a filing against **#181** (decomposition). Not addressed in code, and
must not be: writing a change to "exclude harness calls" would be inventing work
to satisfy a malformed obligation.

## Finding 2 — two obligations reported `unsupported / (no mapped test)` whose tests exist and are cited elsewhere in the same report. #245.

| # | obligation | reported | the test that demonstrates it |
|---|---|---|---|
| 14 | `test-fails-on-inconsistent-answer-formats` | `unsupported`, `(no mapped test)` | `tests/test_supplied_ids.py::test_every_batch_of_a_stage_asks_for_the_identical_schema` — **cited by obligation 1 as 1.5** |
| 17 | `test-fails-on-withheld-conclusion-condition` | `unsupported`, `(no mapped test)` | `tests/test_supplied_ids.py::test_a_test_the_response_passes_over_is_recorded_as_unanswered` — **cited by obligation 16 as 16.1** |

Both tests assert precisely what the obligation demands. #14's test asserts two
batches of one stage send byte-identical `response_format`; #17's asserts that a
passed-over item leaves the obligation `indeterminate` with
`unmapped_obligation_ids == []`, which *is* the withheld conclusion.

Same shape as #265's Gate 2: an obligation told its evidence is missing while a
sibling is strongly supported citing that very test. The mapper returned the id
for one obligation and not for its twin.

**The recommendations were read before forming this view**, as the gate requires.
Both describe building a test that already exists — #14's asks for "two
reusable-prefix calls from one stage with different answer formats", which is
`test_every_batch_of_a_stage_asks_for_the_identical_schema`. Recorded against
**#245**. Writing near-copies would chase a rating rather than fix a defect.

## Finding 3 — one `separable` unrequested change. NEEDS A HUMAN DECISION.

> 3. [separable] `unusable_answer_finding` now changes its description based on
> `answer.reason`, instead of always using the previous generic wording.
> `src/acceptance/pipeline.py`

The tool is right. This is a fix to a **pre-existing** defect — every unusable
answer was described as an id "never supplied to that call", which was already
wrong for #204's no-linking rejection — and no obligation in this mandate asks
for it. It is here because #302 makes the wrong description much more visible: an
answer that never arrived was being reported as an id that was supplied.

Three honest options, none of which I took unilaterally: leave it and say so in
the PR; lift it onto `main` as its own change; or add a requirement covering it
and re-run the gate. My recommendation is the second — it is a real fix, it
stands on its own, and it is one commit.

The other three unrequested changes are `in_service` and advisory: duplicate
recording in mapping and linking, and the test doubles reading ids off the prompt.

## Mapping quality — checked, per DR-164

Not half-blind. 18 obligations, 16 with mapped tests, and the two without are
Finding 2's twins whose ids the mapper returned elsewhere in the same run. This
is not the failure mode where mapping returns mostly empty `obligation_ids`.

## Open questions

None raised. Per **#303** that is the axis reporting nothing, not a clean result.

## Not clean, and not negotiable

Every obligation addressed: **no** (13). Every obligation strongly supported:
**no** (14, 17). No recommended tests: **no** (two). No other flags: **no** (one
`separable`). The gate stops here.
