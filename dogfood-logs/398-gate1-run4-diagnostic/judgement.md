# #398 Gate 1, run 4 (diagnostic, fresh) — judgement

Run `8ec089ff76154502`, `acceptance decompose --task current-task.md` with **no**
`--continue`, on branch `398-load-dotenv` off main 80511ee. The task file is
byte-identical to run 3's (`dogfood-logs/398-gate1-run3/current-task.md`; not
duplicated here).

Run to tell my wording apart from the carry: a continued run never re-derives a
requirement's obligations from scratch, so it cannot show what the decomposer
makes of the current text.

Output went to `$TMPDIR` and was copied in afterwards. It made 13 live calls
and wrote 4,600 bytes. The three empty logs in this gate were all
live-call runs redirected straight into this Google Drive folder, so this is
the first evidence pointing at the folder rather than at live calls.

11 obligations, 0 open questions. **This is the breakdown taken to Gate 1.**

## Findings

- **exclusion-02 is right on a fresh run:** `no-warning-or-stop-for-mutation-edit-key`,
  *"The change does not add warning or startup-stop behavior for a missing key
  that the coding agent which builds mutation edits needs."* Confirms run 3's
  wrong obligation came from the carry, not the wording.
- **Tool defect reproduces fresh:** `startup-warns-missing-model-keys` again
  drops "In record mode". Second independent derivation, same loss. Filing
  drafted in `docs/DEFERRED.md` under #181.

## Accepted, with the one defect recorded

Every other obligation states its requirement accurately, none is invented and
none is missing: `load-working-directory-env-before-model-call`,
`env-vars-take-precedence-over-dotenv`, `no-dotenv-file-is-allowed`,
`missing-key-preflight-error`, `call-not-sent`,
`invalid-api-key-reply-not-shown`, `no-live-call-no-keys-required`,
`preserve-recorded-transcripts-replay`, `env-loading-stays-working-directory-only`,
`no-custom-env-file-option`. `call-not-sent` and `invalid-api-key-reply-not-shown`
overlap (the second follows from the first) but state different things: the
call, and what the user sees.
