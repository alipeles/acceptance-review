# Judgement — #167 Gate 2, run 2 (`7de7d71`)

Verdict: **INCOMPLETE**. 4 of 12 obligations below `strongly supported` — a
**different** four from run 1. The two run 1 flagged were now `strongly
supported`.

The diff since run 1 was **purely additive**: six added tests, nothing deleted or
weakened. Adding tests cannot reduce the evidence for an obligation, so any
rating that fell did so for reasons outside the diff.

| obligation | run 1 → run 2 | my judgement | disposition |
|---|---|---|---|
| `default-to-most-recent-review` | STRONG → `nominal` | **Real, and run 1 was wrong.** My test stored exactly one review, so it could not distinguish "newest" from "only". The test did not verify its own name. | **Addressed** — two stored reviews that disagree, written in a known order; plus a case where the newest review is the alphabetically *first* filename, which a name-sorted implementation fails. Defect-injected to confirm it bites. |
| `retrieve-from-stored-review-state` | STRONG → `partial` | **Real.** Nothing distinguished "read stored state" from "recomputed and happened to agree", and nothing proved the *named* revision was read. | **Addressed** — two stored reviews disagreeing on the same criterion, read by explicit `--revision`; plus a test that retrieval builds no model client and never enters the pipeline. |
| `byte-identical-retrievals` | STRONG → `partial` | **Rating noise.** The existing test invokes twice and compares output exactly, which is precisely what the recommendation asked for. No change made. | **Attributed** to rating instability. |
| `spec-no-longer-describes-written-file` | STRONG → `partial` | **Rating noise.** `test_the_spec_no_longer_names_a_written_file` asserts directly on spec text — exactly what the recommendation asked for. No change made. | **Attributed** to rating instability. |

**Outcome:** the two I addressed rose to STRONG in run 3. Of the two I attributed
to noise, `byte-identical-retrievals` returned to STRONG in run 3 with **no
change of any kind** — confirming the attribution. `spec-no-longer-describes-
written-file` stayed `partial`.
