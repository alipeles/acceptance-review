# Gate 2, run 3 — #216 at `616f505`

`INCOMPLETE`, and **worse than run 2: five findings, up from two.** The only
change between the runs was adding one test that strengthens the suite.

**No finding in this run is attributable to the work.** All five are tool
defects, and three of them are the tool moving backwards while the evidence
under it improved. The implementation is, in my judgement, complete and
correctly evidenced; the gate cannot say so.

## The headline: three ratings fell as the evidence rose

`Changes since 77ae7cb7: moved` reports three obligations losing a tier:

| obligation | run 2 | run 3 | mapped set |
|---|---|---|---|
| coverage over committed task files | strongly | nominally | **byte-identical** |
| coverage over decompose-stability | strongly | nominally | lost one test that did not change |
| decision recorded in repository | strongly | partially | *gained* the three on-point tests |

The first is the cleanest instance of #180 I have seen: **the mapped set is
byte-identical across the two runs and the rating still fell.** No mapping
change, no code change to either mapped test, no task-file change. This is the
shape #167's Gate 2 recorded and the reason #182 and #183 are separate
umbrellas — a byte-identical mapped set with a flipped judgement over it.

The third is worse than instability, and is the finding I would most want acted
on. See below.

## 1. `obligation-region-level-coverage-assertion` — partially supported — TOOL DEFECT

Third run at this obligation. The recommendation now asks for:

> a claimed list item containing a nested bullet or second paragraph whose text
> is present in the file yet absent from the accounted spans. The input must
> make count-based checks pass while region coverage fails.

That is `test_the_pre_216_parse_is_detected_although_every_span_it_emits_is_exact`,
added in `616f505`, present in the diff under review, and written in response to
this obligation's own run-2 recommendation.

The mapper saw it. From the run-3 transcript, it mapped that test to **five**
obligations — and not to this one:

```
obligation-parse-nested-content-as-own-or-unread
obligation-second-paragraph-as-own-or-unread
obligation-no-unaccounted-region-for-nested-bullet-item
obligation-no-unaccounted-region-for-multi-paragraph-item
obligation-every-non-whitespace-non-heading-region-accounted
```

So the tool prescribed a test, was given it, mapped it accurately to five
neighbours, withheld it from the one obligation that asked for it, and then
re-issued the same prescription. **#173's shape** — the on-point test rejected
while unrelated ones are accepted.

Two rounds of real strengthening came out of this obligation (runs 1 and 2), so
the recommendations were worth reading. This third round has nothing left to
build. **Attributed to #173**, filed as `#173 (comment 5220724039)`.

## 2 & 3. `…coverage-on-committed-task-files`, `…coverage-on-decompose-stability-corpus` — TOOL DEFECT

Both strongly supported in run 2, both nominally supported here.

Obligation 7's mapped set is byte-identical between the runs
(`test_the_repositorys_own_task_files_are_fully_covered`,
`test_parses_the_projects_own_current_task_file`). Obligation 8 lost
`test_purpose_built_fixtures_are_fully_covered` from its mapped set — a test
that did not change in the interval.

Both recommendations ask for what the tests already do: *run the assertion
against the actual committed task files* and *against the actual
decompose-stability corpus*. Both are parametrised over exactly those globs,
and `test_the_corpora_under_test_are_not_empty` exists precisely so a glob that
matches nothing cannot turn them into zero silent passes.

**Attributed to #180**, filed as `#180 (comment 5220738963)`.

## 4. `obligation-region-level-total-coverage-tests` — unsupported — TOOL DEFECT

Third consecutive run, same obligation id, same absorption of `constraint-11`
(pydantic schemas) and `constraint-12` (no live model calls) into an obligation
that states neither, and still a duplicate of obligations 7 and 8.

**Attributed to #223**, filed as `#223 (comment 5220684032)`.

## 5. `obligation-decision-recorded-in-repository` — partially supported — TOOL DEFECT, and the sharpest one

Run 2 rated this **strongly supported** on four tests that have nothing to do
with recording a decision. Run 3 rated it **partially supported** — *after*
mapping the three tests that actually pin DR-216:

```
13.12  test_dr_216_records_that_the_real_corpora_cannot_falsify_the_guard
13.13  test_dr_216_records_the_nested_content_decision_as_resolved
13.14  test_dr_216_states_the_decision_uniformly_rather_than_per_block_type
```

And its recommendation is:

> assert the persisted text contains the chosen nested-content policy… The input
> should be the actual `docs/DR-216-parser-accounts-decomposer-splits.md` file
> as committed in the repo.

**That is 13.13, which is in its own mapped set.** The rating fell as the
evidence improved, and the prescribed test is one the strength call was looking
at when it prescribed it.

This is not #180 (the mapping changed, and changed for the better) and not #173
(the mapping is correct here). It is a strength-judgement failure with the
mapping working: correct discriminating evidence present, mapped, and
under-rated, with a recommendation duplicating a test in its own set.

**Filed as #225**, child of #183.

## Not blockers

Seven unrequested changes, all `in_service` — advisory. One deserves an answer
rather than a shrug:

> The new coverage helper excludes list markers and indentation from the
> asserted region set… this changes what the assertion considers covered and
> could let dropped marker-adjacent content escape detection.

A fair question about a real carve-out. The answer is that `_MARKER` matches
only leading indentation, the bullet or number, and the whitespace after it —
never the text that follows, which stays under assertion. Dropped content is the
*text* of a block, and a block's text is neither a heading nor a marker, so
excluding markers can weaken the assertion's reach but cannot produce a false
pass on dropped content. That rationale is in `region_coverage.py`'s docstring;
this run is the reason it is worth keeping there.

## Standing

**Gate 2 did not come back clean, and the branch moves forward anyway** under
CLAUDE.md's second permitted disposition: every remaining finding is attributed
to a tool defect with a backlog item filed before moving on. Reviewed and
approved by the human, then filed:

| finding | tracked as |
|---|---|
| on-point test withheld from the obligation that prescribed it | #173 (comment 5220724039) |
| two ratings fell, one on a byte-identical mapped set | #180 (comment 5220738963) |
| `constraint-11`/`constraint-12` absorbed, third consecutive run | #223 (comment 5220684032) |
| rating falls as evidence improves; recommendation names a test in its own mapped set | **#225**, new child of #183 |

Nothing here is suppressed and nothing is waved off as noise. What the gate
could not certify is now four tracked defects in the tool, each with the run
that produced it as its evidence — which is what dogfooding is for.

The distinction that matters for anyone reading this later: **runs 1 and 2 found
real gaps and made the work better; run 3 found only tool defects.** Three
rounds is not three rounds of the same thing.
