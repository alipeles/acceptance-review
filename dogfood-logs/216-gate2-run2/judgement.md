# Gate 2, run 2 — #216 at `77ae7cb`

`INCOMPLETE`. Two obligations below strongly-supported, down from three. Run 1's
corrections re-armed the gate; this is the re-run.

## What closed, and why the credit is not mine

`obligation-decision-recorded-in-repository` moved **nominally → strongly
supported**, reported under `Changes since 2ae0fed7: closed`.

I initially read that as my three new DR-216 tests landing. **It was not.** The
mapped set for that obligation in this run is:

```
test_decomposition_round_trips_through_persistence
test_a_disposition_naming_a_renamed_obligation_still_links
test_a_fully_accounted_response_disposes_every_requirement
test_dr_202_no_longer_lists_requirement_id_stability_as_open
```

None of those is a `test_dr_216_*` test. The obligation was upgraded to
*strongly supported* on the strength of four tests that pass whether or not
DR-216 records anything — the same inverted evidence that had it at *nominally
supported* in run 1, re-scored upward. The rating moved in my favour for a
reason unrelated to the work.

Recorded here because it is the exact judgement failure CLAUDE.md and
session-state warn about, made in the direction that is easy to accept: a green
movement is not self-justifying, and *"my fix landed"* is a conclusion that has
to be checked against the mapped set like any other.

## 1. `obligation-region-level-coverage-assertion` — partially supported — REAL

The recommendation **sharpened** between runs, and the new version names
something the run-1 fix genuinely did not cover:

> Use a task-file fixture where the parser can produce the same requirement
> count *and exact per-span text for the claimed requirements*, but still miss
> some source characters because a claimed list item contains nested content.

Run 1's fix damages a span — truncates it. That is not #216's shape. The old
parser emitted nothing malformed: every span it produced was exact, `unclaimed`
was empty, and three whole blocks were simply absent. A damaged span is findable
by inspection; an absent block is only findable by accounting for the source.

A good catch, and a real distinction.

**Addressed** in `616f505`: reconstruct the pre-#216 parse by deleting the
nested spans from a good one, assert every span it still emits is exact, and
assert the check names all three missing blocks. The regression is now pinned
without needing the old parser to exist.

## 2. `obligation-region-level-total-coverage-tests` — unsupported — TOOL DEFECT

Unchanged from run 1, including the obligation id. Still the duplicate of
obligations 7 and 8 that absorbs `constraint-11` and `constraint-12` without
stating either. **Attributed to #223**, filed as `#223 (comment 5220684032)`.

That it reproduces byte-for-byte across two runs at two different SHAs is worth
more to #223 than either run alone.
