# Task
Make a re-run against a new head build on the previous review instead of
starting over. When an agent addresses the gaps a review reported and produces a
new head, the checker should re-derive only what the new work could have
affected, carry the rest forward, and show the reader what changed since the
last review — which gaps closed, which obligations flipped, and how the overall
verdict moved. A judgment that was carried forward rather than re-derived must
say so, and say which revision it was established against.

## Constraints
- Review state must stay byte-identical across two runs over the same input, so
  nothing about ordering a re-run may depend on wall-clock time or on the order
  reviews happen to have been written.
- A carried-forward judgment keeps the evidence tier it was originally
  established at; a re-run must not raise a judgment's tier without re-deriving
  it.

## Scope exclusions
- Reviewing more than one new head at a time, or reconciling reviews that
  diverge on separate branches, is out of scope; a re-run considers one prior
  review and one new head.
- Rendering unrequested-change findings as advisory is M7.6's deliverable, not
  this one.

## Completion expectations
- Implementation
- A re-run identifies the prior review to build on without relying on when
  reviews were written or on any ordering the store happens to preserve.
- A review records the task it was produced from, so a re-run can tell that the
  task itself changed and decline to carry any earlier judgment forward.
- An obligation whose code and tests are untouched by the new work keeps its
  previous judgment rather than being re-judged.
- An obligation the new work could have affected is re-derived from the new head.
- A judgment that was carried forward is reported as carried forward, naming the
  revision it was established against, so a reader can tell which parts of a
  review are fresh.
- The report states what changed since the prior review, including any gap that
  closed and any obligation whose evidence classification moved.
- The overall completion verdict reflects the new head, so a re-run after the
  reported gaps are addressed no longer reports those gaps.
- The archetype 9 revision cycle, re-run from its base review against its head,
  flips the previously unsupported obligation to supported and updates the
  verdict accordingly.
