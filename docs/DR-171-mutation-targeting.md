# DR-171 — turning a named plausible defect into a mutation at exact lines

**Issue:** #171 (the open decision on how a named plausible defect becomes an
actual mutation at actual lines), owned by M8.4 / #45 (targeted mutation, the
`defect-killed` evidence tier).
**Resolved:** 2026-09-02, in conversation, before the M8 sequence starts.
**Revised:** 2026-09-14, in conversation, before #45 starts. Decisions 4, 6, 7
and 8 changed; see *Revision* below.
**Revised again:** 2026-09-16, during #45, on measurement. Decisions 1 and 3
changed; see *Revision — 2026-09-16* below, and its later addendum on the tier
gate, the breadth check and the verifier measurement.
**Status:** resolved.

## Addendum to the 2026-09-16 revision: the tier is gated on a verified edit

Measured on the same review (audits v6 and v7 and their judgements, and
`verifier-measurement-gpt-5.4.md`).

**Decisions 7 and 8 are amended: an observed result is not a settled one.** An
injection result is evidence about a defect only if the edit made that defect
true, and on audit v6 about half did not. A kill or survival is now *observed*;
it *settles* its defect — produces verdicts, reaches `DEFECT_KILLED`, and leaves
the static judge's input — only when its edit is **verified**. An unverified one
is kept and reported, stays `STATIC`, and its defect goes to the static judge. A
bad edit costs compute rather than a wrong tier.

**Decision 3 stands: no confirming model call is adopted.** A verifier was built
(`mutation/verification.py`: shown the defect's two behaviours and 30 lines of
code either side of the edit, before and after, never the tests) and measured on
`openai/gpt-5.4` against audit v6's 66 hand-labelled edits:

| | count | rate |
|---|---|---|
| bad edits it refused (catch rate) | 27 of 35 | 77% |
| good edits it refused (false alarms) | 8 of 31 | 26% |

About a quarter of what it would verify is still a bad edit, so it is **not
adopted**; it sits behind `ExecutionSettings.verify_edits`, off. Five of its eight
false alarms answered "cannot tell" on the 30-line window (first recorded here as
six, a miscount corrected on re-reading the per-edit results), and most bad edits it
accepted do change the named behaviour literally while also crashing. **With it
off, nothing reaches `DEFECT_KILLED` and injection saves no pair judgement.** The
tier and the saving now both wait on a verifier good enough to adopt.

**The edit-building answer states what the code does first.** A required
`code_currently_does` field — expected, defective, cannot tell — is read
mechanically and decides what the edit means. "Defective" is recorded as
`already_present` at the static tier, flagged in the report as model-asserted,
and its edit is run as a repair: every candidate test passing says no test pins
the expected behaviour; a test failing names a test that asserts the defective
behaviour. This replaces the `already_present` typed decline.

**A seventh mechanical check: breadth.** A result is refused when more than 7.5%
of candidate tests fail under the edit and more than 10 do, whatever exception
they failed on. On audits v5 and v6 (339 candidate tests) real kills failed at
most 23; the widest edits that broke far more failed 79, 29 and 26, but most
failed 4 or fewer. 7.5% keeps every real kill and catches only the extremes. The
exception list of check 6 was deliberately not widened: a real injected defect
can fail with a `TypeError`.

**Result, on 22 of the 25 criteria** (three contested ones left out for human
adjudication), v6 recounted on the same criteria against v7:

| | v6 | v7 |
|---|---|---|
| edits counted (kills and survivals) | 58 | 44 |
| put the named defect into the code | 25 (43%) | 25 (57%) |
| repair a defect the code already had | 7 | 3 |
| change something other than the defect | 16 | 12 |
| break far more than the defect | 10 | 4 |
| real kills | 20 of 46 | 23 of 36 |
| real survivals | 5 of 12 | 2 of 8 |

v7 also refused 8 edits after their run, all correctly, and recorded 12
already-present claims, 9 of them right. Edits that change the wrong thing are
the largest remaining problem and nothing adopted addresses them.

## Revision — 2026-09-16: a defect is two behaviours, and validity is more than four checks

Measured over #45's own Gate 2 review — 25 criteria, the diff `61c5a3c..518f876`,
about 70 defects, 339 candidate tests — with every edit judged by hand
(`dogfood-logs/45-injection-audits/`, audits v2 to v6 and their judgements).

**Decision 1 is revised: the enumeration output shape DOES change.** Each defect
now carries `expected_behavior` (what the code must do for the criterion) and
`defective_behavior` (what it would do instead), beside the unchanged
`description` and `code_refs`. A one-sentence defect is usually a present-tense
claim about the code, and the edit-building step could not tell whether to make
it true or whether it already was. When the code already had the defect, it
edited the code to *repair* it, and the tests that failed were counted as
catching the defect: 17 of 60 edits on `openai/gpt-5.4` (audit v5).

With the two fields (audit v6), repairs fell to 9 of 66 and edits that genuinely
inject the named defect rose from 32% to 47%. The grounds Decision 1 gave still
hold for what it rejected — the enumerator is still not asked for an edit, and it
is told not to say which of the two behaviours the code has — so the denominator
is not thinned toward what is mutable. The recording cost it named was paid.

**Decision 3 is amended: validity is six checks, not four.** Two were added on
measurement:

5. **The replacement differs from the text it replaces.** 21 of 71 descriptors
   on `gpt-5.4-mini` returned their input verbatim; each would have been a
   survival recorded against the builder for a defect never introduced.
6. **A kill is not counted when every failed test failed with `NameError`,
   `UnboundLocalError`, `ImportError` or `ModuleNotFoundError`.** The edit parses
   and imports, then fails on a name that does not exist when a test calls it.
   7 of 47 kills on `gpt-5.4` were this. The defect goes to the static judge.

No confirming model call was added. Whether one is needed is **still open**:
16 of 66 edits in audit v6 change something other than the named defect, and 5
of those change nothing at all, which a check on the text cannot see.

**Two measured corrections to *What injection cannot decide* below:**

- **Absence defects are reachable.** All 19 `not_wired` and `missing_case`
  defects named regions. When the code does the right thing, "nothing calls it"
  is injected by deleting the call.
- **A defect already true of the code cannot be injected**, and was not
  anticipated here. The edit-building step answers `already_present` for it
  (a typed decline, with `not_a_code_property` and `not_one_contiguous_edit`),
  which is reported as needing human review and moves no rating.

## Revision — 2026-09-14: injection replaces the static judgement rather than correcting it

The original record treated execution as an upgrade layered on top of the static
per-pair judgement. Decision 7 said injection "overwrites individual verdicts
with better-evidenced ones", which means the model judges all 23,808 pairs and
execution then discards some of its answers. That pays the pair stage's $6.02 in
full and adds the test runs on top.

The point of the execution tier is to remove that cost, not to add to it. This
revision inverts the order: **execution decides first, and the static judge runs
only on the remainder it could not reach.** Nothing about the evidence ladder,
the mutant's construction, or the single-record design changes — Decisions 1, 2,
3 and 5 stand as written.

Three things follow, and they are Decisions 4, 6 and 7 below:

- **Coverage stops being the selector.** The mutant runs against every candidate
  test. Coverage was measured to miss 43 of 268 recorded kills, and under the
  original design those became reported findings rather than wasted money.
- **The candidate tests must be green at head before injection is worth doing**,
  by default, with an override.
- **`judge_pairs` becomes the fallback stage, not the default one.**

**§8.2 was amended in the same conversation** to match, because its "runs *only
the handful of mapped tests*" assumed a cheap prior mapping from tests to
criteria. #312 and #316 deleted that mapping; the per-pair judgement replaced it,
and its cost is the thing execution exists to avoid. Narrowing the test set with
it would forfeit the whole saving.

## What was open

The defect enumeration stage (`defects/enumeration.py`, DR-312's defect-first
shape) produces a named plausible defect as prose plus a list of `path#hunk`
labels. M8.4 has to turn that sentence into a real code edit at real lines, run
tests, and read red or green as discriminates or proven-weak. #171 left five
things unsettled: where the mutation descriptor is produced, how the sentence
resolves to an exact span, whether the vocabulary is a fixed operator set or
free-form, what makes a mutant valid, and what happens when no valid mutant can
be built.

It was filed as a decision that must land before M8 starts, because the answer
might have required the enumeration stage's output shape to change — an
already-shipped stage whose recordings a schema change would orphan.

**It does not.** That is the first decision below, and it is the reason this
record could be written without touching any code.

## Decision 1 — the mutation descriptor is produced at M8.4, and the enumeration output shape does not change

The enumeration stage keeps emitting prose plus `code_refs`. A separate stage,
inside M8.4, reads one `Defect` and the source at head and produces the
descriptor. The alternative — having the enumerator commit to something
executable at the moment it names the defect — is rejected on four grounds, the
first of which is the important one.

**It would thin the denominator toward what is mutable.** The enumerator is
deliberately blind to the tests, because a denominator chosen by something that
can see what is already covered drifts toward it, and a thinner enumeration then
earns a stronger rating. That is #252, and the mitigation is DR-312 decision 2.
Requiring the same call to also produce a working patch reintroduces the same
drift from a different direction: the stage would favour defects it can express
as an edit. The measured shape of what is hard to express — documentation
defects, defects in non-Python files, defects about absent behaviour — is
recorded in §"What injection cannot decide" below, and those are precisely the
ones that would go missing. A recall stage must not be scored on executability.

**The obligation set is not final when enumeration runs, and enumeration is not
the last thing that can add to it.** I verified this in
`pipeline.py::run_review`: `resolve_open_questions` runs, `derive_obligations`
turns the resolutions into further obligations, those are appended to the set,
and only then does `enumerate_defects` run over the combined set. Any mutation
work done earlier than the defect it belongs to would have to be redone for the
derived obligations anyway.

**Cost.** Enumeration runs on every review; mutation runs only where the
feasibility probe passes (§8.3, and #170, the open decision on what signals
declare a suite hermetic and fast enough). At #316's Gate 2 scale — 48 defects —
a call per defect is small beside the 992 calls the pair stage already spends.
Folding it into enumeration charges every review on every repository for
something most of them will never use.

**Recording cost.** CLAUDE.md records that changing a stage's response schema
invalidates that stage's recorded transcripts. Adding a field to the enumeration
response orphans every enumeration recording in the corpus. Adding a new stage
orphans nothing.

## Decision 2 — the descriptor is one contiguous span replacement, inside the defect's own region

Three fields: a file path, a line span at head, and the replacement text. The
stage is asked for the smallest edit that makes the named defect true.

**Rejected: a fixed operator vocabulary** (constant replacement, boundary flip,
branch removal, return-value substitution). It is cheaper to verify, but the
taxonomy has 21 defect types plus `other` (DR-313, the defect taxonomy), and
`not_wired`, `error_swallowed` and `explanation_states_wrong_cause` each need
their own operator. A menu long enough to cover the taxonomy is not meaningfully
more constrained than free text, and it fails closed on `other` by construction.

**Rejected: a free-form diff.** It can fail to apply, which adds a failure mode
that span replacement does not have.

A span replacement expresses everything an operator set expresses and applies by
construction. The cost is that the vocabulary is unconstrained, so validity has
to be checked rather than guaranteed — Decision 3.

**Left open deliberately:** whether to revisit a canonical operator form later,
with an escape for cases it cannot express, if measurement shows the free-form
call is slow, expensive or unreliable. Nothing in this record forecloses that;
the descriptor's three fields are the same either way, and only what produces the
replacement text would change.

## Decision 3 — validity is four mechanical checks and no confirming model call

A mutant is valid when all four hold:

1. **It applies** — true by construction for a span replacement.
2. **The mutated file parses, when the file has a parser** — `ast.parse` on the
   result for a Python file. This is the compile check, and in Python it is free.
   **Revised 2026-09-14: a file with no parser is not thereby invalid.** See
   *Non-Python files* below.
3. **The span lies inside a region one of that defect's `code_refs` names.**
   This is what stops a mutant wandering into unrelated code, which is #171's
   third validity concern.
4. **The edit is bounded in size**, by a recorded line count.

### Non-Python files (added 2026-09-14)

The original check 2 failed closed on any file `ast.parse` could not read, which
silently made every documentation defect unmutable. That was never argued for; it
fell out of writing the check in terms of Python.

**A span replacement is text, and mutating a Markdown file works.** It is also
the only way to reach a measured class of real defects: the coverage-prefilter
experiment found tests asserting on README and decision-record text that kill
documentation defects, and one of the nine defects with no usable region at
#316's scale named a non-Python file outright. Injecting into the Markdown and
running the candidate tests is exactly how those tests prove themselves — the
test reads the mutated file and goes red.

For a file with no parser, checks 1, 3 and 4 carry validity on their own. Check 3
does the load-bearing work: the span must lie inside a region the defect's own
`code_refs` names, so the mutant cannot wander into an unrelated file, and a
defect whose `code_refs` name no region is `not_mutable` for that reason rather
than for its file type.

**What this does not license.** Mutating a file that is neither code nor an
artifact a test reads — lockfiles, generated output, binary assets — is pointless
rather than unsafe, and the bounded-size check plus the `code_refs` containment
check already keep it rare. If it turns out to matter, an allowed-extension list
is the cheap remedy; it is not added pre-emptively.

**Rejected: a second model call to confirm the mutant really violates the
obligation.** It would be judging its own output, it costs a call per defect,
and it produces a claim at the same tier as the thing it is checking. Instead the
mutant text is recorded in review state so that a person reading the finding can
see exactly what was injected and disagree with it. That is weaker than a proof
and is honest about being weaker.

## Decision 4 (revised 2026-09-14) — the mutant runs against every candidate test, and injection is what maps tests to criteria

**Superseded:** the original Decision 4 made coverage the selector — run only the
tests that execute the defect's lines, and settle a defect no test covers at
`COVERAGE_CONFIRMED` (§8.1 tier 3) without injecting. Both halves are withdrawn.

**What replaces it.** Inject the mutant and run every candidate test against it.
The tests that go red are the tests that discriminate for that defect, and that
result *is* the mapping — there is nothing to select with beforehand that does not
cost more than it saves.

- **Some test goes red.** The defect is killed and those tests discriminate.
- **No test goes red.** The defect survives, and every candidate test is proven
  not to discriminate for it.

Both are `DEFECT_KILLED` (tier 4), because both were observed rather than
predicted.

**Why coverage cannot be the selector.** It was measured wrong often enough to
matter. Over #316's Gate 2 review, coverage reachability excluded 43 of 268
recorded kills — tests that genuinely detect the defect while never executing the
implicated lines. Three channels hide in that: tests asserting on README and
decision-record text, which detect a documentation defect through a file read;
absence defects (`not_wired`, `documented_not_implemented`, `missing_case`),
where the named lines are where behavior *should* be and a test fails on its
absence through code elsewhere; and coverage that simply does not see the
execution, as when the code under test runs in a subprocess.

Under the original Decision 4 each of those became a **reported finding** —
"no test covers this defect" — not merely a wasted opportunity. That is the
failure mode #312 (the defect-first restructure) exists to remove, arrived at
from the other side.

**Coverage survives as an optional narrowing, never as a verdict.** On a suite too
slow to run whole against every mutant, coverage may cut the test set, and the
measured lever is 2.6x, not 10x: the median filtered defect is still reachable by
137 of 496 tests, because a pipeline-level suite executes most of the changed code
on most tests. When it is used, what it excludes is recorded as **undecided and
handed to the static judge** (Decision 7), never recorded as uncovered. This is
narrower than the contract `defects/support.py` gives an
`UnjudgedCause.PREFILTERED` pair, which it treats as a survival established
statically; coverage has not earned that contract and the 43 lost kills are why.

**Cost, measured.** At the suite's observed 0.2 seconds per test, 48 defects
against 496 candidate tests is about 23,800 test executions, on the order of 79
CPU-minutes and zero tokens, against $6.02 of static pair judging per review. It
parallelises across cores; the static judging does not parallelise past the
provider's rate limit.

**Rejected: forcing the code down the path, or substituting a test double so the
defect can be triggered.** Three reasons.

It answers a question nobody asked. The review's question is whether the tests
*the builder wrote* discriminate. "Would a test that drove this arm have caught
it?" is a different question, and its answer is almost always yes, so it carries
no information.

It is the tool doing the thing it is supposed to be prescribing. Constructing a
fixture that drives an arbitrary path is test authoring. M8.4's output when a
defect is uncovered is a recommendation that such a test be written; writing it
in order to then report that it passes is circular in the way §13.5 scenario 5
(circular expected result) exists to catch.

It breaks Decision 3's third check by definition. A double changes something
outside the defect's own region, so a red result no longer says the mapped test
would catch this defect in the delivered code — it says the test noticed that we
swapped a dependency.

**A limit that the revision removes, and one it does not.** Line-level coverage
is too coarse for a defect on an unexercised *branch* of a line that does execute
— a configuration threshold the tests never cross. Under the original decision
that defect was decided wrongly, because the mutated line looked reached when the
relevant branch was not. Running every candidate test removes the problem
entirely: the tests either go red or they do not, and no reachability claim is
made. If coverage is later enabled as the optional narrowing above, M8.3 (#44,
the coverage-confirmed tier) should record whether branch coverage is on, and
whether subprocess coverage is configured, since both bound what the narrowing
may safely exclude.

## Decision 5 — the ambiguous outcome is a surviving mutant on executed lines, and it stays a finding

#171's comment names the "no test failed" result as ambiguous between blind
tests and an injected edit that changed no behaviour.

**Amended 2026-09-14.** The original Decision 4 removed the first half by
splitting blind tests off one rung down, before injecting. The revised Decision 4
does not split them off, so they land here instead — and that turns out to be the
better place for them. Whether the suite fails to catch a defect because no test
executes the code or because the tests that do execute it assert nothing useful,
the finding delivered to the builder is the same: **no test you wrote catches
this defect.** The two causes differ in the remedy, not in the verdict, and the
remedy is a test recommendation either way.

What is genuinely ambiguous is narrower: a survival may also be a mutation that
changed no behaviour at all. Nothing mechanical separates a behaviour-preserving
mutant from a weak test, which is why the mutant text is recorded.

It is recorded as a survival and reported as one, at `DEFECT_KILLED` tier, with
the mutant text attached. Two reasons for taking the risk in that direction. The
survival is the direction that produces a finding against the builder, and an
unsound survival recreates the failure #312 exists to remove — recommending a
test that already exists (#250, #287). But suppressing survivals would inflate
the rating, which is the failure #252 exists to remove, and inflation is silent
where a wrong recommendation is visible and arguable. Recording the mutant text
is what makes it arguable.

## Decision 6 (revised 2026-09-14) — one baseline run of the candidate tests at head, and a red one halts the review by default

**Still required, and for the original reason.** A test already failing at head
tells you nothing when it fails under mutation, so the control must be
established before anything is injected. The run also feeds #170's feasibility
probe. What it no longer has to produce is the coverage map, since the revised
Decision 4 does not select with one; coverage instrumentation becomes optional on
this run rather than the point of it.

**The run covers the candidate tests, not the suite.** This was already DR-170
Decision 4's reading of §1 principle 6 and §17 ("CI owns full-suite execution",
"targeted subsets only, never full suite"), and the revision does not disturb it.
At #316's Gate 2 the candidate set was 496 tests of about 1,311; the
coverage-prefilter experiment's 5m15s figure covered all 1,623 and is an upper
bound, not an estimate.

**New: a red candidate test halts the review by default, with an override.** If
any candidate test fails at head, the review stops and says so, rather than
falling back to static judging.

The reasoning is cost, not policing. Falling back does not save money — it spends
*more*, because the static pair stage is the expensive half ($6.02 at #316's
scale) and the execution tier exists to avoid it. Spending that on a change whose
own tests are failing buys a review whose conclusions rest on tests that do not
pass. Halting is the cheap honest answer.

**The override exists because a deferred failure is a real situation.** A known
hard-to-fix test the builder has consciously parked should not make the tool
unusable. With the override set, the review proceeds, failing tests are excluded
from the verdict with a recorded reason, and the exclusion is reported.

**This is still not the product grading the user's green suite**, which §8.2's
scope boundary rules out. Three things keep the distinction real: no finding is
ever produced *about* a failing test beyond the fact that it was excluded or that
the review halted; only candidate tests are consulted, never the suite, so the
product never forms a view on whether the project as a whole passes; and the halt
is a refusal to spend, not a verdict on the change.

**It is also not §8.3's graceful degradation, and must not be folded into it.**
§8.3 covers a suite that *cannot* be run — cloud dependencies, UI-bound behavior,
live-service tests, excessive runtime — and its answer is to degrade silently to
static inference with a lower recorded tier. A suite that runs and fails is a
different case, not in that list, and it is the one case where continuing costs
more than stopping. Conflating them would make every red suite silently expensive.

## Decision 7 (revised 2026-09-14) — one `PairVerdict` record carrying a tier, and the static judge runs on the remainder rather than first

**Superseded:** the original wording was "Injection does not replace the static
pair judgement. It overwrites individual verdicts with better-evidenced ones."
Read literally that judges all 23,808 pairs by model and then discards the
answers execution supersedes — paying the full $6.02 *and* the test runs. The
single-record design below was the point of the decision; the ordering was an
unexamined side effect of it.

**What replaces it: execution decides first, and `judge_pairs` runs on what is
left.** Concretely, in `src/acceptance/pipeline.py::run_review`, `judge_pairs`
currently runs unconditionally over every test-and-defect pair. It moves after
the mutation stage and receives only the remainder:

- defects for which no valid mutant could be built (Decision 3);
- the absence classes (`not_wired`, `documented_not_implemented`,
  `missing_case`), where there is no span to replace because the defect is that
  the code is not there;
- every pair, when the feasibility probe declines or the candidate tests are red
  and the override is set;
- pairs excluded by the optional coverage narrowing, if it is enabled
  (Decision 4).

**Why the single-record design is untouched by this.** A parallel record type for
executed verdicts would fork the rating logic and the two copies would drift —
the failure `CLAUDE.md` records against the CLI and the benchmark, which had
drifted onto different pipelines before a test pinned them together. One record
with a tier field keeps one rating implementation whichever stage produced the
verdict, and that argument does not depend on which stage runs first.

**The degradation story is unchanged and still structural.** A repository where
the probe declines everything is the case where the remainder is every pair, and
every `PairVerdict` stays at `STATIC`. That is today's behaviour exactly, reached
with no special case — which is what §8.3 asks for.

`PairVerdict` gains a tier field. A verdict the pair-judgement stage produces is
`STATIC`; one the mutation runner produces is `DEFECT_KILLED`.
`evidence_tier.py::authorize_tier` already enforces which component may produce
which tier, and `Component.MUTATION_RUNNER` is already the only one authorized
for `DEFECT_KILLED`, so nothing new is needed there.

I verified at the time this record was written that
`defects/support.py::derive_support` computes the rating by collecting defects
with at least one killing verdict and comparing that count to the enumerated
count, with no reference to a tier. That arithmetic is unchanged by the original
decision and by the revision alike.

`defects/support.py` currently hardcodes `EvidenceTier.STATIC` as the achieved
tier for every criterion. It becomes the weakest tier among the verdicts the
criterion's rating actually rests on. A review is therefore a mixture of verdicts
at different tiers, in the same way that running enumeration before test
discovery makes its test-blindness structural rather than promised.

## Decision 8 (revised 2026-09-14) — every attempt is recorded with a typed outcome

Following `UnjudgedPair` and `UnjudgedCause`, which record pairs that got no
verdict rather than dropping them, because a pair nothing can see is
indistinguishable from a verdict of *survives*. Mutation needs the same:

| outcome | meaning | tier reached |
|---|---|---|
| `killed` | some candidate test went red under the mutant | `DEFECT_KILLED` |
| `survived` | every candidate test ran under the mutant and none went red | `DEFECT_KILLED` |
| `not_mutable` | no valid mutant could be constructed (Decision 3) | `STATIC` |
| `not_attempted` | the probe declined, the candidate tests were red, or the defect is in a class injection cannot express | `STATIC` |

`not_mutable` and `not_attempted` must carry a reason, for the same reason
`DefectSet` requires one on an empty set: "looked and could not" and "did not
look" are different, and only one of them is a defect in the tool.

**`unreached` is withdrawn.** The original table gave it to a defect no candidate
test executes, reaching `COVERAGE_CONFIRMED`. The revised Decision 4 does not ask
that question, so the outcome has nothing to report: a defect no test executes
now simply survives, along with every other defect the candidate tests fail to
catch. If the optional coverage narrowing is enabled, the pairs it excludes are
recorded as unjudged and routed to the static judge (Decision 7) rather than
given an outcome of their own.

**Both `STATIC` outcomes are routing instructions, not conclusions.** A defect
marked `not_mutable` or `not_attempted` has not been decided; it is handed to
`judge_pairs`, and the verdict that comes back is what the rating uses.

## What injection cannot decide, measured

The premise that injection eventually supersedes the static pair judgement — the
argument in #171's comment, that one injection plus one suite run answers for
every test at once, so the static stage's cost per pair cannot be defended
against a runnable suite — holds for the pairs injection can reach. It does not
reach all of them, and the shape of the remainder is measured rather than
assumed. From `docs/experiments/coverage-prefilter/FINDINGS.md`, over #316's
Gate 2 review at head `3e1d3a9` — 48 defects, 496 tests, 23,808 pairs, 268
recorded kills:

- **Nine of the 48 defects had no usable code region at all**: seven named
  module-level regions, one named a non-Python file, one named lines that never
  execute.
- **Tests that fail through file reads rather than execution.** Tests asserting
  on README and decision-record text kill documentation defects without
  executing the implicated code. Line coverage cannot see that channel, and
  neither can a line-level mutation.
- **Absence defects.** For `not_wired`, `documented_not_implemented` and
  `missing_case`, the implicated lines are where behaviour *should* be, and a
  test can fail on the absence through code that lives elsewhere.

Those three classes stay on the static judgement, on any repository, whatever the
probe says. They are separate from the repositories where execution is
unavailable, which is §8.3's case and is handled by Decision 7. The division of
labour: injection decides the pairs it can reach, and the static prediction
covers what injection cannot express or cannot run.

**Re-read after the 2026-09-14 revision.** Two of the three bullets above were
written when coverage was the selector, and the revision narrows what they prove.
The measurements stand; the attribution changes.

- The **file-read** bullet no longer describes a limit. Its claim that "line
  coverage cannot see that channel" is beside the point, since nothing consults
  coverage; and Decision 3's revision means the Markdown can be mutated, so the
  tests that read it go red and prove themselves. This class moves out of the
  unreachable set and into injection's reach.
- The **absence** bullet stands unchanged and is the harder class. A span
  replacement cannot express "this code should exist and does not", because there
  is no span to replace.
- The **suspect verdicts** the experiment found — kills the static judge asserted
  through code paths the test never drives — are no longer a limit at all. They
  are the thing injection now settles, and settling them is what the 43
  disagreement pairs in the pilot case list are for.

## Consequences

- **No change to `defects/enumeration.py` or its response schema**, so no
  enumeration recordings are orphaned by this decision.
- **`PairVerdict` gains a tier field** (Decision 7), which is a review-state
  schema change and orphans nothing, since it is additive with a default.
- **A new record type for mutation attempts** (Decision 8), holding the
  descriptor, the mutant text, the outcome and the reason.
- **#45 (M8.4, targeted mutation) no longer depends on #44 (M8.3, the
  coverage-confirmed tier), and the sequencing inverts.** The original record
  made #44 own the coverage map that Decision 4 selected with; the revised
  Decision 4 selects with nothing, so the only thing #45 needs from a prior run
  is the per-test baseline, which it can take itself (Decision 6). #44's coverage
  map becomes an optimization for slow suites and can follow.
- **§8.2 was amended on 2026-09-14** to remove "runs *only the handful of mapped
  tests*" and "not a combinatorial explosion", which assumed the mapping stage
  #312 and #316 deleted. §1 principle 6 and §17 are untouched: the candidate test
  set is a targeted subset, and the full suite is still never run.
- **`judge_pairs` moves in `pipeline.py::run_review`** from running
  unconditionally over every pair to running on the remainder after the mutation
  stage (Decision 7). This is the change that realises the saving; the rest of
  the revision is what makes it safe.
- **#170 (the open decision on what declares a suite hermetic and fast enough)
  is unaffected by this record** and still has to be resolved before #42 (M8.1,
  the feasibility probe) is implemented. Decision 6's green-candidate-tests gate
  is a natural member of that probe's result once #42 exists; until then #45
  carries it.
- **The pilot case list already exists.** The coverage-prefilter experiment
  leaves 43 pairs where coverage and the static judge disagree, plus three from
  `prefilter-committee/`. Adjudicating them by injection measures pair-verdict
  accuracy against ground truth for the first time; #315's human-reviewed labels
  are the only current proxy.
