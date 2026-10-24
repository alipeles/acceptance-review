# 413 Gate 2, run 2 — judgement

Continuing run 1 (`ea62a34bb02a6166`) after its findings were fixed. $1.17 on 121
live calls, 44 replayed.

Verdict INCOMPLETE. Not clean, one finding.

The three obligations run 1 reported as not addressed or unclear (replay without
a live call, byte-identical reruns, the typed error) are now addressed and
strongly supported, after their tests moved onto `DEFAULT_MODEL`. The provenance
obligation is strongly supported. No unrequested changes.

## Finding

**`prompt-test-assertions-hold-on-claude-answers`, partially supported (4 of 5)**
— real. The planted bug that survived is
`assertions-weakened-to-pass-on-claude`. Its recommendation asks for a
deliberately wrong answer that a faithful assertion rejects and a loosened one
lets through. That is exactly what the two strict xfails removed in this change
used to prove. Fixed by pulling each check into a helper and adding
`test_the_preservation_check_still_catches_the_reframing_gpt_5_4_mini_gave` and
`test_the_framing_check_still_catches_the_duplicate_gpt_5_4_mini_gave`, which
rebuild the gpt-5.4-mini answer from Claude's own. I verified each by breaking its
helper: only the new test failed, and the original one still passed.
