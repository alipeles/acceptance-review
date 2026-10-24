# #405 Gate 1, run 3 — judgement

Run `4fe56787714b80f4`, continuing run 2. 8 requirements, 20 obligations, 0 open
questions.

**Accepted as accurate**, pending the owner's confirmation at Gate 1. Every
requirement in the task file has its obligations; none is invented.

One tool defect, attributed and queued: `hide-env-var-values` ("Each test run
prints the names of the environment variables passed to the tests, while hiding
their values") contains the whole of `print-env-var-names` and adds one clause.
It should state only that values are never printed. It is close to #277 (two
obligations from one requirement stating the same property, differing only in
voice) but is a containment rather than a restatement. Drafted as a comment on
#277 in `docs/DEFERRED.md`.

No open questions. Not raised, and an implementation detail left to the builder:
what the tool does when no test command is set. The plan keeps today's behaviour
in that case.
