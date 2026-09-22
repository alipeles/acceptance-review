# The judging pass, as it is given to the judge

`docs/audit-protocol.md` defines the categories and what they mean. This file is
the other half: the exact instructions handed to the judging pass, so a later
audit is judged the same way rather than by whatever was typed that day. It is
apparatus, like `run_audit.py` beside it, and nothing in `src/` reads it.

Two properties are load-bearing and easy to lose:

- **The judge never sees what the verifier concluded.** The judging pass is the
  ground truth the edit verifier is measured against, so `run_audit.py` writes
  `verified`, `verification_reason` and `refused_by` to the attempts JSON and
  never to the Markdown handed over here.
- **The judge runs no tests.** The categories are about what an edit means, not
  about what happened when it ran.

## The instructions

> You are judging a defect-injection audit. Work read-only. Run nothing.
>
> Read `<audit markdown>`. It has one section per defect, each carrying the
> defect's two behaviours — what the code must do (`expected`) and what it would
> do instead (`defective`) — and the edit that was made, as a diff.
>
> For every section, decide what the edit did, judging it **against those two
> behaviour fields and the source at revision `<revision>`**, checked out
> read-only at `<source worktree>`. Judge against the behaviours, never against
> the defect's prose description.
>
> Give each edit **exactly one** category:
>
> - `injects` — after the edit the code does the defective behaviour, and before
>   it did the expected one. A plausible small mistake. This is the only
>   category that makes the run's result evidence.
> - `backwards` — the code already did the defective behaviour and the edit
>   moves it toward the expected one, so a test failing afterwards is catching a
>   repair.
> - `unrelated` — the edit changes behaviour, but not the behaviour the defect
>   names. This includes an edit that changes nothing observable.
> - `overbroad` — the edit makes the defect true and also breaks much more: it
>   crashes, disables a whole feature, or refuses everything, so a kill is
>   credited for the wrong reason.
> - `unclear` — it cannot be decided from the diff and the source. Use it; a
>   guess is worse than an admission.
>
> Separately, for the same edit, answer whether it **changes the code's
> behaviour at all**: `true`, `false`, or `null` when you cannot tell. `false`
> means the edited code does exactly what the original did for every input — an
> always-true condition, a value nothing reads, a reordering with no effect —
> even though the text differs by more than comments and whitespace. This is a
> different question from the category, and an `unrelated` edit may answer either
> way.
>
> For a section whose outcome is `already_present`, the model claimed the code
> already has the defect. Record two things instead of a category: whether the
> claim is `right` or `wrong`, and whether the repair edit shown `repairs`, `does
> not repair`, or is absent (`no repair`).
>
> For a section whose outcome is `not_mutable` or `no_usable_edit`, no edit was
> used. Record the outcome, and where a refused candidate edit is shown, say
> whether refusing it was correct — a refused edit that would have injected its
> defect is a cost of the check and must be visible.
>
> Give every judgement a one-sentence reason **naming the lines that decided
> it**. A reason that does not name lines is not usable.
>
> Return JSON only, in this shape:
>
> ```json
> {"labels": [
>   {"defect_id": "...", "outcome": "killed",
>    "edit": "injects", "changes_behaviour": true,
>    "reason": "... src/acceptance/x.py:120-124 ..."},
>   {"defect_id": "...", "outcome": "already_present",
>    "claim": "right", "repair": "repairs", "reason": "..."},
>   {"defect_id": "...", "outcome": "no_usable_edit",
>    "refusal_correct": true, "reason": "..."}
> ]}
> ```

## After the pass

The result is saved as `labels/<audit>.json` with the header fields the other
label sets carry (`audit`, `source`, `revision`, `descriptor_model`,
`protocol`), and then:

1. **Hand-check a sample**, prioritising any edit where this audit and v8
   disagree on the same defect, and record in the judgement which entries were
   checked. The protocol requires this because a judging pass called an edit
   `overbroad` in v7 that v8 called `injects` on the identical diff.
2. Run `score_audit.py` over the labels and the attempts to derive the rates.
   Nothing is counted by hand.
