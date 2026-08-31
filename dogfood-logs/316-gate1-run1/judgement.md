# Judgement — #316 Gate 1, run 1

Run `0bf2214b000f9f93`. 15 requirements, 14 with obligations, 22 decompose calls,
$0.1244. No open questions raised.

**Not accepted.** The Task section produced eight obligations from four
requirements, two of them invented and one of those contradicting a scope
exclusion in the same run.

## Findings

**1. Background became obligations, one of which contradicts an exclusion — mine
to fix, and an instance of #212 (task files cannot distinguish context from
requirements, so background becomes an obligation).** My Task narrative opened
with two sentences of background — "The review already records, for each
criterion, the ways a change could fail it, and for each of those and each
candidate test, whether that test would fail…" — stating existing behaviour as
if it were a requirement. Three obligations came out of it:
`record-criterion-failure-modes`, `candidate-tests-fail-on-each-failure-way` and
`criterion-rating-derived-from-failure-modes`.

The second of those says "For each recorded way the delivered code could fail a
criterion, and for each candidate test, determine whether that test would fail if
the code failed that way" — which is precisely what exclusion-01's obligation
`no-recording-or-judging-failures` says the change does **not** include. The two
obligations contradict each other, in one run, with no diagnostic. Disposition:
rewrote the narrative so the background sits inside a relative clause rather than
standing as its own sentences. Recorded as evidence for #212; nothing new filed.

**2. A duplicate pair from one sentence — evidence of #304 (twin obligations left
unmerged with no diagnostic).** `remove-older-judgement-of-test-discrimination`
("Remove the older judgement of whether each of those tests discriminates") and
`remove-discrimination-judgement` ("The change removes the judgement of whether
each candidate test discriminates") are the same requirement stated twice, from
one clause of one sentence, and the linking stage did not merge them. Known
defect; noted, not re-filed. Gone after the rewrite in run 2.

**3. A contentless obligation from a noun phrase, typed `test_demand`.**
`tests-the-review-recommends` — "The review recommends tests." Carved out of the
subject of a sentence whose actual requirement is about where those tests come
from. Same root as finding 1 (#212). Gone in run 3 after the compound subject was
split into separate sentences, so it is my wording rather than a defect that
survives good input.

**4. No open questions, in a task file with real ambiguity in it.** This is #303
(decomposition cannot raise an open question about a requirement that also yields
obligations, and has raised none since #217). Known; noted.

## Disposition

Rewrite `current-task.md`'s Task section and re-run with
`--continue 0bf2214b000f9f93`.
