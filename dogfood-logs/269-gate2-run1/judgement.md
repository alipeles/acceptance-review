# Judgement — #269 Gate 2, run 1

`check --task current-task.md --base 9def9e7 --head c7bbd46`.

**Not clean.** `Task completion: INCOMPLETE` —
*1 obligation(s) with non-discriminating test evidence
(schema-change-blocks-carry-forward).*

## The finding was correct, and it was mine

`completion-08` — *a change to the decompose response schema prevents carrying
the obligations derived under the previous schema* — came back
`test evidence: unsupported`, `(no mapped test)`.

It was right. The carry key hashes the response schema, so the behaviour exists,
but I had written invalidation tests for the model, the seed, the stage-logic
version and the prompt, and none for the schema. Untested behaviour is not
evidence.

The recommendation was precise and usable as written:

> Use a two-run scenario with the same task text and the same prior ledger entry,
> but change only the response schema between runs in a way that would alter the
> carry key while leaving the requirement text unchanged.

Fixed in `8e6a934` with two tests rather than one, because they catch different
defects — see that commit and run 2.

## Everything else

54 of 55 requirements yielded obligations; the one declined is `completion-01`
(*"Implementation"*), a section marker, taken at face value. No open questions
unresolved. Ten unrequested changes reported, nine `in_service` and one
`separable` — the DR, which no obligation asks for and which the convention
requires anyway.

No tool defect attributed from this run.
