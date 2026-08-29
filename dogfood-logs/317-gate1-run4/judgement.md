# #317 Gate 1, run 4 — did not pass

Run `7cb6be48b0942761`, continuing `40c12c90018b3526`, at `a10cdc0`.

`current-task.md` had been replaced wholesale for this run: the previous mandate
was about combining several accounts of one requirement, and the new one is
about accounting for each requirement on its own and judging the opening summary
last. `--continue` was passed because `CLAUDE.md` asks for it on a re-run.

## Why it did not pass

Two obligations are wrong, and both come from the carry rather than from the
decomposer.

**`exclusion-04` was inverted.** The requirement is a scope exclusion —
*"Combining obligations that state the same thing as one another."* The carried
obligation is `combine-agreeing-accounts-2`: *"The review combines agreeing
accounts of the same requirement into one account and carries on."* That
requires the delivered change to do the work the mandate excludes. The
`-2` suffix is the id-collision marker, so it is a carried id.

**`completion-06` kept a stale id.** Its description is correct — *"A test fails
when a stretch the already-derived obligations require yields an obligation"* —
but its id is `combined-agreeing-accounts-stop-review`, from the mandate this
file replaced. The id no longer names what the obligation says.

The run reports nine `REMOVED` requirements, all from the previous mandate, so
the carry did notice the file had changed. It removed the requirements and kept
obligations derived from them.

## Triage

**Attributed to a tool defect**, and it is an already-filed one: **#306**, the
sub-issue of #181 recording that a continued run keeps an obligation after its
source sentence is deleted. This instance is stronger — inversion rather than
orphaning — so it is drafted as a comment on #306 in `docs/DEFERRED.md`, not as
a new issue.

Nothing was rewritten in `current-task.md` in response. The wording is not the
problem; the fresh run over identical text is correct.

## Disposition

Re-ran fresh, without `--continue`, as run 5. `--continue` is wrong here by
construction: #269's carry exists to hold an obligation stable when a
requirement is **reworded**, and this mandate was replaced.

## Also observed

`acceptance decompose … > output.log` exited 0 and left a **zero-byte** file on
the first attempt. Removing it and re-running the identical command produced the
full log. This is the defect `CLAUDE.md` documents with cause unknown; it fired
again on run 5. No action, no filing — it is already recorded.
