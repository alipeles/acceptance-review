## Deliverable
nine minimal Git fixture repos, each a real task file + base/head diff + tests reproducing the archetype (missed obligation, qualifier missed, superficial test, non-discriminating input, circular expected result, mocked-out behavior, declaration mismatch, unrequested change, revision cycle).

## Acceptance
each fixture builds; `git diff base head` is non-empty; pytest runs (pass/fail as the archetype intends).
