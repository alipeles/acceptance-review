#!/usr/bin/env bash
# PostToolUse on Edit|Write: auto-format the single Python file that just changed,
# and auto-fix the safe lint findings, so style never becomes a reason to stop.
#
# Deliberately always exits 0. A PostToolUse hook exiting 2 surfaces the problem to
# YOU, which is the opposite of what we want here — real lint failures should be
# caught by the milestone's own acceptance checks, not by an interruption.

set -uo pipefail

INPUT="$(cat 2>/dev/null || true)"
FILE="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"

[ -z "$FILE" ] && exit 0
[ -f "$FILE" ] || exit 0
case "$FILE" in
  *.py) ;;
  *) exit 0 ;;
esac

if command -v ruff >/dev/null 2>&1; then
  ruff format "$FILE" >/dev/null 2>&1 || true
  ruff check --fix "$FILE" >/dev/null 2>&1 || true
fi

exit 0
