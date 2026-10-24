# Task

Every bullet under a task file's `## Scope exclusions` heading becomes an
obligation saying the change does not do the excluded work. That holds when the
bullet ends with a clause explaining the exclusion, such as "Model calls issued
by the measurement harness, which is not part of a review run." Today a bullet
like that sometimes becomes an obligation describing the excluded work as
something the change must do, and the review then reports it as not addressed.

An obligation that comes from a scope exclusion requires code evidence only,
never a test. Within one review, two such obligations whose code evidence is the
same get the same coverage status.

A regression case in the decomposition prompt tests covers a scope-exclusion
bullet that ends with an explanatory clause.

## Scope exclusions
- Which evidence obligations from the other sections of a task file require.
- Which model each stage calls.
