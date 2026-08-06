# Judgement — #202 Gate 2, run 2

`acceptance check --task current-task.md --base 4ec4470 --head 2cb8084`.
Re-run after the scope correction the human authorised, per the re-arming rule.

**Verdict: INCOMPLETE. Still not clean — and the headline numbers improving is
itself the most important finding in this run.**

## The numbers look better and the review is worse

| | run 1 | run 2 |
|---|---|---|
| requirements | 47 | 52 |
| **yielded an obligation** | **46 of 47** | **42 of 52** |
| obligations | 35 | 36 |
| mapped tests | 80% | 92% |
| coverage gaps | 4 | **0** |
| strongly supported | 27 of 35 | **33 of 36** |
| recommended tests | 8 | **3** |
| open questions | 0 | 0 |
| unaccounted / unread | 0 / 0 | 0 / 0 |

Every headline moved the right way. **Nine of ten scope exclusions stopped
producing obligations**, each declined with identical boilerplate — *"Scope
exclusion naming a separate, excluded change."*

Fewer obligations means fewer things that can lack evidence. The four coverage
gaps and five of the eight recommendations did not get fixed; **their
requirements stopped being represented.** Mandate coverage fell from 46/47 to
42/52 and no headline figure moved to say so.

I recorded "much better" on first reading this run, and that was wrong. The
correction is the finding.

## Finding 1 — the verdict cannot see mandate coverage (#214, filed)

`derive_verdict(obligations, findings, open_questions)` never receives the
requirement map. A requirement that yielded no obligation contributes to none of
its three inputs, so **mandate coverage cannot move the verdict in either
direction.**

#202 made the loss visible in the report. It did not make it count.

This is the tool's own founding failure one level up. §3.7 bounds positive
results to *"no material gaps at the achievable tier"*, and the achievable tier
is silently reduced by requirements that never became obligations — with nothing
in the verdict disclosing the reduction. Worse: **a decomposer that drops
requirements now scores better**, because dropped requirements cannot generate
gaps. That defeats the control #202 exists to provide.

Filed as **#214**, child of #185.

## Finding 2 — run 3's conclusion does not survive (#193)

`dogfood-logs/202-gate1-run3/judgement.md` concluded that the unresolvable-
reference prompt rule fixed the scope-exclusion declines, on the evidence that
they went 2 of 10 → 10 of 10.

| run | task file | exclusions yielding |
|---|---|---|
| Gate 1 run 2 | A | 2 of 10 |
| Gate 1 run 3 | A + prompt rule | 10 of 10 |
| Gate 1 run 4 | A + parse fix | 10 of 10 |
| Gate 2 run 2 | A + 6 bullets, 2 rewordings | **1 of 10** |

The prompt is unchanged since run 3. Six added bullets and two rewordings flipped
it back. And `exclusion-09` and `exclusion-10` name **no issue number**, so this
is not the unresolvable-reference mechanism at all — it is a blanket position
that scope exclusions do not yield obligations, adopted and abandoned between
runs.

**The rule moved the outcome on one input; it did not make the behaviour stable.**
Run 3's judgement is corrected in place and the data is recorded on #193.

This is the second time this session that a conclusion drawn from one run has had
to be withdrawn. The first was the `exclusion-04` inversion. Both were single-run
readings that felt solid. That is what #211 is for.

## Finding 3 — the three remaining recommendations

| # | obligation | disposition |
|---|---|---|
| 1 | #195's suite runs unchanged | **#213** — the evidence is the existing green suite; the tool cannot read it |
| 2 | no case in #195's suite flips | **#213**, same |
| 3 | DR-202 records the resolved requirement-id decision | **fair and cheap.** A test can assert the document states it resolved and no longer lists it open |

Recommendations 1 and 2 are attributed to #213, filed before this run. I am
deliberately **not** writing a duplicate test to satisfy them: the evidence
already exists and is passing, and writing a redundant test to clear a gate is
precisely the behaviour this tool exists to discourage in others.

Recommendation 3 is actionable and I intend to satisfy it.

## Finding 4 — the scope correction worked

Run 1's four coverage gaps included two for the representational invariant, and
those are gone — correctly, because the task file no longer claims something
false. `exclusion-01` now excludes changing how obligations are *derived* rather
than which ones result, and that distinction holds: the derivation is untouched;
what changed is which requirements reach the model.

`obligation-transcripts-rerecorded-once` is gone with the requirement, which was
a process instruction no code could evidence.

All 36 obligations are `addressed`. Unrequested changes are 16 `in_service` and
1 `separable` (`dogfood-logs/`), correctly dispositioned.

## Prediction check

I predicted before this run that the residue would be #153 — scope exclusions
demanding proof of a negative — as it was for #190 and #195.

**Wrong, and wrong in an instructive way.** #153 did not fire because the scope
exclusions produced no obligations to demand evidence for. The condition that
suppressed #153 is a worse defect than #153.

## Disposition

| finding | disposition |
|---|---|
| verdict blind to mandate coverage | **#214**, filed, child of #185 |
| exclusion declines oscillate; run 3's conclusion withdrawn | **#193**, recorded; run 3's judgement corrected |
| recs 1–2, green suite unreadable as evidence | **#213**, filed before this run |
| rec 3, DR-202 doc assertion | **address it** — write the test |
| scope correction | delivered; run 1's two representational gaps resolved |

## Gate status

**Not clean, and it should not be forced clean.** The residue after satisfying
recommendation 3 is two obligations attributed to #213 — the same position #190
and #195 shipped from. Whether that is acceptable is the human's call, and it
should be made knowing that #214 means this run's clean-looking numbers were
partly produced by the mandate shrinking.
