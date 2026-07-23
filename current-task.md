# Task
Fix obligation-attribution so a diff region that literally delivers an obligation — including obligations that ask for fixture/test/example artifact content whose content resembles a questionable change — is no longer misclassified as an unrequested or not-addressed change.

## Constraints
- Sharpen the classify_coverage and detect_unrequested_changes system prompts so a region is checked against the full text of every obligation, including obligations phrased as "add/include a fixture/test/example representing X", before being classified not_addressed or unrequested.
- A region whose content is literally what such an artifact obligation asks for must classify as addressed coverage, and must not be flagged as an unrequested change.
- Recall must not drop: a genuinely unrequested change that no obligation explains must still be flagged (bias toward surfacing the unexplained).
- File category may feed the prompt as a hint, but the fix is the model's attribution reasoning, not a structural filter.

## Completion expectations
- The two sharpened prompts
- Live before/after verification, since prompt quality cannot be asserted by injected-response unit tests
