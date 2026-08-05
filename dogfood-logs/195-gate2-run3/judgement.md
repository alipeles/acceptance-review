# #195 Gate 2 — judgement across three rounds

*`check --mode record`, base `dbb342f`. Rounds 1-3 at heads `4425e51`,
`61cde69`, `ac3a71d`.*

## Verdict

**Gate 2 passed at round 3**, clean on every criterion: 23 obligations all
addressed and strongly supported, both open questions resolved, no recommended
tests, no risky unrequested change. Two rounds of real findings preceded it, and
both were addressed with code rather than attributed away.

| round | verdict | flagged |
|---|---|---|
| 1 | INCOMPLETE | 1 obligation — `update-readme-status` unsupported |
| 2 | INCOMPLETE | 19 obligations non-discriminating; 1 unsupported |
| 3 | NO-MATERIAL-GAPS | none |

## Round 1 — a real gap, fixed

`update-readme-status` was `unsupported`, no mapped test. Correct: the README
changed and nothing held it there. The recommendation asked specifically that the
old blanket claim be *gone* rather than contradicted by a newer table below it,
which is the sharper requirement and is what the test now asserts.

## Round 2 — the finding that mattered, and the noise around it

Round 2 fell from 1 flagged obligation to 19 on a diff that **only added a
test**. That is #191's shape exactly, and DR-180 names the inference to avoid:
purely-additive diff, added tests cannot weaken evidence, therefore the drop is
noise. Both premises true, conclusion false. Checked on merits before deciding.

**The real finding.** `no-live-model-calls` was `unsupported`, no mapped test.
Genuine: the degenerate decomposers run in RECORD mode, which reads like a live
call and is not one, and that holds only while every client injects its own
`completion_fn`. Nothing would have noticed one that stopped. Fixed, and verified
non-vacuous — a `ModelClient` built without `completion_fn` does pick up the
patched default, so the assertion fires on the regression it is written for.

**The mapping audit, before believing or disbelieving the rest.** 15 mapping
transcripts, 149 test judgements, **87% carrying at least one obligation id**.
DR-164's half-blind failure was ~17%; #189's Gate 2 read 76% unfiltered. This run
was not half-blind, so the findings could not be dismissed as blindness.

**What drove the other 18.** Mapped sets containing plainly unrelated tests —
`test_dirty_working_tree_matches_committed_diff_shape` mapped to *"assert content
differences separately from shape differences"*, and
`test_archetype_8_unrequested_change_gap_matches_via_its_obligation` mapped to
four separate obligations it has nothing to do with. An irrelevant test in the
mapped set gives the discrimination stage a defect it cannot catch, which is what
pulls a rating to `partially supported`. **#173**, recorded there.

The movement itself — 17 obligations `strongly` → `partially` and back to
`strongly` in round 3 with no change to their evidence — is **#191**, recorded
there.

## Unrequested changes — investigated, not waved off

Eight, none `risky` (round 1 had rated the `decompose_case` change risky; it is
`in_service` in round 3, correctly, now that a test pins it).

Six `in_service` are the shared-model extensions this task needed and which were
stated as a design decision before any code: `expected_type`, `required_symbols`
and `open_questions` on the ground-truth shape, `decomposition_precision` on the
score, the decompose-case builder, and `decompose_case` carrying open questions.
All additive, all defaulted, no existing fixture touched.

Two `separable` — `session-state.md` and `dogfood-logs/195-gate1-run1/` — are
accurate findings and correctly labelled. Both are mandated by CLAUDE.md rather
than by the task's obligations, which is precisely what `separable` means. No
action, and worth noting as structural: **every PR in this repo will carry these
two**, because the conventions that require them are not part of any task
mandate. Not a defect in the tool; possibly an argument that the advisory
presentation in #88 should learn to recognise repo-conventional artifacts.

## What this run does not establish

The suite runs against stub decomposers. It proves the ground truth is encoded,
that the metrics reach 1.0 on a faithful decomposition and fall in both
directions on a degenerate one, and that the scoring path is wired. It does not
measure any real decomposer — that is the model experiment this scoreboard was
built to make scorable, and it has not been run.
