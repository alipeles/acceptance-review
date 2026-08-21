# Judgement — #317 Gate 1, run 3 — **Gate 1 PASSED**

*Run at `a10cdc0` on branch `317-disposition-union`, 2026-08-21.*

```
.venv/bin/acceptance decompose --task current-task.md --continue b35e72704d1fc4f9
```

Exit 0. Run id `40c12c90018b3526`. 20 requirements, 19 with obligations, 1
deliberately none. `output.log` was non-empty first time — the zero-byte problem
that hit runs 1 and 2 did not recur.

**This supersedes run 2's PASSED marking.** Run 2 was defensible on coverage and
I said so, but re-reading its breakdown found a contradiction in the mandate
that run 2's judgement had missed. Run 3 is the breakdown Gate 1 passes on.

## What run 2's breakdown exposed in my own mandate

Two obligations from run 2 describe the same mechanical condition and demand
opposite things about it:

| obligation | from | says |
|---|---|---|
| `disambiguate-colliding-obligation-identifiers` | constraint-03 | two obligations sharing an identifier are **made distinct** |
| `stop-on-differently-stated-shared-obligation` | constraint-06 | agreeing accounts stating one shared obligation differently **stop the review** |

"A shared obligation stated differently" is two obligations with the same
identifier and different content — exactly the collision constraint-03 says to
disambiguate. Nothing in the data can tell the two cases apart, because
obligation identifiers are minted by the tool and `_unique` already renames
collisions, so there is no notion of a shared obligation across two accounts.
The mandate asked for both behaviours on one input.

It was also **scope I invented**. Issue #317's Acceptance asks only that "copies
whose `disposition` values differ still raise". The shared-obligation rule was
mine, added while writing the task file, and it went beyond the issue.

Both bullets were removed — constraint-06 and its completion expectation. This
is the sanctioned rewrite of weak requirement text, and the gate's re-arm rule
is why this run exists.

**The decomposer did not flag the contradiction.** It rendered both bullets
faithfully as separate, well-formed obligations and raised no open question
about them — which, per **#303**, it is structurally unable to do for a
requirement that also yields obligations. So the catch came from reading the
breakdown, which is what step 2 of Gate 1 is for. Worth recording as a limit on
what a clean-looking decomposition proves: consistency *between* obligations is
not something this stage checks.

## The carry behaved exactly as #269 designed it

**0 derived, 20 carried, 0 revised, 0 decompose calls.** A pure deletion cost
nothing. The run named what it dropped rather than silently shrinking:

```
REMOVED constraint-06: … (1 obligation(s) dropped)
REMOVED completion-07: … (1 obligation(s) dropped)
```

Requirement ids after the deletion shifted up — the old `constraint-07` is now
`constraint-06` — while obligation ids did not: `single-account-unaffected` kept
its identity across the renumbering. That is carry keyed on requirement *text*
rather than positional id, working. One live obligation-linking call was issued
because the obligation set changed; decomposition itself was not re-asked.

## The two known defects are unchanged, and still not re-filed

Both persist exactly as run 2 recorded them, and neither is fixable by further
rewording:

1. `task-01` still yields `combine-agreeing-accounts-2`, a duplicate of
   `constraint-01`'s `combine-agreeing-accounts` with the same generated slug and
   no merge, while `disagreement-stops-review` merges correctly across `task-01`
   and `constraint-05` in the same run. Twin-splitting family — #304, #242, and
   the open blocker in `docs/DEFERRED.md`, which now carries this instance.
2. `exclusion-01`'s obligation is still the malformed prohibition "The review
   does not let an unreadable answer stop the whole review or only the
   requirements that answer was asked about", byte-identical across a rewording
   of its requirement. Recorded as a drafted follow-up comment on #301.

## The breakdown I would defend

Nineteen obligations. The six that define the work:

| obligation | property |
|---|---|
| `combine-agreeing-accounts` | agreeing accounts of one requirement are combined into one |
| `preserve-all-obligations-in-combined-account` | the union states every obligation, in returned order, dropping none |
| `disambiguate-colliding-obligation-identifiers` | colliding ids are made distinct, as they already are elsewhere |
| `record-that-combining-happened` | the combine is recorded, naming the requirement, not silent |
| `disagreement-stops-review` | accounts disagreeing about the outcome still stop the review |
| `single-account-unaffected` | a requirement accounted for once is untouched |

Plus five scope exclusions, seven test demands, one determinism obligation, and
`Implementation.` correctly disposed as yielding none. Nothing real is missing;
the two wrong obligations are the known defects above, and neither touches the
six.

## Open questions: none, and it still means nothing

Zero across all three runs, for the #303 reason. The gate's three-case triage
has nothing to apply to.
