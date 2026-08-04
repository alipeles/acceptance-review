# Judgement — #167 Gate 2, run 1 (`07075a6`)

Verdict: **INCOMPLETE**. 2 of 12 obligations below `strongly supported`.

| obligation | rating | my judgement | disposition |
|---|---|---|---|
| `replace-written-file-with-command` | `unsupported`, **no mapped test** | **Partly tool, partly real.** A compound umbrella obligation ("replace the file WITH the command surface, defaulting to JSON") whose constituents the other 11 obligations already cover individually — a #144-shaped decomposition artifact, and the mapper reasonably preferred the specific obligations. But its *"defaulting to JSON"* clause appears in no other obligation, and I tested that only implicitly (a test that happened to `json.loads` the output). | **Addressed** — added `test_json_is_the_default_format_when_none_is_requested`, stating the guarantee by name. |
| `fixed-command-surface` | `nominally supported`, mapped to `test_check_rejects_unknown_mode` and `test_check_requires_all_flags` (both irrelevant) | **Real.** #167 fixed the command surface up front precisely so the spec could name it; nothing pinned the spec string to the parser, which is the drift this task exists to prevent. The two mapped tests are unrelated — mapping noise on top of a genuine gap. | **Addressed** — added tests pinning the documented command string to the parser, plus rejection of undocumented command names, missing `--criterion`, and unknown `--format`. |

**Outcome:** both rose to `strongly supported` in run 2. The fixes worked.

**Retrospective (added after run 3):** run 1 rated
`default-to-most-recent-review` **`strongly supported`** while its only test
stored a *single* review — a test that could not distinguish "the newest" from
"the only one". Run 2 correctly flagged it. So run 1's STRONG here was a **false
negative**: the rating was wrong, not merely unstable.
