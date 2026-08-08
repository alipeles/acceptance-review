# Task
Obligation derivation reads one requirement at a time and produces obligations
for it alone, so a requirement stated in two places yields two obligations that
assert the same thing. On one observed task file, 34 requirements produced 71
obligations. Every later stage runs once per obligation, so the duplication
multiplies the work and the length of the report while adding nothing.

The duplication is not a fault in the input. A mandate and its acceptance
criteria naturally restate each other, and a requirement is often followed by a
clause giving the reason for it. Both are ordinary ways to write a requirement,
and both currently produce a second obligation.

Add a pass that runs after derivation and recognises when two obligations state
the same requirement. Its output is a link rather than a deletion: the surviving
obligation is named by every requirement that stated it.

## Constraints
- The pass runs after obligation derivation, over the obligations derivation
  produced, rather than inside derivation.
- Recognising a duplicate produces a link from a second requirement to an
  existing obligation. No obligation is deleted and no requirement text is
  discarded.
- A linked obligation carries the union of the requirement links and the union
  of the source spans of everything merged into it, so it still traces to every
  piece of task text that produced it.
- The links are typed fields in the schema-constrained response. A link stated
  in an obligation's description, rationale, or any other free-text field does
  not count as a link.
- Two obligations about the same area of the change are not necessarily the same
  requirement. Where the judgement is uncertain, leave them separate.
- A requirement and a clause giving the reason for that requirement state one
  requirement, not two.
- The obligations derivation produced, before any linking, are persisted in the
  review state. They are provenance rather than report content.
- Obligations derived for a requirement change only when that requirement's own
  relevant inputs change.
- The links this pass produces are identical unless the derived obligations they
  were computed from change.
- Two runs over byte-identical task text produce byte-identical review state,
  both for the derived obligations and for the linked result.
- Typed schemas are pydantic models, as the rest of the repository defines them.
- Tests issue no live model calls.

## Scope exclusions
- How finely a single requirement is split into obligations, which is #117.
- Measuring how accurate the links are, which is #211.
- The wording of the decomposition prompt beyond what this pass requires, which
  is #205, #206 and #219.
- Whether an obligation needs test evidence at all, which is #148.
- Recovering requirements that an earlier run dropped.

## Completion expectations
- Implementation
- A task file stating one requirement in two sections yields one obligation
  linked to both requirements, whose source spans cover both statements.
- A test asserts that two distinct requirements sharing vocabulary are not
  linked to one obligation.
- A test asserts that a requirement followed by a clause giving its reason
  yields one obligation rather than two.
- A test asserts that the obligations derivation produced, before linking, are
  present in the persisted review state.
- A test asserts that a link is expressed as a typed field, and that the
  response schema cannot express a link as free text.
- A test asserts that two runs over byte-identical task text produce
  byte-identical review state at both the derived and the linked stage.
- A test asserts that changing a requirement's own inputs changes only that
  requirement's derived obligations.
- A test asserts that the links are unchanged when the derived obligations they
  were computed from are unchanged.
