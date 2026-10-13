# Hand check: did the coding agent plant the defects it was asked to plant?

About 30–40 minutes. Six examples. Each one has everything you need on this
page; you should not need to open any other file.

## What you are checking, and why it matters

Our review tool judges whether a set of tests is any good. One way it does that
is by **planting a defect on purpose**: it takes a description of a plausible
bug, edits a copy of the code so the bug is really there, and runs the tests
against that broken copy. If a test fails, the tests catch that bug. If every
test still passes, the tests miss it.

That only works if the edit really plants **the bug that was described**. An
edit that breaks something else, or changes nothing that matters, produces a
test result that means nothing — and the tool would then praise or blame the
tests for the wrong reason.

The edits below were written by **Claude Code** (a coding agent). Each was
then labelled by **a second Claude model acting as judge**. Because both are
Claude, they may share blind spots, so their agreement is weak evidence. Your
job is to be the independent check: for each example, decide for yourself, then
open the judge's answer and see whether you agree.

Please decide **before** opening the judge's answer. Its answer is hidden in a
fold for that reason.

## Background you need

**The code being broken on purpose.** All six examples come from an earlier
version of this same review tool. That version had just gained the feature
described above (plant a bug, run the tests, see who notices). So the "code
under test" in every example is part of that feature.

**How each bug is described.** Every bug comes with two sentences:

- **Should do** — what correct code does.
- **Would do if broken** — what the code does once the bug is present.

A good edit makes the code go from "should do" to "would do if broken", and
does it the way a careless programmer might — a small slip, not a demolition.

**The verdicts you can give an edit:**

- **Plants it** — before the edit the code did "should do"; after it, the code
  does "would do if broken". A small, plausible slip.
- **Already broken** — the code *already* did "would do if broken" before
  anyone touched it. There was nothing to plant, so any edit is wrong.
- **Something else** — the edit changes behaviour, but not the behaviour the
  bug describes (or changes nothing anyone would notice).
- **Too broad** — it plants the bug but also breaks far more, so a failing test
  could be failing for the wrong reason.
- **Can't tell** — the code shown is not enough to decide.

**When the agent made no change.** The agent was told: if the code already
does "would do if broken", or if no single small edit can plant the bug, make
no change at all. So in two examples below the question is instead: **was
making no change the right call?**

**How to read the code.** Code is Python. In the edits, a line starting with
`-` was removed and a line starting with `+` was added.

---

## Example 1 — an empty explanation should be refused

**The bug, as described**

- **Should do:** every record of a failed attempt to plant a bug must carry a
  written explanation of why it failed.
- **Would do if broken:** a failed attempt can be recorded with an empty
  explanation.

**The code before the edit** — a check that runs whenever an attempt record is
created. `settled` means the attempt succeeded; `has_reason` means the
explanation is not blank. If the attempt failed and there is no explanation, it
raises an error and the record is refused.

```python
def _reason_accompanies_every_unsettled_attempt(self):
    has_reason = bool(self.reason.strip())
    if not self.settled and not has_reason:
        raise ValueError(
            "... must carry a reason: a defect the stage tried and could not "
            "settle has to stay distinguishable from one it never tried"
        )
    return self
```

**What the agent did**

```diff
-        if not self.settled and not has_reason:
+        if not self.settled and not has_reason and False:
```

Adding `and False` makes the whole condition always false, so the error is never
raised.

**Two questions for you**

1. Does the edit plant the described bug?
   - [ ] Plants it  - [ ] Already broken  - [ ] Something else  - [ ] Too broad  - [ ] Can't tell
2. A planted bug is supposed to look like a slip a careless programmer could
   make. Does `and False` count, or is it obviously deliberate sabotage that no
   real programmer would write?
   - [ ] Fine as a planted bug  - [ ] Not plausible, and that should count against it

Notes:

<details>
<summary>The judge's answer (open after deciding)</summary>

**Plants it.** That check was the only thing requiring an explanation on a
failed attempt; with `and False` it never fires, so a failed attempt with a
blank explanation is now accepted. Successful attempts are unaffected.

The judge did not consider whether `and False` is plausible as a slip.

For comparison, the older one-call builder (the cheaper approach the agent is
meant to improve on) changed the same line to require an explanation only on
*successful* attempts. The judge called that **too broad**: successful attempts
are always created without an explanation, so every success would now be
refused too.

</details>

---

## Example 2 — no tests left to run (agent made no change)

**The bug, as described**

- **Should do:** even if the first, untouched test run leaves no usable tests,
  the tool should still run the tests against the broken copy.
- **Would do if broken:** when the first run leaves no usable tests, the tool
  immediately records every bug as "not attempted" and runs nothing against the
  broken copy.

**The code as it was** — the start of the function that plants and tests every
bug. `baseline` is the result of the first, untouched test run;
`usable_tests` is the list of tests that passed in it.

```python
def run_mutations(defect_sets, change_set, project_root, baseline, ...):
    defects = [defect for defect_set in defect_sets for defect in defect_set.defects]

    if baseline.halted:
        return [_not_attempted(defect, "the review halted before injection: ...")
                for defect in defects]
    if not baseline.usable_tests:
        return [
            _not_attempted(
                defect,
                "no candidate test survived the control run, so there is nothing a "
                "mutant could be observed against",
            )
            for defect in defects
        ]
    ...  # otherwise, plant each bug and run the tests
```

**What the agent did:** made no change.

**Your question:** was making no change the right call? (The agent was told to
make no change if the code already does "would do if broken".)

- [ ] Yes — the code already does "would do if broken"
- [ ] No — there was a small edit that would have planted it
- [ ] Can't tell

Notes:

<details>
<summary>The judge's answer (open after deciding)</summary>

**Right call: already broken.** The second `if` block does exactly what "would
do if broken" describes, word for word: with no usable tests, every bug is
recorded as not attempted and nothing runs.

For comparison, the older one-call builder deleted that `if` block. The judge
called that a **repair**, not a planted bug: it moves the code toward "should
do".

</details>

---

## Example 3 — weak evidence should stay labelled weak

One extra idea is needed here. The tool labels every piece of evidence with how
strong it is. Two levels matter:

- **Predicted** — a model read the code and the tests and *predicted* whether a
  test would catch the bug. Weaker.
- **Observed** — the tests were actually run against a broken copy and one
  failed. Stronger.

When one bug has several pieces of evidence, the tool rates the bug at the
**weakest** level among them: one guess makes the whole thing a guess. In code,
the levels are ordered weakest to strongest, so `min(...)` picks the weakest.

At the time, the requirement was that this new "observed" evidence should
**not** yet count as strong — it was being trialled — and should stay at the
weaker level everywhere.

**The bug, as described**

- **Should do:** any evidence feeding this judgement is recorded and kept at
  the weaker level throughout.
- **Would do if broken:** results from actually running the tests are recorded
  at the stronger "observed" level, and that stronger level flows through into
  the bug's final rating.

**The code as it was** — three relevant pieces.

When the tests are run against a broken copy, each result is recorded like
this. `DEFECT_KILLED` is the stronger "observed" level:

```python
verdicts.append(
    PairVerdict(
        defect_id=attempt.defect_id,
        test_id=test_id,
        kills=test_id in killing,
        tier=EvidenceTier.DEFECT_KILLED,
        ...
    )
)
```

Bugs that running the tests already settled are **not** sent to the model for
a prediction; only the unsettled ones are. Then both kinds of evidence are
combined into one list:

```python
pair_mapping = judge_pairs(
    remaining_defect_sets(attempts, defect_sets),  # only the bugs running could not settle
    ...
)
verdicts = executed_verdicts + pair_mapping.verdicts
```

Each bug's level is the weakest among its evidence:

```python
for verdict in verdicts:
    known = tier_by_defect.get(verdict.defect_id)
    tier_by_defect[verdict.defect_id] = (
        verdict.tier if known is None else min(known, verdict.tier)
    )
```

**What the agent did**

```diff
-            verdict.tier if known is None else min(known, verdict.tier)
+            verdict.tier if known is None else max(known, verdict.tier)
```

So a bug now takes its **strongest** level instead of its weakest.

**Your question**

- [ ] Plants it  - [ ] Already broken  - [ ] Something else  - [ ] Too broad  - [ ] Can't tell

Hint, if you want one: think about a bug that running the tests settled. What
evidence does it have, and what level does it end up at — before the edit?

Notes:

<details>
<summary>The judge's answer (open after deciding)</summary>

**Something else** — and the bug was **already present**, so there was nothing
to plant. A bug settled by running the tests is never sent for a prediction, so
its only evidence is "observed", and `min` of only "observed" is "observed".
The stronger level already flowed through before the edit.

Switching `min` to `max` only matters for a bug that has *both* kinds of
evidence at once, and the code never produces that. So in practice the edit
changes nothing. (The agent should have made no change here.)

I checked this one against the code myself and agree with the facts above. I
have not checked the judge's other answers.

For comparison, the older one-call builder relabelled every *predicted* piece
of evidence as "observed". The judge called that **something else** too, for
the same reason: the described behaviour was already there.

</details>

---

## Example 4 — whether a failing test may stop the review

**The bug, as described**

- **Should do:** whether a planted-bug edit is valid is decided only by a fixed
  set of mechanical checks on the edit itself (is it in the right place, is it
  small enough, does the file still parse). The settings for running tests
  only decide whether tests run *after* validity is settled.
- **Would do if broken:** the test-running stage can cut the decision short —
  by stopping the review when a test already fails, or by carrying on past such
  failures — so whether an edit is valid depends on how test-running is set up,
  not just on the mechanical checks.

**The code as it was.** Before planting anything, the tool runs the tests once
on the untouched code. If some test **already fails** there, a failing test
later would mean nothing, so by default the review stops. The user can set
`allow_failing_tests` to carry on anyway, with those tests set aside.

```python
failing = [test for test in set_aside if test.kind is TestOutcomeKind.FAILED]
if failing and not allow_failing_tests:
    return Baseline(set_aside=set_aside, halted=True, halt_reason="...")
```

And in the main flow, a halted first run stops the whole review **before any
edit is written or checked**:

```python
baseline = establish_baseline(test_ids, repo, ...,
                              allow_failing_tests=execution.allow_failing_tests)
if baseline.halted:
    raise ReviewHalted(baseline)

descriptors = build_descriptors(...)   # the edits are written here, after
```

**What the agent did**

```diff
-    if failing and not allow_failing_tests:
+    if failing:
```

Now any already-failing test stops the review, and the `allow_failing_tests`
setting is ignored.

**Two questions for you**

1. Does the edit plant the described bug?
   - [ ] Plants it  - [ ] Already broken  - [ ] Something else  - [ ] Too broad  - [ ] Can't tell
2. Read the bug description again. Is it a sensible description of a bug at
   all? Stopping on a failing test happens before any edit exists, so it is not
   obviously about "whether an edit is valid".
   - [ ] Sensible  - [ ] Muddled — no edit could plant it cleanly

Notes:

<details>
<summary>The judge's answer (open after deciding)</summary>

**Something else.** The judge's reasoning: before the edit, the review already
stops on an already-failing test before any edit is written or checked, which
is the "would do if broken" behaviour — so the bug was already present in that
sense. The edit only stops the "carry on anyway" setting from working, and
leaves the mechanical checks on edits exactly as they were.

The judge also noted the description is muddled: halting happens before any
edit exists, so it is not really about edit validity.

For comparison, the older one-call builder added a condition to the
stop-the-review line that the judge showed could never change the outcome — an
edit that changes nothing — and called it **something else**.

</details>

---

## Example 5 — an edit outside the area the bug names

The tool only accepts an edit inside the part of the code the bug description
points to — call it the bug's **named area**. One of the mechanical checks,
the **containment check**, enforces that.

**The bug, as described**

- **Should do:** if a bug names no area that can be edited, the mechanical
  checks reject any edit for it before any tests run.
- **Would do if broken:** a bug with no named area can get past the checks,
  because the containment check only does anything once areas have been found.

**The code as it was** — the containment check. `named` is the list of the
bug's named areas that are in the file being edited.

```python
named = [region for region in regions if region.path == descriptor.path]
if not named:
    return "the defect names no region in this file, so an edit there could not be credited to it"
if not any(region.contains(descriptor.start_line, descriptor.end_line) for region in named):
    return "the span falls outside the region(s) the defect named"
# returning a message = rejected; falling through = accepted
```

And earlier, in the step that calls the checks, before any edit is even
requested:

```python
regions = regions_for(defect, change_set)
if not regions:
    return _not_mutable(defect, "the defect names no changed region ..., so there is no span to replace")
```

**What the agent did** — rewrote the containment check so it only applies when
the file has named areas:

```diff
-    if not named:
-        return "the defect names no region in this file, ..."
-    if not any(region.contains(...) for region in named):
+    if named and not any(
+        region.contains(descriptor.start_line, descriptor.end_line) for region in named
+    ):
```

So on its own, the containment check no longer rejects an edit to a file the
bug never named.

**Your question**

- [ ] Plants it  - [ ] Already broken  - [ ] Something else  - [ ] Too broad  - [ ] Can't tell

Things worth weighing: the containment check itself is now weaker. But look at
the second code block: does a bug with no named area ever reach the containment
check in the real tool? Should the verdict be about the check on its own, or
about what the whole tool does?

Notes:

<details>
<summary>The judge's answer (open after deciding)</summary>

**Plants it** — but the judge listed this as one of its least certain labels.

Its reasoning: called directly, the containment check now accepts an edit for a
bug with no named area, which is the described bug. But it also noted that in
the real tool such a bug is stopped earlier (the second code block), and an
edit to an unnamed file fails a different check first. So through the whole
tool, nothing visible changes.

I think its own reasoning argues against its label. For comparison, the older
one-call builder deleted that earlier stop (the second code block), and the
judge called *that* **something else** — precisely because another check still
caught the bug further on. The two calls are hard to square, and this is the
example where your verdict matters most.

</details>

---

## Example 6 — which stage runs first (agent made no change)

The tool has two ways of judging the tests: **running** them against broken
copies, and a model **reading** the code and predicting. The feature being
built here deliberately runs the tests **first**, and only asks the model to
read the code for the bugs that running could not settle — reading is the
expensive part.

**The bug, as described**

- **Should do:** the test-running stage goes first; the code-reading judgement
  runs afterwards, only on what running could not settle.
- **Would do if broken:** the code-reading judgement runs before the
  test-running stage, making it the first pass instead of the follow-up.

**The code as it was** — the two stages in the main flow, in this order:

```python
# 1. run the tests against broken copies
attempts, executed_verdicts, set_aside_tests = _run_execution_tier(
    defect_sets, discovered.tests, change_set, repo, client, unusable, execution
)

# 2. then ask the model to read the code -- only for bugs step 1 could not settle
pair_mapping = judge_pairs(
    remaining_defect_sets(attempts, defect_sets),
    discovered.tests,
    change_set,
    client,
    ...
)
verdicts = executed_verdicts + pair_mapping.verdicts
```

Note that step 2 uses `attempts`, the output of step 1, to decide which bugs to
ask about. So step 2 cannot simply be moved above step 1 without also changing
what it is given. The tool only accepts a single edit of at most 12 lines.

**What the agent did:** made no change.

**Your question:** was making no change the right call? (The agent was told to
make no change if no single small edit can plant the bug.)

- [ ] Yes — no single small edit plants it honestly
- [ ] No — a small edit could have planted it
- [ ] Can't tell

Notes:

<details>
<summary>The judge's answer (open after deciding)</summary>

**Wrong call: it could have been planted** — though the judge flagged this as
arguable. A faithful reordering needs about 23 lines, over the 12-line limit.
But inserting an extra copy of the step-2 call **above** step 1, whose result
is simply thrown away, is one small edit that makes a code-reading pass run
first.

Whether a throwaway duplicate counts as "the code-reading judgement runs
first" is the open question. If you think it doesn't, the agent was right.

For comparison, the older one-call builder replaced step 1 with empty results,
switching test-running off entirely. The judge called that **too broad**.

</details>

---

## When you are done

Tell me your answers, or tick the boxes in this file and tell me it is done. I
will record them beside the judge's labels and recompute the agent's result
using your verdicts where they differ. Your answers to the extra questions in
Examples 1 and 4 also matter: if `and False` should not count, or if some bug
descriptions are too muddled to plant, the way the audit scores edits needs to
change, not just these six labels.

---

## Human verdicts (recorded 2026-10-13)

Given by the project owner over 2026-10-07 to 2026-10-13, in conversation.

| Example | Judge said | Human verdict | Agree? |
|---|---|---|---|
| 1 empty explanation | plants it | **plants it**, but `and False` is not a plausible slip | yes |
| 2 no usable tests (no change) | right: already broken | **right to make no change**; the "should do" is itself nonsense, since with no usable tests there is nothing to run | yes, for a different reason |
| 3 weak evidence stays weak | something else; already broken | **out of the count.** The bug was written against a requirement that lost its condition when it was split out ("where nothing can be run"), so it contradicts another requirement and cannot be tested | no |
| 4 failing test stops review | something else | **out of the count.** The description confuses "can the tests be trusted" with "is the edit valid" | no |
| 5 edit outside named area | plants it | **something else.** Two separate checks reject the case; planting needs both changed, which is small but not one block. Right to make no change under the one-block rule | **no** |
| 6 which stage runs first (no change) | wrong: could be planted | **agree, could be planted**: run step 2 first on the full list. Also: the older builder's edit is "something else", not "too broad" | yes |

**Effect on the agent's result.** Of the judge's 6 "plants it" verdicts, one
(example 5) is overturned: **5 planted**, not 6. Examples 3 and 4 are bad bug
descriptions and should not count for or against either builder.

**What the owner raised about the audit itself**, recorded as follow-ups
rather than resolved here:

- Requiring a planted bug to look like a plausible slip is a separate burden
  from the real question (do the tests catch the behaviour) and may be causing
  bad edits. What matters is that the edit produces exactly the described
  behaviour and nothing broader.
- A too-broad edit still matters even when the bug is present, because each
  failing test is credited with catching that specific bug.
- Duplicated checks are not always wrong, and the tool should be able to plant
  through them: a few separate small changes should be allowed, within the same
  size limit.
- Some requirements, such as which of two steps runs first, are better settled
  by reading the code than by planting bugs and running tests.
- Several of these 21 bugs are subtle, muddled, or about supporting
  requirements rather than core behaviour. The planted-bug approach was decent on
  the clear-cut cases. Being good at easy and moderate cases first is an
  acceptable outcome.
- Benchmarking should move to an ordinary business codebase, ideally in
  finance, rather than this tool's own history. Bugs should be classified by
  testing priority, by difficulty, and as bad descriptions, so targets can
  differ by class.
