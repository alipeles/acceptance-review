#!/usr/bin/env bash
# Start one Claude Code cloud session per line of a batch file.
#
# Usage, from the repo root, after the command files are pushed to main:
#   scripts/launch-cloud.sh scripts/batch-1.txt
#
# Batch file format: "<issue> <owned file>" per line; blank lines and lines
# starting with # are ignored. "289,290" is passed through as one issue.
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

grep -Ev '^\s*(#|$)' "$batch" | while read -r issue owned; do
  echo "launching #$issue ($owned)"
  claude --cloud "/fixbug-cloud $issue $owned"
  sleep 5
done

echo
echo "Sessions are listed at https://claude.ai/code. Each pushes a branch"
echo "named <issue>-headless when it finishes. Nothing is merged."
