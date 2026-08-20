# Judgement — #293 Gate 1, run 1

Command:

```bash
.venv/bin/acceptance decompose --task current-task.md --mode record \
  --continue fea8e0fd30dd6f0d
```

Run id `136b6616a990d48f`, continuing `fea8e0fd30dd6f0d` (#291's Gate 2 run 2).
`output.log` is 10,294 bytes. Exit 0. Six live model calls, $0.0360.

## Is the breakdown accurate?

Yes, on the two questions Gate 1 step 2 asks. **No obligation was invented** —
every one traces to a line of `current-task.md`. **No requirement was lost** — all
25 requirements are present (1 task statement, 8 constraints, 6 scope exclusions,
10 completion expectations), 24 yielded obligations and `completion-01`
("Implementation") was correctly recorded as a section marker with no requirement
under it.

The carry behaved as the handoff predicted: 13 requirements derived, 2 carried,
10 revised, and the 8 requirements belonging to #291's task file were dropped
with their obligations, each named in a `REMOVED` line.

## Finding 1 — five of seven twin pairs left unmerged (tool defect, #304)

The task-file convention states each rule as a Constraint and mirrors it as a
Completion expectation, which produces twin requirements that should link to one
obligation. Seven such pairs exist here. **Two merged, five did not.**

| Constraint | Completion expectation | Merged? |
|---|---|---|
| `constraint-01` unchanged inputs keep the stored rating | `completion-02` (first half) | **no** |
| `constraint-02` unchanged inputs cost no judgement request | `completion-02` (second half) | **no** |
| `constraint-04` mapped test set changed → judged again | `completion-05` | yes |
| `constraint-05` requirement text changed → judged again | `completion-06` | yes |
| `constraint-06` the file-touch rule is removed | `completion-07` | **no** |
| `constraint-07` coverage and evidence staleness decided separately | `completion-08` | **no** |
| `constraint-08` a repeated review produces the same review state | `completion-09` | **no** |

`constraint-03` has no exact twin (`completion-03` and `completion-04` are
instances of it, not restatements), so it is not counted as a pair.

`completion-02` is additionally split into two obligations —
`criterion-unchanged-inputs-keeps-stored-rating` and
`criterion-unchanged-inputs-no-judgement-request` — where the second is contained
in the first. That split is defensible on its own (it mirrors the way
`constraint-01` and `constraint-02` separate the two claims); what is wrong is
that neither half then merged with the constraint it restates.

**Attribution: tool defect, already filed as #304** (twin obligations left
unmerged with no diagnostic), a child of #181, the decomposition umbrella. This
matches #304's signature rather than #242's: #242 announces itself with an
`Unreconciled linking answers:` block in the output, and **that block is absent
here** — the failure is silent.

Downstream consequence, measured on #291 and recorded in
`dogfood-logs/291-gate2-run2/judgement.md`: unmerged twins get judged
independently and can land on different ratings over the same tests, so five
duplicate pairs is five chances for a Gate 2 to be non-clean for a reason that is
not about the code.

## Finding 2 — no open questions were raised, which is not a signal (#303)

The run printed no `Open questions:` section, so Gate 1 step 3 ("triage every open
question it raises") had nothing to triage. **This is not evidence that the
mandate was unambiguous.** A requirement's disposition is exactly one of
`yielded` / `open_question` / `no_obligation`, so a requirement that yields an
obligation cannot also raise a question, and the prompt tells the model `yielded`
should be the large majority. The last committed run to print the section is
`dogfood-logs/202-gate1-run{1,2}/`; nothing in the ~30 issues since. Filed as
**#303**. Recorded here as silence, not as a pass.

## Finding 3 — two weak obligations traceable to my wording, not to the tool

Both were found by reading `current-task.md` against the code, not by anything the
tool reported. Both are the sanctioned kind of edit (fix genuinely bad requirement
wording), and both are held for the human's call rather than applied, so that one
reword round produces one re-decompose.

**3a. `constraint-02` / `completion-02` — "costs no evidence-judgement request".**
`judge_discrimination` issues **one batched call** over every criterion with a
mapped test (`src/acceptance/evidence/discrimination.py:206`), so a single carried
criterion removes no request; it is only excluded from the one request that is
made, and the call disappears entirely only when every criterion carries. As
written the obligation is either untestable or invites a test that pins the wrong
thing. Proposed wording: *"A criterion whose requirement text, mapped test set and
mapped test contents are all unchanged is not asked about in the
evidence-judgement request."* This also touches #191, parked on
`191-partition-discrimination`, which splits that batched call.

**3b. `exclusion-04` — "Rejecting a re-judgement that names no change it was
given".** The generated obligation reads *"The change does not reject a
re-judgement that names no change it was given."* That behaviour **already exists**
— #292 built it and it stays — so the obligation asserts something false about the
delivered tree, and only survives on a reading where "the change" means this
task's diff alone. Proposed wording: *"Changing how a re-judgement that names no
change is rejected."* This is the #301 family (scope exclusions receive
inconsistent dispositions in one run), but the fix here is my wording, so it is
not attributed to the tool.

## Dispositions

| Finding | Disposition |
|---|---|
| 1 — five unmerged twin pairs | tool defect, recorded against **#304** (already filed) |
| 2 — no open questions raised | tool defect, recorded against **#303** (already filed) |
| 3a, 3b — two weak obligations | fix `current-task.md`, then re-run Gate 1 — held for approval |

No finding was suppressed and nothing was worked around.
