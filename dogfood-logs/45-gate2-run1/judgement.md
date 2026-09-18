# Judgement — #45 Gate 2, run 1

Run `4e93f560eb546ef5`, continuing Gate 1's `84e1d47126b4ee99`. Base
`61c5a3c`, head `d6ab6c5`. $5.1153 over 686 live calls.

**Not clean.** Verdict INCOMPLETE. 26 obligations, every one *addressed* on code
evidence, no open questions, no unclear or not-addressed status. What stops it:
seven obligations whose test evidence is less than strongly supported, with a
recommended test each; five unrequested changes, all `in_service`; and 31 pairs
left unjudged.

## The cost, which is the finding nobody asked for

Of the $5.1153, **$4.5830 was defect-to-test pair judgement** — 658 of the 686
calls. That is the stage this branch exists to replace, paid in full, because
Gate 2 ran without `--execute`. Enumeration was $0.41; everything else together
was $0.12.

This is the strongest evidence for the milestone in the whole run, and it is
evidence *about* the run rather than about the code. A second Gate 2 with
`--execute` would measure the saving directly.

## The seven recommendations, triaged

### Real, and needing a human decision

**`candidate-tests-run-once-before-changes`** — *"The pre-change test run only
happens when `--execute` is enabled, so the delivered code can skip the required
once-before-changes run entirely on the default path."*

Correct, and the disagreement is real. `current-task.md` says "Before anything is
altered, the candidate tests run once against the code as delivered", with no
condition. The implementation makes the whole tier opt-in, on the strength of
§8.3 (execution is optional and conditional on a feasibility probe) and the fact
that #42 (M8.1, that probe) does not exist yet.

So the mandate and the code genuinely disagree, and the tool found it. Two ways
out and both are the human's: the code always runs the tests, which contradicts
§8.3; or the mandate was incomplete in never saying execution is optional. I did
not edit `current-task.md`, because doing so would change what the review says,
which is the forbidden direction.

### Real, and a disclosed limitation rather than a fixable gap

**`smallest-edit-that-makes-defect-true`** — *"nothing in the delivered code
checks that the chosen edit is actually the smallest one."*

True. The prompt asks for the smallest edit and `invalidity_reason` bounds the
edit at a recorded line count, but minimality of a semantic edit is not
mechanically decidable — there is no test that distinguishes "smallest" from
"small enough". The line bound is the operationalization, and it is tested
(`test_an_oversized_edit_is_refused`). This is worth disclosing, not fixing.

### Real, and cheap to fix

**`parser-files-still-parse`** — *"Files that have a parser but are not listed in
the hardcoded parser map are treated as having no parse check at all."*

Correct and a genuine gap. `validity.py::_PARSERS` holds `.py` alone, so a
mutated `.json` or `.toml` file passes validity however malformed it is, while
the obligation says a file that *has* a parser must still parse. Adding the
stdlib parsers closes it materially.

**`report-lists-set-aside-tests`** — *"if a set-aside entry is created with an
empty or generic reason the report will not tell the reader which tests were set
aside in a meaningful way."*

Minor but fair. `SetAsideTest.reason` has no non-empty validator;
`baseline.py::_read` always supplies one, so this can only bite a caller
constructing the record directly. A validator makes it structural, the same way
`TestOutcome` and `MutationAttempt` already require theirs.

**`execution-could-not-settle-defects`** — the stated reasoning is confused (it
describes the fallback working and calls it a risk), but underneath is a real
coverage gap: no test asserts that a `not_mutable` defect reaches `judge_pairs`
**while execution is enabled**. The wiring test covers the opposite case, where
execution settled everything and nothing was judged.

### Tool defects — queued, not acted on

**`injected-text-recorded-next-to-result`** — *"reviews that halt at the baseline
gate or never opt into execution carry no injected-text record at all."* That is
not a defect: where nothing was injected there is no injected text to record.
The recommendation asks for a record of an event that did not happen.

**`mechanical-validity-checks`** — *"a human-readable LLM response is part of
deciding whether a mutant is valid."* Wrong. The model *proposes* the edit;
validity is decided by `invalidity_reason`, four mechanical checks with no model
call, which is DR-171 Decision 3. The recommendation conflates proposing with
validating.

## The 31 unjudged pairs

All with cause `unanswered` — "offered to the judge and not answered; no verdict
was produced". This is #331's shape (twenty pairs unjudged in one run, all
naming one test; the rerun judged them all), already filed under #183. Several
here name one test,
`tests/defects/test_support.py::test_a_reasoned_empty_enumeration_gets_its_own_class_and_says_evidence_is_unobtainable`,
which matches #331's pattern. Recorded against that issue, not re-filed.

## The five unrequested changes

All disposed `in_service`, which is the benign reading, and I agree with each:
the CLI flags, the `acceptance.mutation` package, the tier fields on
`DerivedSupport` and `PairVerdict`, the two new `Review` fields with their report
blocks, and `ReviewHalted` plus `ExecutionSettings`. Every one is the mandate
being implemented rather than scope creep. Nothing is `separable` or
`risky_adjacent`.

## What did not happen that I predicted

`weaker-tier-evidence` — the Gate 1 obligation whose governing condition the
decomposer dropped — was **not** flagged. It is addressed with no recommended
test. The contradiction I expected between it and
`recorded-at-strongest-evidence-tier` did not surface at Gate 2. The Gate 1
defect stands as filed; its predicted downstream consequence did not occur.

#333 (a defect no test could ever kill pins a criterion below
`strongly_supported`) also did not visibly bite: every rating here is limited by
enumerated defects that *could* be killed, not by platform limits.
