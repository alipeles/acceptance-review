# Decomposition: target design

This document specifies what the decomposition stage must produce and how it
produces it. It is written for two readers: the project owner, who judges
whether the output meets the bar, and the coding agent, who builds it. Sections
1 through 9 are the design. Section 10 is background for the coding agent on
what this replaces; it is not part of the design and can be skipped by anyone
who already knows the current code.

## 1. Purpose

Decomposition turns a change mandate into the set of acceptance criteria a
reasonable human expert would check when the work is declared finished. The set
must be:

- clearly stated, each item a behavior that can be checked;
- aligned to the mandate, nothing invented and nothing material missing;
- unambiguous, or explicitly marked as an open question where the mandate does
  not settle it;
- at the coverage and grain an expert reviewer would expect: enough to confirm
  the requested functionality was delivered and works, and that the probable
  ways it could fail have been prevented.

The acceptance review confirms that the agent delivered what it was asked to.
It is not a code quality review. Items that would normally be caught by code
review or unit testing are not acceptance criteria.

## 2. Terms

Every term below is used with exactly this meaning throughout. Do not introduce
others.

**Mandate.** The task as it was given: a GitHub issue, a Jira ticket, or a task
file. It is the input and it is immutable. The tool never edits it and never
asks for it to be rewritten. The mandate may be in any shape; headings and
structure are hints, never requirements.

**Claim.** One span of the mandate, constructed deterministically from the
parse (a sentence or line, as the parser already splits it), with an id and a
line anchor. A claim is verbatim and carries no semantic label: it is not a
request, a constraint or an exclusion, and it is not split when it says more
than one thing. Claims are an intermediate, not an output: they exist to make
the obligation set traceable and stable across runs.

**Obligation.** One requirement the delivered work must meet, judged by the
downstream stages. An obligation references every claim that supports it (many
claims may support one obligation; one claim may support several). The
obligation is where meaning is assigned: "implement X using subsystem Y" is
one claim supporting two obligations, a request obligation for X and a
constraint obligation that X uses Y. Each obligation carries a type using the
existing type field, which distinguishes requested behavior, constraints and
scope exclusions. An obligation must pass the standard in section 3.

**Expectation.** A behavior the tool believes an expert would expect given the
obligations, but which the mandate does not state. An expectation is not an
obligation. It becomes one only when a clarification confirms it. Every
expectation carries a rationale and references the obligations or claims
that led to it.

**Open question.** Something the tool cannot settle from the mandate: an
expectation awaiting confirmation, or an ambiguity in a stated obligation.
Every open question has an id and is answerable by a clarification.

**Clarification.** An answer to one open question, by id. The clarification
record is append-only and separate from the mandate. A clarification can do
exactly one of three things: confirm an expectation into an obligation,
exclude it, or disambiguate a stated obligation. It cannot restate the mandate
or add obligations that no question asked about.

**Provenance.** Where an obligation's authority comes from. One of:
`stated` (supported by claims in the mandate), `clarified-human` (confirmed or
disambiguated by a human), `clarified-agent` (confirmed or disambiguated by the
coding agent), `inferred` (an expectation; unconfirmed and therefore not yet an
obligation).

## 3. The standard for an obligation

An obligation is anything the mandate asks for, or that the requested work
plainly entails, that an acceptance reviewer would check before accepting the
change. What is excluded is choices the mandate leaves to the builder.

Most obligations are behaviors: observable from outside the change by a
caller, a user, a downstream system, or a file or record the change produces.

Architectural requirements are also obligations when the mandate states them
or the codebase's established structure makes them the only acceptable
answer: reuse an existing subsystem or shared utility rather than duplicating
it, conform to an existing interface, place the work where that kind of work
lives in the system. These are satisfied by code evidence, not tests, in the
same way scope exclusions are: they sit at the static tier and never produce
a test recommendation.

The following are not obligations, even when the mandate mentions them, unless
the mandate makes them an explicit requirement:

- low-level design choices: naming, how a function is factored, use of a
  particular construct or library where the mandate and the codebase leave
  that open;
- general code hygiene: docstrings, type hints, logging, "validate input",
  "handle errors" with no stated behavior behind it;
- tests: a mandate saying "add a test that X" yields the obligation X, not an
  obligation to write a test. The one exception is when a test is itself the
  deliverable, for example a regression test reproducing a reported defect;
- restatements: a second sentence saying the same thing as a first is a second
  claim for the same obligation, never a second obligation.

Failure modes are in scope when they are failure modes of the requested
behavior: what the new feature does on bad input, on a missing dependency, on
a boundary. They are out of scope when they are general robustness concerns
unrelated to what was asked.

Scope exclusions in the mandate are obligations: they require evidence of
absence in the code and no test. They also act as a filter on expectations
(an excluded behavior is never proposed as an expectation).

Gross architectural divergence in the delivered change (building two copies
of a utility in one change, duplicating something the repository already
provides, bypassing an established interface) is not decomposition's
concern. Decomposition does not know the repository well enough to mandate
reuse of a subsystem the mandate never names, and listing everything a
builder should not do is the pedantry this design removes. Such divergence is
a finding about the diff, raised by the coverage stage alongside unrequested
changes, at the static tier. It is out of scope for this document beyond this
note.

## 4. Inputs

1. The mandate, as a file. Any shape. Structure is used when present and
   inferred when absent (section 5, step 1).
2. The clarification record, as a file, possibly empty. Append-only. Each
   entry carries: the question id it answers, the answer, the effect (confirm,
   exclude, disambiguate), who answered (`human` or `agent`), and which
   routing policy produced that responder (section 7).
3. Optionally, a continued run id (the existing `--continue` mechanism). When
   present, the claims from the continued run are carried forward unchanged
   and only the later steps re-run (section 8).

The mandate is never edited by the tool and never edited in response to the
tool. If the mandate changes upstream, that is a new version and is run with
the previous run continued.

All model calls follow the existing invariant: inputs already parsed reach the
model as typed, identified fields, never re-pasted as raw markdown.

## 5. Steps

Each step is a separate model call (or set of calls) with its own schema,
recorded for replay like every other stage. The output of each step is
persisted in review-state so any later step, the report, and the evaluation in
section 9 can inspect it.

**Step 1. Section classification.** For each unit the parser already produces
(heading, paragraph, bullet, line), decide one thing: does it feed claim
extraction or not. Background, motivation, history and references do not;
everything else does. Explicit headings are used when present; the model
decides when they are not. A unit the model is unsure about feeds extraction,
because extracting nothing from a background paragraph costs nothing and
dropping a requirement costs everything. There is no finer classification at
the section level: a single line can carry a request and a constraint, and
that is sorted out at the obligation, not here.

**Step 2. Claim construction.** From the units that feed extraction, construct
claims deterministically: one per sentence or line as the parser splits them,
each with an id and a line anchor, verbatim. No model call and no semantic
label. A claim that says more than one thing stays one claim; it will support
more than one obligation. This is the existing per-line layer, kept because
it is what makes the obligation set traceable and stable across runs.

**Step 3. Synthesis.** From the full set of claims, produce the obligation
set. Each obligation lists the claim ids that support it. This is the step
where meaning is assigned: the model is asked to produce requirements, not to
rewrite claims. Several claims about one behavior become one obligation, and
one claim saying several things becomes several obligations ("implement X
using subsystem Y" becomes a request obligation for X and a constraint
obligation that X uses Y). Synthesis includes what the claims plainly entail,
not only what they say: "a CRUD interface for X" entails delete, and delete
becomes an obligation supported by that claim with no question asked. The
test for "plainly entails" is that the model can defend the obligation from
the claim alone; anything it cannot is left for step 5. Each obligation
carries a type using the existing type field (requested behavior, constraint,
scope exclusion). Provenance is `stated`.

**Step 4. Pruning.** Apply the standard in section 3 to every obligation.
Each is kept or dropped with a one-line reason naming which rule applied.
Dropped obligations are retained in review-state with their reason; they are
not shown as obligations downstream but are available to the report and to
evaluation. Pruning happens before questions are raised so that no question
is ever asked about a pedantic item.

**Step 5. Expectations and ambiguities.** Given the surviving obligations and
the claims, the model is asked two things as an expert reviewer:

- What would you expect to be true of this work that these obligations do not
  cover? Each answer is an expectation with a rationale in plain language and
  references to the obligations or claims that prompted it. By construction
  these are the things the tool could not defend from the mandate in step 3;
  that is why every one of them is a question rather than an obligation. There
  is no catalogue of patterns; the rationale is free text. Expectations must be
  phrased as acceptance criteria, not implementation decisions ("the date
  calculations in requirements A, B and C agree with each other", not "date
  logic is centralized"). An architectural expectation that depends on what
  the repository already contains is phrased conditionally ("if the platform
  already has a day count utility, this change uses it rather than adding
  one"), and the coverage stage settles the condition against the repository
  and the diff. Giving this step a view of the repository is a possible later
  change, not part of this design.
- Which surviving obligations are ambiguous, and in what way? Each answer is
  an ambiguity attached to the obligation.

Every expectation and ambiguity becomes an open question with an id.
Scope-exclusion obligations filter expectations: nothing excluded is proposed.

**Step 6. Omission check.** A separate call, with a different question from
step 3: given the mandate's claims and the current obligation set plus
expectations, what does this set miss? Any additions go through steps 4 and 5.
The check repeats until it adds nothing, with a hard cap of two passes. This
replaces re-running decomposition from scratch to find missed items.

**Step 7. Clarification intake.** Read the clarification record. For each
entry, apply its effect:

- `confirm`: the expectation becomes an obligation with provenance
  `clarified-human` or `clarified-agent` according to who answered;
- `exclude`: the expectation is closed and recorded as excluded, with
  responder;
- `disambiguate`: the obligation's text is revised per the answer and its
  provenance becomes `clarified-human` or `clarified-agent`; the original text
  and claims are retained.

Open questions with no clarification remain open.

**Step 8. Residual deduplication.** Run the existing pairwise deduplication
over the final obligation set. With synthesis in step 3 this is expected to
find little; it stays as a backstop and its merge count is reported.

## 6. Outputs

Review-state holds, for the run:

- the per-unit extraction decision (step 1), claims (step 2);
- obligations, each with: text, type, provenance, supporting claim ids, and if
  clarified, the question id and the original text;
- dropped obligations with reasons (step 4);
- expectations and ambiguities, each with: id, text, rationale, references,
  status (open, confirmed, excluded) and if answered, responder and policy;
- omission-check passes and what each added (step 6);
- dedup merges (step 8).

The rendered report shows:

- obligations grouped by provenance, with `clarified-agent` called out
  explicitly: "N obligations rest on clarifications the builder supplied";
- open questions still open, each with its rationale;
- expectations excluded, with responder;
- a one-line count of dropped obligations with a pointer to the detail.

Downstream stages (mapping, evidence, verdict) operate only on obligations.
Expectations that remain open are never mapped or judged; they appear in the
report as open questions. The verdict reports provenance counts so a clean
verdict resting mostly on agent-supplied clarifications is visible as such.

## 7. Interaction: answering questions

Open questions are meant to be answered during the coding agent's session,
not at a separate gate.

The tool provides two commands (names to be settled by the coding agent within
the existing CLI conventions):

- list the open questions for a run, with id, text, rationale and whether each
  is a scope question or an implementation question (the model labels this in
  step 5);
- append a clarification: question id, effect, answer text, responder, policy.

A routing policy says which responder handles which class of question. The
default is: scope questions (is behavior X in or out; must A and B agree)
go to the human; implementation questions (how, where, which approach) are
answered by the agent. The coding agent may hold and adjust the policy on the
user's instruction. Whatever the policy, every clarification records who
actually answered, and the report discloses it. The tool never answers a
question itself.

Nothing here requires a hosted service. The clarification record is a local
file, and the commands run locally.

## 8. Stability across runs

Claims are the stable layer. On a continued run, claims from the previous run
are carried forward unchanged unless the mandate itself changed, in which case
only claims for changed lines are re-extracted. Steps 3 onward re-run.

The difference between two runs' obligation sets over the same claims is the
instability measure for synthesis and is reported when a run is continued:
obligations added, removed, or reworded, each with its supporting claim ids
so the cause can be seen.

Determinism rules are unchanged: same inputs, same model, same seed, byte
identical output.

## 9. Evaluation

Correctness is judged on real mandates, not on task files written for the
tool. The sample is drawn from GitHub issues as they stand, unedited, from the
job-search CRM repository, with a few of this repository's issues for range.

For each mandate the evaluation page shows the obligation set and the open
questions, with a confirm/disagree toggle on every item defaulted to the
tool's output. The owner labels:

- each obligation as one of: real acceptance criterion, restatement, code
  quality, wrong;
- each expectation and ambiguity as: useful, not useful, wrong;
- anything missing, added as free text.

Scores: precision of obligations (share labelled real), recall against the
owner's additions, and the useful share of questions. The missing column is
the one the tool cannot measure itself and is the primary signal.

This evaluation is built after the pipeline, using the existing labeling page
with the sample changed. No labelled data is needed to start implementation.

## 10. Background for the coding agent: what this replaces

This section exists only so the coding agent can find and remove what the
design supersedes. It is not part of the design.

- Obligations are currently produced directly by per-line extraction, so they
  read as restatements of the mandate's sentences and deduplication carries
  the load of merging them. Under this design that extraction produces claims
  (step 2) and obligations come from synthesis (step 3).
- There is currently no pruning step; code-quality and implementation-detail
  items reach the obligation set and the downstream stages.
- Open questions are currently anchored to lines. Expectations (step 5) have
  no line; they reference obligations and claims instead. The review-state
  schema needs a reference type that allows this.
- `CLAUDE.md`'s Gate 1 procedure sanctions rewriting weak wording in
  `current-task.md` and describes task-file authoring style. Under this
  design the mandate is immutable: `current-task.md` becomes a copy of the
  issue as filed, the weak-wording rewrite becomes a clarification, and the
  task-file style guidance is removed. Gate 1 and Gate 2 procedures and the
  working agreement need a corresponding edit, which is a separate task.
- Decomposition is currently re-run from scratch to catch missed items. Step 6
  replaces that with an omission check over the existing set.
- The existing `--continue` mechanism carries the obligation set forward.
  Under this design it carries claims forward and re-synthesizes (section 8).

Not decided, deliberately: a catalogue of change patterns (rejected for now; the
rationale in step 5 is free text), a "pedantic mode" that lowers the pruning
bar, and whether `clarified-agent` obligations should weigh differently in the
verdict beyond being reported.
