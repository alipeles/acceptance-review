# Task

The review refuses an edit that differs from the text it replaced only in
comments or whitespace. It refuses it always, not only when the review is also
checking whether an edit really makes its named defect true.

The refusal is recorded as one of the review's own mechanical checks, not as a
judgement about what the edit does, so that counts of what each judgement refused
are not inflated by edits no judgement was asked about.

## Constraints
- The refusal is reached without asking a model.

## Scope exclusions
- The questions the review asks about an edit's behaviour, and whether they run
  at all.
- Building an edit, or choosing the region of the code it falls in.
- Running the project's tests.
