# DR-437: four obligation types, not ten

**Status:** decided by the owner, 2026-11-02, while starting #437 (synthesis:
obligations produced from claims). **Parent:** #435, the decomposition redesign.

## Decision

An obligation has one of four types:

| type | meaning | evidence it requires |
|---|---|---|
| `requested_behavior` | something the change must do, observable from outside it | code and tests |
| `constraint` | a condition on how the work is done, settled by reading the change | code only |
| `scope_exclusion` | work the change must not do | code only; satisfied by absence |
| `test_deliverable` | a test that is itself the thing delivered | tests only |

They replace the ten types the spec's §7.3 (requirement interpretation) listed:
functional, boundary, error handling, invariant, regression, compatibility,
explanation/observability, docs/config, human-review and test-demand. The
evidence column is a rule the code applies from the type; synthesis does not ask
the model for it.

## Why

The design (`docs/decomposition-redesign.md` §2 and §5 step 3) asked for
obligations typed as requested behaviour, constraint or scope exclusion "using
the existing type field". That field did not hold those distinctions. It held the
ten-value list, which nothing used to tell a request from a constraint.

Reading the code showed what the ten types bought:

1. **Defect checklists.** Defect enumeration asks about four general failure
   modes for every obligation, and each of eight types added two of its own
   (`defects/taxonomy.py`). This was the only use with real effect.
2. **A merge guard.** Linking never merged two obligations of different types
   (`requirement/linking.py`), so a behaviour and a demand for a test of it
   stayed apart (DR-232). Synthesis now merges restatements itself, and the
   redesign's pruning step drops a test paired with its behaviour.
3. **A benchmark score** of each obligation's type against the archetype labels.

Two considerations settled it. Constraints and scope exclusions never reach
defect enumeration, which only receives obligations owed tests, so a second
"what kind of behaviour" value on them would be filler. And the owner, who wrote
the product, could not say what several of the ten meant; a classification its
author cannot apply cannot be labelled, evaluated or argued with.

## Alternatives rejected

- **A separate `kind` field beside the ten types.** Keeps the per-type checklists,
  but every constraint and exclusion would carry a meaningless behaviour type.
- **Keep the ten, add `constraint` and `scope_exclusion`** (twelve in all), and
  revisit after #440's evaluation. Recommended at first; the owner chose to
  simplify now.

## Consequences

- **Staged.** #437 adds the four values to `ObligationType` beside the old ten;
  only synthesized obligations use them, and nothing downstream reads those yet.
  The issue that switches the pipeline over to synthesis deletes the old ten.
- **Defect enumeration loses its per-type failure modes.** At the switch-over a
  `requested_behavior` obligation is asked about the four general modes only;
  constraints, scope exclusions and test deliverables are not enumerated. This
  changes enumeration's requests, so its recordings re-record then. Whether the
  lost modes found defects the general ones missed was never measured.
- **`required_evidence = neither` is no longer produced** by synthesis: an
  obligation only a person can judge has no type of its own. The switch-over
  issue decides whether that needs one.
- **Archetype ground-truth labels** carry the old types. The switch-over issue
  maps the mechanical ones (every behaviour type to `requested_behavior`) and
  gives the owner one document for the rest, each with its evidence, a
  plain-English explanation and a recommended label. No label changes unasked.
- §7.3 of the spec is edited to the four types and points here.
