# Judgement — #261/#239 Gate 1, run 2

The gate run. Task file at the version committed with this log; issues #261
(formatter) and #239 (linter and build actions), taken together as one mandate
because both change the same two files and the churn is paid once.

## Outcome

20 requirements → 19 obligations, one deliberate none. **1:1 apart from the
headline.** No open questions. No unreconciled cluster. No invented obligation,
and no requirement left without one.

| section | requirements | obligations |
|---|---|---|
| headline | 1 | 1 (composite — see below) |
| constraints | 13 | 13 |
| scope exclusions | 5 | 5 |
| completion expectations | 1 | 0, deliberately |

Every constraint obligation is a verbatim or near-verbatim restatement.
`constraint-10` flips "does not discard the lint tool's exit code" to "preserves
the lint tool's exit code" — a faithful negation, not a drift; the truth
conditions are identical.

**Confirmed accurate.** Agent judgement; human confirmation pending.

## Open questions

**None raised.** Nothing to triage under the gate's three cases.

Recorded, not claimed as a result: zero open questions is *observed*, not
*confirmed*. #193 holds that membership oscillates run to run, and a replayed
re-run would reproduce this output by construction. Distinguishing a genuinely
unambiguous task file from a quiet run needs #189's harness with determinism off.

## Findings

### 1. The headline yields a composite that duplicates six constraints — #223 shape

`task-01` produced one obligation carrying both of its clauses:

> The repository's Python sources are formatter-clean and lint-clean, and the
> automated build fails any change that leaves them otherwise.

The first clause restates `constraint-01` and `constraint-02`; the second
restates `constraint-07` through `constraint-10`. Linking merged none of it,
which is correct under the strict sameness test — a composite spanning two
requirements can never have truth conditions identical to either part.

This is the mechanism already filed on #223 (composite obligations spanning two
requirements are structurally unmergeable), reproduced on a task file written for
a different purpose. Mild here: the composite is the headline, so its redundancy
is expected, and it costs one redundant obligation rather than destroying
content. Queued as a further instance on #223 rather than a new filing.

Run 1 split the same headline into two obligations. The task file changed between
the runs, so this is not a controlled instability pair.

### 2. Five identical scope exclusions get three different types — #205, again

| requirement | type |
|---|---|
| `exclusion-01` Which lint rules are selected | `regression` |
| `exclusion-02` Formatting files that are not Python | `regression` |
| `exclusion-03` The behaviour of the review pipeline | `functional` |
| `exclusion-04` Which Python version the build targets | `compatibility` |
| `exclusion-05` Unrelated test-suite failures | `functional` |

Five bare noun phrases in one section, one construct, **three** types. #191's
Gate 1 showed the same failure at two types over six exclusions; this is the
stronger instance, and it breaks the pattern #191 observed — there the type
tracked the description's phrasing exactly, whereas here `exclusion-03` and
`exclusion-05` share the "does not alter" form with `exclusion-01`/`02` and are
typed differently anyway. So the type is not a clean function of the phrasing
either; it is unstable.

Queued as an addition to the #205 comment already drafted from #191.

### 3. `exclusion-05` restates a scope exclusion as a behavioural claim

Requirement: *Failures in the test suite that are unrelated to formatting or
linting.* Derived: *The change does not alter **how failures in the test suite
unrelated to formatting or linting are handled**.*

The requirement excludes those failures from the mandate's scope. The obligation
asserts something about how they are *handled*, which the mandate never
discusses and which nothing in the change touches. Mild — the two happen to be
satisfied by the same empty diff — but it is the exclusion being read as a
feature rather than as a boundary. Not queued separately; noted as context for
#205's typing work, since the same section produced finding 2.

## Structural note for Gate 2 — recorded before the fact

This mandate's deliverable is a reformat, a lint pass, `pyproject.toml` and
`ci.yml`. **None of its 19 obligations can be supported by a pytest**, by the
human's own direction on run 1: tests exercise the code's behavior and must not
be aware of the linter or the build. The one exception is `constraint-04`/`05`,
the `tests/test_partition.py` change, which is itself a test.

So Gate 2's requirement that every obligation be *strongly supported by test
evidence* is unreachable here for reasons that have nothing to do with the
quality of the work. Recorded now, before the check runs, so that the Gate 2
result is not read as a defect in the delivery — and so the alternative reading,
that the tool has no evidence path for a configuration-only change, is on the
record as the thing to judge at that gate rather than discovered there.
