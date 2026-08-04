# Decision Record 180 — Evidence-judgement instability, and where it lives

*Relates to issue #180 (open, under umbrella #183). Status: **findings recorded,
localized, unresolved.** Track: checker. Stage: 1.*

*A findings record, not a resolved decision. It exists because the measurement
took five dogfood rounds and two corrected judgements to produce, and none of it
is recoverable from the logs alone — `dogfood-logs/` is gitignored and
`current-task.md` is overwritten by the next task. One design decision **is**
settled here: what a fix must not do.*

---

## The measurement

Three consecutive `acceptance check` runs over a **byte-identical** task file,
against a **strictly growing** test suite, disagreed about **8 of 12
obligations**. Commits `07075a6` → `7de7d71` → `95b880a`.

| run 1 | run 2 | run 3 | obligation |
|---|---|---|---|
| STRONG | nominal | STRONG | `default-to-most-recent-review` |
| STRONG | STRONG | partial | `no-speculative-writing` |
| nominal | STRONG | STRONG | `fixed-command-surface` |
| STRONG | partial | partial | `spec-no-longer-describes-written-file` |
| STRONG | partial | STRONG | `byte-identical-retrievals` |
| STRONG | STRONG | partial | `remove-stale-next-instruction-file` |
| UNSUP | STRONG | STRONG | `replace-written-file-with-command` |
| STRONG | partial | STRONG | `retrieve-from-stored-review-state` |

Only 4 of 12 held their rating throughout. Full corpus — each run's task file,
report, and the judgement made at the time — in `tests/fixtures/rating-stability/`.

## The asymmetry — the load-bearing finding

> **In 7 of the 8 unstable obligations, the LOW rating was the correct one.**

Every rating that fell turned out to be the judge finally noticing a hole that
had been there all along. The most serious: `remove-stale-next-instruction-file`
was `strongly supported` in runs 1 and 2 while the `--json` code path **deleted a
file in the user's repo and reported nothing**. Run 3 dropped it to `partial` and
was right.

So the defect is **not that ratings move**. It is that `strongly supported` is
issued when it has not been earned. The tool errs toward "looks fine", which is
considerably worse than noise: a permissive false negative is invisible, and
Gate 2 is a shipping gate.

**This inverts the obvious fix.** Damping the judge to stabilise ratings would
make the symptom disappear while making the tool worse.

## The localization — M5.2, not mapping, not the reduce

#167 Gate 2 runs 4 (`52c52b8`) and 5 (`dd0a6a5`), one commit apart. Obligation
`replace-written-file-with-command`, **byte-identical mapped test set** in both:
`test_check_writes_no_instruction_file_even_when_the_review_has_gaps`,
`test_json_is_the_default_format_when_none_is_requested`,
`test_the_spec_names_the_command_the_cli_actually_accepts`.

The discrimination stage named essentially the same plausible defect in both runs
and judged it **oppositely**:

| run | `would_be_caught` | reason given |
|---|---|---|
| 4 | **true** | "The test explicitly checks that the file does not exist after `check`, so any implementation that still writes it would fail." |
| 5 | **false** | "The mapped tests mostly check that the command exists and that the file is absent in the exercised run… could slip past." |

**Run 4 is correct.** `test_check_writes_no_instruction_file_even_when_the_review_has_gaps`
invokes `check` on a review *with gaps* — exactly the case that previously wrote
the file — and asserts its absence. Run 5's verdict is not a defensible
difference of judgement; it is wrong about what the test does.

What this exonerates:

- **Mapping** (#182). The mapped set was byte-identical across the two runs, so
  #150/#173 are not the cause here.
- **`strength.py`** (M5.3). It is a pure deterministic reduce — `all caught →
  strongly_supported`, `some → partially_supported`. It cannot introduce variance.

The variance is **entirely in M5.2's per-defect `would_be_caught` verdict**. One
flipped boolean moved the obligation from `strongly_supported` to
`partially_supported`, and with it the run's verdict.

A second-order finding: the two runs also *worded the defect differently*
("…but also adds the new `recommendation` command so retrieval works too" vs
"…and only adds the new `recommendation` command as an extra way to view it").
**Defect enumeration is itself unstable**, so pinning verdicts is not enough — the
defect set they range over has to be stable first.

---

## Decision — what a fix must not do

Settled, and recorded here because the corpus makes it non-obvious:

**Stability must not be bought by blunting the judge.** Across five dogfood rounds
this stage found **seven real gaps** in the work under review, including the
silent file deletion, a test that stored a single review while claiming to verify
"the most recent" (it did not verify its own name), and two §9.5 fields that were
never asserted. Those are exactly what the tool exists to find.

Consequently #180's acceptance criterion *"adding a test never lowers any
obligation's rating"* was **struck**. Every falling rating in the corpus was
correct, so that criterion is satisfied by a permanently permissive judge — it
encodes the bug. The criterion that matters is: **`strongly supported` is not
issued on evidence that does not earn it.** The corpus supplies six worked cases
where it was.

## The inference to avoid

The most reusable thing here, because it was made twice and would have shipped a
silent file deletion:

> *The diff was purely additive; added tests cannot weaken evidence; therefore a
> rating that fell did so for reasons outside the diff.*

Both premises are true. **The conclusion does not follow.** A rating that falls on
an additive diff can equally mean the judge has finally noticed a pre-existing
hole — which is what happened every time it was checked.

Corollary for dogfooding: instability is not a licence to dismiss a finding.
Check the finding on its merits first; attribute to instability only after.

## Open

- Whether stabilising defect **enumeration** is a precondition for stabilising the
  verdicts, or whether both can be addressed together.
- Whether the fix belongs in the determinism component (#184) as a general
  "same evidence → same result" guarantee, or in the discrimination prompt/schema
  specifically (#183). The component work touches the request key and so forces a
  transcript re-record; sequence accordingly.
- `byte-identical-retrievals` (STRONG → partial → STRONG) is the one case still
  believed to be genuine noise. Given the record above, treat it as unsettled
  rather than as an established example.
- Whether #150 (mapping instability) and #154 (idempotent findings) close into
  #180 or remain the narrower halves.

## Related

- **#183** — evidence judgement umbrella; owns the fix.
- **#184** — determinism as an owned component; the human's design direction is to
  extend it from byte-identical *replay* to *judgement* stability.
- **#144** — the compound umbrella obligation involved in the localized instance.
  A real defect, and it makes the judge's job harder, but **not** the cause; an
  early attribution of the finding there was wrong and has been corrected.
- `tests/fixtures/rating-stability/` — the corpus, including two judgements I made
  wrong and rewrote. The errors are kept deliberately.
