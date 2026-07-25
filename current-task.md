# Task
`classify_coverage` cannot positively confirm a prohibition-style obligation ("leave X unchanged") — it always reads as a gap. Root cause: a negatively-phrased obligation has no positive response by construction, so the coverage classifier, whose frame is "does the diff respond to this?", is structurally doomed to classify it `not_addressed`. Fix it at the source by having `decompose` state obligations as positive invariants, and having `classify_coverage` treat a preserve/maintain obligation as addressed when the diff does not violate it.

## Constraints
- Keep the existing `CoverageStatus` set; introduce no new status value and no rename. There must be one positive indicator (`addressed`), meaning the evidence was reviewed and the obligation is confirmed handled.
- `decompose` must state every obligation as a positive invariant — the property the code must hold — converting any prohibition ("don't do X", "leave X unchanged") into the property it protects ("maintain X"). A prohibition and the invariant it protects are the same obligation.
- `classify_coverage` must treat a preserve/maintain obligation as addressed when it is not violated, including when no diff region touches it (empty diff references are valid for a satisfied invariant); when the diff violates such an obligation, it is not addressed and should cite the violating change.
- Reframing fixes how obligations are filed, not what evidence exists: an invariant that genuinely needs runtime or non-code evidence still routes to the appropriate status; this change lowers no bar on what counts as confirmed.

## Completion expectations
- Implementation: decompose prompt emits positive invariants; classify prompt handles preserve/maintain obligations and permits a violated invariant to cite the breach; archetype #8's ground-truth obligation rephrased positively for consistency.
- Unit tests: a preserve obligation not violated classifies addressed with no diff references; a violated preserve obligation classifies not addressed and cites the violating hunk.
