# #405 Gate 1, run 1 — judgement

Run `ccd98d16ee12d812`. 8 requirements, 21 obligations, 0 open questions.

**Not accepted.** The opening paragraph described today's broken behaviour in
the present tense, and the decomposer turned it into six obligations that
*require* that behaviour: `use-tool-interpreter`, `cwd-launch-directory`,
`subdir-tests-not-run`, `project-dependencies-available-to-tool-interpreter`,
`pytest-name-mismatch`, `pytest-declines-all-tests`.

Attributed to my wording, not to the tool: the paragraph never said "today" or
"currently", so reading it as a statement of required behaviour is a fair
reading. Fixed by rewriting the paragraph as the outcome that must hold (run 2).

Also lost: "never the values" of the environment variables had no obligation.
Reworded into its own clause for run 2.
