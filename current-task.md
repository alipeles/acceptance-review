# Task
Make a second review of the same task cheaper and more honest than starting
over. Today every run is a first run: the checker re-derives every judgment
from scratch even when the new work could not have touched most of them, and it
says nothing about what changed since it last looked. Let a review be re-run
against a new head, starting from the previous review of the same task —
re-judging the obligations the new work could have affected, keeping the
judgments it could not have affected, and reporting what closed since last time.

## Constraints
- A preserved judgment must never be presented as though it were re-derived
  against the new head. It carries a standing invariant of this tool: a reader
  can tell what each conclusion rests on.
- A re-run must not be able to improve a judgment it did not actually
  re-examine.

## Scope exclusions
- The checker's inputs are unchanged by this task; it reads what it already
  reads.
- The file the checker writes when a review has gaps is superseded by #167 and
  is not part of this task.

## Completion expectations
- Implementation
- A re-run against a new head starts from the previous review of the same task
  rather than treating the run as a first review.
- An obligation the new work could not have affected keeps the judgment the
  previous review reached, instead of being re-derived.
- An obligation the new work could have affected is judged again against the new
  head, so a fix made since the previous review is seen.
- A preserved judgment is marked as carried forward and names the revision it
  was established against, so a reader can tell it was not re-examined here.
- The evidence strength of a preserved judgment is the strength the previous
  review recorded, so a re-run cannot raise a claim it did not re-examine.
- The review reports what changed since the previous review, including the gaps
  that closed and the obligations whose status moved.
- A first review — one with no previous review to build on — reports no such
  comparison, rather than an empty or misleading one.
- When no usable previous review exists, the run completes as a first review
  rather than failing.
- On the archetype #9 revision cycle, an obligation that the previous review
  found weakly supported becomes strongly supported once the discriminating
  test is added, and the completion verdict moves with it.
