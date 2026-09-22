# #334 Gate 1, run 5 — judgement

Run `635a306672ff17b2`, continuing `f1594dbe2bba8c92`. One decompose call.

**Not accepted — a tool defect.** Scope exclusion 3 was reworded after Gate 2
run 1 found it contradicted #334's Deliverable. The run marked it `revised`,
recorded the old text as its `revision_reason`, and made a fresh model call for
it — and the obligation that came back was the old one, word for word:
*"The change does not include running the candidate tests or making any decision
based on their results."* Its type moved from `regression` to `docs_config`, so
it was re-derived, not carried; the model reproduced the previous derivation.

Gate 2 would then have judged the old exclusion again. Queued as a filing under
#181, the decomposition umbrella. Run 6 decomposes afresh.
