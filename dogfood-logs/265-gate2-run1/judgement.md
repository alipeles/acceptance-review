# Judgement — #265, Gate 2, run 1

`check --base c63bf86 --head a332e29 --continue 7971c67ae6329468 --mode record`.

## Outcome: the run aborted at the mapping stage, and the defect was mine.

```
acceptance.request_blocks.BlockError: SUBJECT block contains 'cache_control'.
Where a request's reusable opening ends is the client's to mark, not a stage's.
```

`assemble` scanned every block's text for a provider breakpoint, on the
reasoning that a stage writing one would be doing the client's job.

**A block's text is mostly not the stage's own words.** A mapping request's
SUBJECT is the source of the tests under review, and the DIFF block is the diff
under review. This branch's `tests/test_reusable_opening_marker.py` contains the
string `cache_control`, so the tool refused to map its own tests — and `llm.py`
now contains it too, so coverage classification and unrequested-change detection
would have aborted on the diff a moment later.

Generalised: **the tool could not review any repository that mentions prompt
caching.** It treated content under review as though the content were
instructing it.

## Triage: my defect, fixed here, not filed

This is not a defect in the tool-as-shipped; it is a defect in the change under
review, found by running the change against itself. It is inside this task's own
area and it made the task's Acceptance unreachable, so it was fixed immediately
(*Working agreement* §4 exception) as `8a09d5c`.

The fix removes the scan rather than narrowing it, because the scan was
unnecessary as well as wrong. A block carries a `str`; a provider breakpoint is
a structured content part that `llm.mark_reusable_opening` creates by replacing
a message's content with a list. A stage cannot emit one through `assemble`
whatever text it writes, so the guarantee is structural and the scan was theatre
on top of it.

Three tests replace the one that asserted the old behaviour: assembled contents
are always plain strings; no prompt a stage *authors* mentions a breakpoint,
checked against `authored_prompts()` rather than a live request; and a request
carrying `cache_control` in both its diff and its subject assembles cleanly —
which is this failure, pinned.

## Worth keeping

This is the clearest instance so far of dogfooding catching something no unit
test would. Every unit test of `assemble` passed, because they were written with
blocks I authored. The failure needed a *real repository* whose content
overlapped the tool's own vocabulary, and this repository is now permanently
such a case.

No request bytes changed, so nothing re-recorded.
