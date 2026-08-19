# Judgement — #258 Gate 2, run 6 — the last of the sequence

**INCOMPLETE.** Nine obligations strongly supported, four partially, one
unsupported, six needing no test evidence. Five prescriptions remain.

Base `a4abbf4` → head `8904b4c`. Live calls.

## The sequence

| run | head | strongly supported | weak | prescriptions |
|---|---|---|---|---|
| 3 | `a752f82` | 1 | 13 | 13 (one NOT OBTAINED) |
| 4 | `5399afd` | 0 | 14 | 14 |
| 5 | `43c3646` | 8 | 6 | 6 |
| 6 | `8904b4c` | **9** | 5 | 5 |

Two obligations closed this run — both root-task-file-read obligations reached
`strongly supported`, which is the pair the whole issue is about.

## Why this is where it stops

Two obligations **regressed under tests written to close them**:

```
  moved:
    - The region-coverage case list is built only from the committed task files …
        test evidence: strongly supported -> partially supported
    - The region-coverage case list omits a path that is not present in the tree.
        test evidence: partially supported -> unsupported
```

Obligation 12 went to `unsupported` — *no mapped test* — while
`test_an_entry_whose_target_is_missing_is_omitted` sits unchanged in the tree,
was cited as its evidence in run 5, and is the test its own run-5 prescription
described. Nothing in the commit touched it. Obligation 10 fell from strong on
the same diff.

And the five remaining prescriptions are one class:

| obligation | defect it names | does that defect violate the obligation? |
|---|---|---|
| 2, non-empty-test | *"only contains a filtered subset but still at least one item"* | no — still non-empty |
| 3, stays-within | *"includes only dogfood-logs paths but also duplicates one"* | no — all still under `dogfood-logs/`, and the ordered-list assertion added in `8e1b939` already catches duplication |
| 10, case-list-source | *"also includes a synthetic in-memory case not backed by a file"* | no |
| 11, nonempty | *"contains only one case when several should exist"* | no — still non-empty |
| 12, omits-missing-path | *"excludes at least one path that is absent from the tree"* | **that is the obligation's own text**, stated as the defect to catch |

Obligation 12's is the sharpest thing this sequence produced: the tool prescribes
a test to catch the criterion **being satisfied**. No test can be written against
that, because there is nothing to detect.

Three rounds of writing tests moved the count from 13 weak to 5. The five that
remain cannot be closed by writing tests, and two of them moved *away* from
closed when tests were written. Continuing is not a matter of effort.

## What the sequence produced that is worth keeping

Ten tests, all discriminating by injection, none of which existed before run 3:

- reintroducing the root file into the region-coverage case list fails the
  collection comparison;
- making the parse test read the root file again fails the absent-file run;
- an **indirect** read through a helper — no literal pattern anywhere, invisible
  to the source scan — fails both the outcome comparison and the directory
  probe;
- widening the guard's exclusion past `tests/fixtures` fails the exclusion
  assertion while the two files named in the test are still present.

The guard also caught the new module's own docstring naming the banned shape,
which is the third time this sequence that a test caught its author.

## Disposition

**Gate 2 fails, for the fourth assessable time, and this is the residue.** #258
stays unmerged pending a human call. The delivery is materially stronger than it
was at run 3 and its Acceptance is now asserted rather than argued; what stands
between it and a clean gate is five prescriptions that name defects their own
obligations would survive.
