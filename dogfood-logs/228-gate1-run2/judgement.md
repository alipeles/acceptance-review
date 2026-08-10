# Judgement — #228 Gate 1, run 2

**Outcome: Gate 1 passes.** Re-run after the three wording fixes run 1's
judgement called for.

18 requirements, 17 obligations, 1 deliberately none, **no open questions** —
so there is nothing to triage under the gate's three-case table.

## Decomposition accuracy — confirmed

- **No invented obligations.** Each of the 17 traces to a bullet in
  `current-task.md`; the restatements are faithful, not embellished.
- **None of the real ones missing.** All 18 registry entries are accounted for.
- **The one `deliberately none` is correct.** `completion-01` is the bare word
  "Implementation", read as *"Section marker standing alone with no requirement
  under it."* Dropping it is right; inventing an obligation for it would not be.
- **The five scope exclusions are in absence form** and carry code-only
  admissibility, per #153. They are the boundaries this change must not cross —
  the parser's notion of a requirement (#216), obligation granularity (#117),
  decomposition accuracy (#211), pre-reshaping comparability (#204), and the
  wording of the corpus task files themselves.

## The three rewrites from run 1 landed as intended

| Requirement | Run 1 | Run 2 |
|---|---|---|
| `constraint-05` | "No case reaches a scoring hook without having been checked." | "A case built from either corpus is checked before it can be scored." |
| `completion-03` | ungrammatical ("A test asserts that failure by supplying…") | "A test demonstrates that failure with a task file the test supplies…" |
| `completion-05` | "…a scoring hook cannot be reached by a case that was not checked." | "…a case cannot be built from either corpus without the check being performed." |

Each is now a statement the intended change can actually satisfy, which the run 1
versions were not.

## Corpus state at this SHA

Every task file in both named corpora — and in `rating-stability/` — parses to a
non-empty registry today, so the guard changes no current outcome. That is the
point: `1c53592` fixed the instance, and this task fixes the mechanism. It also
means the guard cannot be demonstrated by the corpus, which is exactly why
Acceptance item 3 demands a test-supplied unparseable task file.

```
archetypes/01-missed-obligation                 requirements=  5
archetypes/03-superficial-test                  requirements=  1
...  (all 13 non-zero)
decompose-regression/189-gate1-run1             requirements= 20
decompose-regression/195-gate1-run1             requirements= 34
...  (all 8 non-zero)
```

## Queue

One filing drafted (synthetic benchmark cases whose task text yields an empty
registry). Nothing attributed to a tool defect from this run.
