# Environment notes: sandbox, git, gh, and permission prompts

Moved out of `CLAUDE.md` on 2026-08-29 so the top-level file stays short enough
for its instructions to be followed. Everything here is still true and still
applies; it is reference material for when a command fails or prompts, not
something to read at session start. The short rules that matter every session
are summarised in `CLAUDE.md` under *Commands*.

**`ruff check .` matches CI only when the venv matches the pin.** `pyproject.toml`
pins `ruff==0.16.2`; an older ruff has a smaller default rule set and prints
*"All checks passed!"* on a tree CI rejects. That kept `main` red for four
commits — lint is a build step, so the whole `test` job died in ~25s before a
test ran, blocking another session's PR. When the pinned version was finally
installed there were **three** findings where the local run had reported none,
and one of them was code written minutes earlier on the branch. Check with
`.venv/bin/ruff --version`; `pip install -e ".[dev]"` needs the sandbox off,
because it hits the same TLS wall as `gh`.

Other subcommands: `decompose`, `diff`, `classify`, `recommendation`.

**GitHub goes through the MCP tools, not `gh`.** The `mcp__github__*` tools run
in-process, so they touch neither the sandbox, the macOS keyring, nor TLS
verification — the three walls that make `gh` need an escape hatch (below). They
also have no local git side-effects: `gh pr merge --delete-branch` failed during
#264 with `'main' is already used by worktree`, because the CLI tries to move the
local checkout. The MCP call does not.

| want | use |
|---|---|
| read a task | `issue_read` (`method: "get"`) |
| comment on an issue | `add_issue_comment` |
| file an issue / attach a sub-issue | `issue_write`, `sub_issue_write` |
| read a PR, its diff, its comments | `pull_request_read` |
| **is CI green?** | `pull_request_read`, `method: "get_check_runs"` |
| open a PR | `create_pull_request` |
| merge | `merge_pull_request` (then delete the branch separately) |

Two things this deliberately does NOT change:

- **The approval boundaries stay where they were.** `issue_write`,
  `sub_issue_write` and `add_issue_comment` are allowlisted and file without a
  prompt, exactly as `Bash(gh *)` did — so *Working agreement* §4's review-then-
  file rule is still the only rail, not a permission dialog. `create_pull_request`
  and `merge_pull_request` are **not** allowlisted, so opening a PR and merging
  still stop for a human (§3).
- **A comment body is a parameter, not a file.** No `-F <file>` and no heredoc;
  write the text straight into the call.

**`gh` survives for one job: watching CI in the background.** `Monitor` runs a
shell command and shell cannot call an MCP tool, so a background CI watch still
shells out to `gh pr checks` — and therefore still needs the escape hatch. For a
one-off "is it green yet", prefer `get_check_runs`.

**Sessions start sandboxed.** `sandbox.enabled` is on by default in user
settings, with `autoAllowBashIfSandboxed`, so a sandboxed Bash call runs without
a prompt. Everything above works inside it. Two things follow:

- **Do not reach for `dangerouslyDisableSandbox` as a first move.** It is for a
  command that demonstrably failed *because of* a sandbox restriction —
  "Operation not permitted", a blocked host, a write outside the allowed paths.
  A command can fail for a hundred other reasons, and disabling the sandbox to
  find out costs the protection and answers nothing.
- **The sandbox is what makes the shapes below free.** Auto-allow applies to
  sandboxed commands, so a compound command that has to leave the sandbox pays
  twice. The habits list is not a style preference; it is the difference between
  a call that runs and a call that stops for a human.

**`.env` at the repo root and `pytest` collide, and the fix is a deletion.**
`pytest` stats the repository root while computing its rootdir, so a
`Read(.env)` deny rule makes the sandbox refuse the stat and **the entire suite
fails to collect** — `PermissionError`, zero tests, before anything runs. The
rule was removed for exactly this reason. Claude Code's built-in secret-file
protection still covers the file, so an explicit read or a command naming `.env`
still prompts; what changed is that the block moved off the sandbox's filesystem
layer, where it was catching an unrelated stat. **Do not re-add
`Read(.env)`/`Read(.env.*)` to `.claude/settings.json`** without re-testing
`.venv/bin/pytest -q --collect-only` inside the sandbox.

**`gh` cannot run inside the sandbox on macOS, and `sandbox.excludedCommands` is
not currently rescuing it.** This is why the MCP tools above are the default and
`gh` is reserved for background CI watching. Measured 2026-08-20: it hits
**three** independent walls, and clearing one only reveals the next.

1. **Its config.** `open ~/.config/gh/config.yml: operation not permitted` — the
   project's `permissions.deny` carries `Read(~/.config/gh/**)`, and a `Read()`
   deny is merged into the sandbox's filesystem `denyRead`. Fixed in **user**
   settings with `sandbox.filesystem.allowRead: ["~/.config/gh"]`, which takes
   precedence over `denyRead`. The `Read()` deny still stands, so the *Read tool*
   cannot open the token — only the `gh` binary can. That is the split you want,
   and it hot-reloads without a restart.
2. **Its token.** `The token in keyring is invalid` — the token lives in the
   macOS keyring, which the sandbox blocks. Same family as the harmless
   `failed to store: 100001` that `git fetch` prints.
3. **TLS.** `tls: failed to verify certificate: x509: OSStatus -26276`, because
   verification goes through `com.apple.trustd.agent`.

`excludedCommands: ["gh"]` is set in **both** the project and user settings and
**still does not take effect** — walls 2 and 3 are exactly what an excluded
command would never hit. Until that is resolved, **`gh` needs
`dangerouslyDisableSandbox`, and you should say so rather than escaping
silently.** Do not reach for `sandbox.network.enableWeakerNetworkIsolation`: it
would clear only wall 3, leave the keyring blocked, and weaken every other
sandboxed command.

**`git` is NOT unaffected — but the branch operations are fixable, and the fix
is a flag, not an escape.** `git branch` and `git worktree add` die with
`could not lock config file .git/config: Operation not permitted`, because the
sandbox protects `.git/config` (it can carry `core.sshCommand`, `core.pager` and
aliases, so writing it is arbitrary code execution). What wants to write it is
the **upstream tracking configuration**, not the branch itself, so `--no-track`
removes the need entirely. Both of these run clean sandboxed:

```bash
git branch --no-track tmp origin/main
git worktree add --no-track -b <branch> <path> origin/main
git switch --no-track -c <branch> origin/main     # the one-step form
```

The throwaway-branch push above uses `--no-track` for this reason. `git fetch`,
`push`, `add`, `commit` and the read-only subcommands were always fine.

**`git switch -c` / `-C` without the flag is the trap, and it fails worse than
the others.** `git branch` refuses and changes nothing; `git switch -C` **creates
the branch, then fails setting up tracking**, leaving the index holding the new
branch's tree while `HEAD` still points at the old one. Two consequences, both
seen: `git status` shows main's whole tree as staged changes, and the obvious
retry hits `fatal: a branch named X already exists` because the first attempt
already made it.

Recover in this order, because the middle step is destructive:

```bash
cp <your uncommitted files> "$TMPDIR"/     # reset --hard discards them
git reset --hard HEAD                      # back to a sane state; untracked files survive
git switch --no-track -c <branch> origin/main
```

Verified sandboxed: `--no-track` exits 0 with no config write, and deleting such
a branch afterwards is also clean — there is no tracking entry to remove, so
`git branch -D` stops emitting `warning: update of config-file failed`.

**`git branch -m` prints `fatal:` and still succeeds.** Renaming reports
`fatal: branch is renamed, but update of config-file failed`, which reads like
the rename was rolled back. It was not — the branch is renamed; only the config
update failed, and with `--no-track` there was nothing in it to update anyway.
Check with `git branch --show-current` rather than believing the word `fatal`.

**Do not try to "fix" this by allowing writes to `.git/config`.** The protection
is deliberate and the file is an arbitrary-code-execution vector; `--no-track`
removes the need for the write rather than working around the guard. Probed to
be sure: `.git/probe.tmp`, `.git/foo.lock` and `.git/config2` all write fine, and
`.git/config` and `.git/config.lock` are both refused — the rule is specific to
git's config, not to the `.git` directory or to lock files.

**A branch operation that rewrites `.claude/settings.json` fails inside the
sandbox**, because the sandbox protects that file from writes. `git rebase`,
`switch` and `checkout` all die with `unable to unlink old
'.claude/settings.json': Operation not permitted` — and worse, the checkout is
**partway done** when it fails, so the working tree is left holding the other
branch's content while `HEAD` still points at yours. That looks alarming and is
harmless: nothing is lost, both sides are committed somewhere. Recover with
`git checkout -- .`, then re-run the operation with the sandbox off. Only an
issue when a commit on either side touches that file.

**Habits that cost permission prompts and buy nothing.** Measured across 25
transcripts (3,324 unique Bash calls); together they outnumber every genuinely
missing allowlist rule. The allowlist is close to complete — **prompts are caused
by command *shape*, not by missing vocabulary.**

- **Don't `source .venv/bin/activate`** — 385 occurrences. The `.venv/bin/*` entry
  points above are allowlisted and `source` is not, so activating costs a prompt
  and then changes nothing.
- **No heredocs at all** — 107 occurrences of `cat > f <<'EOF'`. Use the `Write`
  tool; edits are already allowed. Heredocs defeat segment matching, so the whole
  call prompts. **This is about the `<<` shape, not about `cat`**, so
  `.venv/bin/python - <<'PY'` prompts exactly the same way despite
  `Bash(.venv/bin/python *)` being allowlisted — write the script to the
  scratchpad and run it by path. `git commit -F -` is the one worth keeping: it
  is the only way to write a multi-paragraph message, and one prompt per commit
  is a fair price.
- **One command per call. Don't batch.** This is the big one: **63% of Bash calls
  would prompt**, and compound shapes account for 32 of the 34 recorded Bash
  denials. A compound command is only as permitted as its least-permitted
  segment, so batching `echo "=== label ===" && cmd` turns N allowed calls into
  one prompt. Round-trips are cheap; prompts are not. Independent calls issued in
  one message run in parallel anyway — that is the way to batch.
- **Need a different directory? Use a subshell: `(cd <dir> && <cmd>)`.** The
  matcher decomposes it and `cd` is auto-allowed, so `(cd <worktree> && .venv/bin/pytest -q)`
  matches the existing `.venv/bin/*` rules, and the `cd` cannot leak into the next
  call. `git -C <dir>` is fine for *read-only* subcommands (built-in git detection
  handles it); mutating ones need an explicit rule, because every plain `git *`
  rule assumes the subcommand comes first. `add` and `commit` have one —
  **patterns may wildcard mid-string**, as `Bash(git -C * add *)`, so any further
  gap of that shape is one line. Never write a bare `Bash(git -C *)`: it would
  swallow `push` and `merge`, which must keep prompting (*Working agreement* §3).
  Absolute tool paths miss too. `pytest` is worse than either: `addopts = "--ignore=tests/fixtures"`
  and `pythonpath = ["."]` are cwd-relative, so driving it by absolute path
  *silently collects the archetype fixtures as suite tests* and errors.
- **Never name `.env` in a command.** Secret-file protection overrides the
  allowlist, so `ls -la .env` prompts even though `Bash(ls *)` is allowed — and
  inside a batch it blocks every other segment with it. Use `test -f .env && echo
  present`.
