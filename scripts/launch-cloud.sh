#!/usr/bin/env bash
# Start one Claude Code cloud session per line of a batch file.
#
# Usage, from the repo root, on main, after the command files are pushed:
#   scripts/launch-cloud.sh scripts/batch-1.txt
#
# Batch file format: "<issue> <files>" per line, files comma-separated with no
# spaces. The files are the ones that issue is expected to edit. They are not
# a limit on that session; they are what every OTHER session in the batch is
# told to keep its hands off, so two branches never change the same file.
# Blank lines and lines starting with # are ignored. "289,290" is one issue.
#
# Each `claude --cloud` call creates its own session from the GitHub remote at
# the branch you are currently on, so be on main and pushed before running.

set -u
batch="${1:?usage: $0 <batch file>}"

if [ "$(git branch --show-current)" != "main" ]; then
  echo "you are on '$(git branch --show-current)'; switch to main first" >&2
  exit 1
fi
if [ -n "$(git status --porcelain .claude/commands scripts)" ]; then
  echo "uncommitted changes under .claude/commands or scripts; commit and push first" >&2
  exit 1
fi

lines="$(grep -Ev '^\s*(#|$)' "$batch")"

echo "$lines" | while read -r issue files; do
  # Reserved = every file claimed by a different line of the batch.
  reserved="$(echo "$lines" | awk -v me="$issue" '$1 != me {print $2}' \
              | tr ',' '\n' | sort -u | paste -sd, -)"
  [ -z "$reserved" ] && reserved="none"
  echo "launching #$issue (reserved: $reserved)"
  claude --cloud "/fixbug-cloud $issue $reserved"
  sleep 5
done

echo
echo "Sessions are listed at https://claude.ai/code. Each pushes a branch"
echo "named <issue>-headless when it finishes. Nothing is merged."
