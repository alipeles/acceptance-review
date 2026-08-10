# Judgement — #232/#219/#230 bundle, Gate 1, run 7 (post-fix)

Run at `d70d77c`, after both prompt fixes. 21 requirements, 14 with obligations,
7 declined. **No open questions.**

## Fixed, and verified on this repo's own task file

**#219 / #230 — scope exclusions.** All six now decline uniformly, with reasons
that name what is out of scope and assert nothing about the change:

```
[exclusion-05] Whether obligation identifiers are stable across task-file edits, which is #231.
    -- no obligation, deliberately
       Names identifier stability across task-file edits as out of scope for this change.
```

Compare run 4, where the same bullet derived *"Keep obligation identifiers stable
across task-file edits"* — the excluded work as a requirement. Six of six correct,
four runs of inversion ended. This is the sharpened #230 closed.

**#232 — framing preserved.** All five Completion expectations keep "A test
asserts that …" verbatim, all typed `regression`. Run 1 was 0 of 5; run 4 was 2
of 5.

## Not fixed: derivation invents the framing on requirements that do not demand a test

`constraint-02`, `constraint-05` and `constraint-07` state behaviours and say
nothing about a test. All three derived as "A test asserts that …":

```
[constraint-07] Two runs over byte-identical task text produce byte-identical review state.
    -> test-byte-identical-review-state  [regression/explicit]   (also serves completion-06)
       A test asserts that two runs over byte-identical task text produce byte-identical
       review state.
```

Which makes the Constraint and its Completion twin one statement, so linking
merges them — correctly, since by then they *are* the same. The demand for the
test disappears exactly as it did before the fix, by the opposite route.

**Two attempts, same failure.** The first cut caused it (run 6: `constraint-05`,
`-07`). Adding the converse rule and a test for it did not clear it (run 7:
`constraint-02`, `-05`, `-07`). Stopped and escalated per *Working agreement* §3
rather than making a third attempt.

**The control fixture does not reproduce it.** `tests/prompts/
test_decomposition_prompt.py::test_a_constraint_stating_a_behaviour_is_not_given_test_framing`
passes for all three invoice constraints. So the committed test is currently
weaker than this repo's task file, and a fix validated only against the corpus
would look complete while this stays broken. The difference is plausibly that
this file's constraints are *about* tests and obligations as subject matter —
but `constraint-07` contains no test vocabulary at all and was still framed, so
that does not fully explain it.

## Gate 2 status

Not run. Gate 2 cannot come back clean while three Constraints carry invented
framing, so the escalation comes first.
