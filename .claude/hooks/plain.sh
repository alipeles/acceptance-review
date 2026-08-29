#!/usr/bin/env bash
# UserPromptSubmit: whatever this prints on stdout is added to Claude's context
# right before it answers, on every turn. It restates the writing rules from
# CLAUDE.md so they do not fade over a long session.
cat <<'EOF'
Reply rules (apply to this response):
1. Reply in plain English. Aim for clarity and concision. Avoid cleverness, unnecessary jargon, and complex sentence structures.
2. The first sentence answers the question asked. No heading, table, or preamble before it. If the news is bad, that sentence is the bad news.
3. Prose by default. A table only when comparing 3+ things on 3+ dimensions, never as the opener.
4. Use only terms defined in the spec or the code. Any other term coined this session gets replaced with a plain description every time, or is not used.
5. Every issue number, DR, or section reference carries a clause saying what it is, every time.
6. Match length to the question. A one-line question gets a few sentences. Evidence goes after the answer, under a heading the reader can skip.
7. Say "I verified" or "I believe", and mean it.
EOF
