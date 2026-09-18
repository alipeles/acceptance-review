# #340, Gate 1, run 3 — the inversions are gone; pronouns are the new problem

Run `23bd6200d738cd1e`, continuing `469fb7a97284a3d6`. 13 requirements, 1
derived, 7 carried, 5 revised. `task-01` was reported REMOVED with its three
obligations dropped — the background paragraph run 2's judgement blames, and
removing it removed every inverted obligation. No open questions.

## What was still wrong

Three obligations lost the subject my sentence carried in a pronoun:

- `test-fails-to-catch-defect-not-demonstrated` — *"A test does not demonstrate
  that it fails to catch the defect."* My sentence was *"…and it is not a
  demonstration that the test fails to catch the defect"*, where **it** is the
  dropped pair. The obligation is now about the test and says nothing.
- `injection-attempt-decision-basis` — *"The decision is based on the injection
  attempt."* Contentless, and typed `human_review`.
- `must-not-read-as-though-it-had-been` — the id is a fragment, though run 3's
  description was still readable.

This is #330's shape — an obligation description that refers outside itself —
which is already filed, so nothing new is queued for it.

## Disposition — reworded for run 4

Each pronoun replaced with the noun it stood for. Recorded here rather than
treated as a tool defect because the input genuinely carried the ambiguity: my
sentence needed the previous clause to be understood, and an obligation is read
alone.

## Kept from this run, unreworded

`red-test-does-not-identify-defect` came out of a *because* clause — my
rationale, not a requirement. Left in place: it states a real invariant of the
design (a test that went red still goes to the model), so it is worth judging.
