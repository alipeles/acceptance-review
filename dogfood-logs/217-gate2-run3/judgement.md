# Judgement — #217 Gate 2 run 3

`6ae97fd` → `6c06517`. **Not clean.** INCOMPLETE: 5 obligations with
non-discriminating test evidence, down from 11 (run 1) and 7 (run 2). No
obligation unaddressed; no `separable` unrequested change; mandate coverage
unchanged and correct.

Remaining, and **not yet dispositioned** — this is where the session stopped:

| obligation | shape |
|---|---|
| `obligation-schema-test-rejects-empty-yielded` | meta: "a test asserts X" |
| `obligation-union-id-test-covers-members` | meta: "a test asserts X" |
| `obligation-unambiguous-literal-discriminators` | has a direct, on-point test |
| `obligation-disposition-union-payloads` | has direct tests |
| `obligation-pydantic-typed-schemas` | generic; repo-wide convention |

Two are **meta-obligations** — the task file asks that *a test exist*, and the
evidence stage is being asked to find a test proving a test exists. That is a
task-file authoring problem more than a tool defect: the completion expectation
should state the behaviour to be guaranteed, not the artifact.

The other three carry tests written specifically for them
(`test_the_literal_tag_alone_decides_which_shape_a_disposition_is` was added in
run 2's response and the obligation still reads non-discriminating). Whether
that is an evidence-judgement defect (#183) or a mapping defect (#182) is
**not yet established** and must not be assumed — a clean verdict is only as
good as the mapping behind it (DR-164).

Recommendation 2 of this run is a legitimate sharpening rather than noise: it
asks for union members carrying *misleading* fields, which `extra="forbid"`
turns into the strongest available proof that dispatch is by tag alone. Not yet
written.

**Nothing here is waved off. No PR until each of the five is either fixed or
attributed to a filed defect.**


## Re-check of all five recommendations (added later)

Each was checked against the actual tests rather than judged from its `detects:`
line. Four of five held.

| # | obligation | outcome |
|---|---|---|
| 3 | `disposition-union-payloads` | **Real gap.** Both its recommendation and #4's asked for MIXED payloads — a `yielded` entry also carrying `reason`. Addressed in `865f6e9`. |
| 4 | `unambiguous-literal-discriminators` | Same gap, same test. |
| 17 | `pydantic-typed-schemas` | **#148.** See correction below. |
| 21 | `schema-test-rejects-empty-yielded` | **#148 category 2.** `test_the_schema_cannot_express_a_yielded_disposition_with_no_obligations` exists and does exactly what the recommendation asks. Nothing can be mapped to "a test asserts X". |
| 22 | `union-id-test-covers-members` | **#148 category 2.** Same shape; it drew 6 mapped tests including the correct one, where 21 drew none. |

### Correction on obligation 17

It was reported to the human as a **mapping miss (#182)**, on the grounds that
`test_a_union_of_item_shapes_constrains_every_member` does what recommendation 3
describes. That was wrong.

The test matches the recommendation's *prescription* — a synthetic pydantic model
with a union-of-models field, run through the constraining and inlining path —
but it would pass whether or not the production schemas are pydantic. It cannot
discriminate the obligation, so the mapper had nothing on-point to miss.

Obligation 17 is #148 category 1, as the #148 comment filed from this same run
already said. The two accounts were inconsistent and this is the correct one.

**The error shape is worth keeping**: naming a test that resembles the
recommendation, without checking that the test would fail if the obligation were
violated. The same shape produced the wrong dismissal recorded above for #218's
`closing-line-points-at-retrieval-command`.
