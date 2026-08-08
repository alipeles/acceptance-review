#!/usr/bin/env bash
# Fires on Notification (Claude needs input / permission) and on Stop (turn finished).
# Sends a macOS notification, and optionally a phone push via ntfy.sh.
#
# Phone push: pick an unguessable topic, subscribe to it in the ntfy iOS/Android app,
# then export it in your shell profile:
#   export CLAUDE_NTFY_TOPIC="aaron-cc-7f3ab9"
# Leave it unset to keep notifications desktop-only.

set -uo pipefail

MODE="${1:-attention}"
INPUT="$(cat 2>/dev/null || true)"

# The repo/worktree name is the useful identifier when several sessions run at once.
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
[ -z "$CWD" ] && CWD="$PWD"
WHERE="$(basename "$CWD")"

MSG="$(printf '%s' "$INPUT" | jq -r '.message // empty' 2>/dev/null)"

if [ "$MODE" = "done" ]; then
  TITLE="Claude finished — $WHERE"
  BODY="${MSG:-Turn complete. Ready for you.}"
  PRIORITY="low"
  SOUND="/System/Library/Sounds/Tink.aiff"
else
  TITLE="Claude needs you — $WHERE"
  BODY="${MSG:-Waiting on input or permission.}"
  PRIORITY="high"
  SOUND="/System/Library/Sounds/Glass.aiff"
fi

# --- macOS desktop notification ---------------------------------------------
if command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"${BODY//\"/\\\"}\" with title \"${TITLE//\"/\\\"}\"" >/dev/null 2>&1 || true
fi
[ -f "$SOUND" ] && command -v afplay >/dev/null 2>&1 && afplay "$SOUND" >/dev/null 2>&1 &

# --- optional phone push -----------------------------------------------------
# Uses curl, which is denied to Claude by permission rules but is fine here:
# hooks run as you, outside the permission system.
# Runs in the FOREGROUND deliberately. Backgrounding it with `&` loses the push:
# the script exits immediately afterwards and the in-flight request is killed with
# the process group before it completes. --max-time keeps it inside the hook's
# 10s timeout, and stderr is left intact so a failure is visible rather than silent.
if [ -n "${CLAUDE_NTFY_TOPIC:-}" ] && command -v curl >/dev/null 2>&1; then
  curl -fsS --max-time 5 \
    -H "Title: $TITLE" \
    -H "Priority: $PRIORITY" \
    -H "Tags: robot" \
    -d "$BODY" \
    "https://ntfy.sh/${CLAUDE_NTFY_TOPIC}" >/dev/null || \
    echo "notify.sh: ntfy push failed (exit $?)" >&2
fi

exit 0
