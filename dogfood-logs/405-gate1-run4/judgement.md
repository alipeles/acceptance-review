# #405 Gate 1, run 4 — judgement

Run `09cb6b6fd9b02ac6`, continuing run 3. 9 requirements, 0 open questions.
The task file gained one paragraph (owner's request, 2026-10-23): parallel test
runs as a user-declared option, default one.

**Not fully accurate, attributed to a tool defect.** `task-05` reads "When
setting the test command, the user may say how many copies can safely run at
once; the tool then runs up to that many, and tells each copy which one it is
through an environment variable, so that a project can give each copy its own
database." The clause "the tool then runs up to that many" has no obligation.
`test-command-parallel-copies-limit` only says the configuration *includes* the
limit. In its place, `per-copy-database-selection` restates
`env-var-identifies-test-copy` and adds the purpose clause. Same shape as #386
(a listed item gets no obligation, and its slot carries a duplicate of another
obligation's text). The wording is not weak, so no rewrite. Drafted as a comment
on #386 in `docs/DEFERRED.md`. The missing obligation is held by hand at Gate 2.

Run 3's containment (`hide-env-var-values`) did not recur: run 4 has
`never-print-env-var-values`, which states only the values clause.
