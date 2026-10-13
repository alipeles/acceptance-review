# Task

Add a third way of building a mutation edit: drive a headless coding agent over a
copy of the project and ask it for what the one-call builder is asked for — the
smallest edit that makes one named defect true. Claude Code is the first agent it
can drive. The agent is chosen by a setting, and supporting another agent, such
as Codex, means adding that agent's adapter without changing the builder.

The agent builder is a fallback, never the first attempt. It is asked about a
defect only when every candidate the existing builder produced for that defect
was set aside, and only when it has been configured; with nothing configured a
review behaves exactly as it does today.

What the agent changed in the copy is reduced to one span replacement in one
file and then goes through every check any other candidate goes through, before
and after it is run against the tests. If what it changed is not a single
contiguous edit inside a region the defect names, the candidate is set aside
rather than repaired. An unverified agent edit carries no more weight in the
review than any other unverified edit.

The copy the agent works in has the project's test files removed, so it cannot
read them whatever it is told or decides to do.

What a run records is the agent's diff, not its transcript. A replayed review
reuses the recorded diff without starting the agent, and two replays of the same
input are byte-identical. A run that exceeds its time limit, fails, or changes
nothing yields no usable answer.

Each defect sent to the agent records what the attempt cost in dollars and how
long it took on the wall clock, next to the same figures for the one-call
builder's attempts at that defect, so the two can be compared.

## Scope exclusions
- An adapter for Codex or for any agent other than Claude Code.
- Making the agent builder the first attempt or the default.
- A command-line option for the setting.
- Changing the existing builder's prompt or the number of candidates it is asked for.
