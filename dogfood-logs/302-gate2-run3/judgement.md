# Judgement — #302 Gate 2, run 3 — the gate got WORSE from a strictly better input

Base `93740a9`, head `dbc6099`. **Verdict: INCOMPLETE, and further from clean
than run 2.**

| run | head | obligations flagged |
|---|---|---|
| run 2 | `11a8a5a` | **1** |
| run 3 | `dbc6099` | **8** |

The only difference between them is that run 3's branch **adds one test** — the
one run 2's own recommendation asked for — and corrects a docstring. No source
behaviour changed. Adding the evidence the review asked for made eight
obligations worse, including five that were `strongly supported` in run 2.

## This is not a finding about the delivered work, and must not be treated as one

The new test **is** mapped: it appears as evidence 1.6 and 2.5. The obligations it
supports were nonetheless downgraded from `strongly supported` to `partially
supported`, and run 3's recommendations then ask for things that test already
does — *"Capture both the prompt opening and the response_format/schema for each
call"* is a description of
`test_two_batches_of_one_run_offer_the_provider_the_same_reusable_opening`.

Some recommendations have moved to demanding what no test can settle:
*"including any metadata beyond schema/messages that could affect cache reuse"*
asks for evidence about the provider's internals.

**The mapped sets also move between runs with no cause in the diff.** Obligation 5
(`constraint-04`) is `strongly supported` in both runs but cites a different set
of tests in each — `test_the_instruction_requires_every_overlapping_obligation_not_the_closest`
and `test_an_unsupplied_obligation_id_is_recorded_rather_than_silently_dropped`
appear in run 3 and not run 2, on unchanged code.

## Disposition

**Attributed to the tool**, on the rating-instability defect already tracked
under **#251** (adding tests degraded 33 obligations) and umbrella **#183**.
Recorded against them; a comment is drafted for #251 carrying this pair, because
this is a cleaner instance than the original: one added test, no behaviour
change, 1 → 8.

**Not acted on, deliberately.** The two permitted dispositions are to address a
finding or to attribute it, and addressing this one would mean writing more tests
to chase ratings that moved for no reason in the diff — which the gate's own rules
forbid and which run 3 shows does not converge: run 2's single recommendation was
satisfied honestly, and the result was eight.

## What this means for #302

**The gate cannot currently be reached on this task**, and that is a statement
about the instrument, not about the branch. The branch is green (1514 passed),
lint and format clean, no transcript re-record, and the delivered behaviour is
the one #302 asks for and DR-302 argues.

A human decision is owed on whether to ship on run 2's evidence — one honest
finding, acted on — or to hold #302 until the rating instability is fixed. That
is not a call to make inside the session that produced it.
