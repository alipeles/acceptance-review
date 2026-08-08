---
description: Work the bundled queue at a gate — deferred defects, drafted filings, open decisions
---

Read `docs/DEFERRED.md` and work only the entries with `Status: open`.

1. Re-verify each one against the current code. Some will already be fixed, some
   will have been overtaken by later changes, and some will turn out to be wrong.
   Say which.
2. Group the survivors by kind (defect / filing / decision), then severity, and
   for each present:
   - the one-line title and location
   - for a **defect**: the drafted fix, updated if the code moved
   - for a **filing**: the issue body as it would be filed, with its labels and
     parent umbrella, shown *alongside the evidence that produced it*
   - for a **decision**: the recommendation and the alternative rejected
   - the blast radius: which Acceptance items or which umbrella it touches
   - your recommendation: fix now / fix next issue / won't fix / file as drafted /
     needs my call
3. Present the whole grouped list and **stop**. Use `AskUserQuestion` to get my
   disposition. Do not start fixing, and do not file anything.
4. After I approve, act on the approved entries one at a time.
   - For a fix: apply it, then run the checks that entry could plausibly affect
     and paste the result.
   - For a filing: create the issue or comment exactly as approved, and attach it
     to its umbrella as a sub-issue. Editing a draft after my feedback is not a
     second approval — re-show it.
5. Update each entry's `Status:` to `fixed (<commit sha>)`, `filed (#<n>)`,
   `wont-fix (<reason>)`, or `deferred`. Never delete entries — the queue is the
   record.

$ARGUMENTS
