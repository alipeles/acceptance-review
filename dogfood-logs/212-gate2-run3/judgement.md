# #212 Gate 2, run 3 — judgement

Run `5076ddb96cdb7690`, `acceptance check --base 21d12a9 --head e9568dd
--mode record --continue 39ddd65329d04089`. Full suite at e9568dd: 2,014
passed, 1 skipped.

**Not clean.** Verdict NO-MATERIAL-GAPS; all 9 test-owed obligations strongly
supported, mandate coverage 7 of 7, no recommended tests. Run 2's two
partially-supported ratings closed. Two things stop it, and both are about the
sub-heading rule the owner ruled on during run 2.

## 1. Unrequested change: the sub-heading logic

`[in_service]` on `task_file.py`'s heading-level tracking: "No obligation asks
for this nested-heading logic … and the scope exclusions rule out nested
Context handling."

- Partly right: no obligation states the sub-heading rule. It came from run 1's
  finding and the owner's ruling, neither of which is in `current-task.md`.
- Partly wrong: `exclusion-02` excludes Context sections nested INSIDE OTHER
  sections, not sub-headings inside Context. My wording ("Context sections
  nested inside other sections; there is one top-level Context section") is
  ambiguous enough to invite that reading.

## 2. "Needs human review": the expected behaviour flipped between runs

Run 2 asserted, as a defect the code already had, that a `### Constraints`
under Context was swallowed into Context. Run 3 asserts the exact opposite as a
defect: that it ends Context and becomes mandate
(`subheading-in-context-leaks-to-mandate`,
`nested-mandate-named-heading-ends-context`), with the repair `if nested:` —
which is run 2's defective code. The owner ruled for ending Context.

I believe the cause is the same as finding 1: the mandate does not state the
rule, so each run infers an expected behaviour, and the inference is unstable.

The other five entries repeat runs 1–2 and are not defects: exact heading match
(four entries) and the always-present `context` field (one).

## Owner's decision (2026-10-25)

"Just move forward. Let gate 2 be unclean." Gate 2 ends at this run, not
clean. Both findings are attributed to #430 (a behaviour the mandate leaves open
is reported as a defect in whichever direction the code took), filed under
#183, the evidence-judgement umbrella. The task file was not changed.

## Dispositions proposed before the decision

- Add the sub-heading rule to `current-task.md` as a requirement and reword
  exclusion-02 so it cannot be read as excluding it. This is a genuine mandate
  change from an owner decision, not a rewording to silence a finding, so it is
  put to the owner rather than made.
- Queue a tool-defect draft (`docs/DEFERRED.md`): when the mandate leaves a
  behaviour open, the "defects the code already has" section asserts a
  defect in whichever direction the code went, and flips across runs, instead
  of raising an open question.
