# #335 Gate 1, run 1 — judgement

Run `384604f689ad8fca`, `acceptance decompose`, on the task file in this
directory. 12 requirements, 10 with obligations, 1 open question. **Not a
breakdown I would defend.**

## task-01 — background paragraph became eight obligations (tool defect, #212; also my wording)

The opening paragraph describes today's verifier and its failings. It produced
eight obligations, three of which demand the defect being removed:
`single-model-call-before-and-after` (keep the one-call design),
`refuses-too-few-bad-edits` and `too-many-good-ones`. The other five restate the
problem or the goal (`reduce-cannot-tell-refusals`, `cannot-tell-refusals`,
`avoid-cannot-tell-refusals` are one property three times).

Attribution: #212, where a task file has no way to mark background as
background, so it becomes an obligation. Already filed under #181 (the
decomposition umbrella); nothing new to queue. The rewrite for run 2 removes the
paragraph: the reason for the change lives on the issue, not in the mandate.

## task-02 — one sentence, two identical obligations (tool defect, #277)

`split-check-into-two-questions` and `asked-in-sequence` state the same thing.
Matches #277, where one requirement yields two obligations differing only in
voice. Already filed.

## task-04 — condition split from the property it governs (tool defect, #343; also my wording)

`asked-only-about-edit-that-does-change-behaviour` is a bare condition
("the requirement applies only when…"), and `defective-behaviour-match` asserts
that every changed edit matches its defect, which is a property of the edits,
not of the software. Nearest filed defect: #343, where a condition governing two
conjuncts is dropped from one of them. My sentence ("The second is asked only
about… : does the changed behaviour match…?") was a question, not a statement of
what the software does; reworded for run 2.

## constraint-01 — wrong question

`constraint-01-open-1` asks what check should be preserved or changed about
whether the two questions are shown the tests. The constraint answers it: neither
question is shown the tests or their results. "The two questions" is defined in
the Task section. Nearest filed defect: #178, where the decomposer raises open
questions about terms another section already defines. Not certain it is the
same cause. **Per the Gate 1 table, a wrong question is a stop: reported to the
human, not worked around.** The constraint's real obligation is missing from the
breakdown as a result.

## Scope exclusions and the documentation line

Correct. Exclusions yield "the change does not include…" obligations, as #219
(closed) established they should.
