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
