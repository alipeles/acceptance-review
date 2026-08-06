# Decision Record 202 — Decomposition as a requirement mapping

*Relates to issue #202 and the #181 umbrella (decomposition). Status: **accepted,
not built**. Track: checker. Stage: 1, with decomposer grounding explicitly
deferred to its own `decision` issue.*

---

## The mapping is worth having on its own terms

A reader who wants to understand or audit a breakdown needs to see which
requirement each obligation came from. Today they cannot: `Obligation.source_spans`
points at a character offset, so the trace runs one way and only to text, not to
an identified requirement. Auditing a breakdown means reading 29 obligations
against a task file and reconciling them by hand.

Carrying the mapping also turns the review back on the mandate. A requirement that
yields nothing is usually badly worded rather than unimportant; two requirements
that yield the same obligation are redundant; a requirement that yields eight is
doing too much work. None of that is visible from an obligation list, and all of
it is actionable by the person writing the task file — which is the same person
the tool exists to serve.

## What forced it

Gate 1 for #195 produced 29 obligations and 3 open questions over a task file
written by someone who knew what the decomposition should contain. Nothing was
invented; every obligation produced is accurate. The failure is entirely absence.

| lost | count |
|---|---|
| Completion expectations producing no obligation | 4 of 15 |
| Scope exclusions producing no obligation | 5 of 8 |
| Open questions raised that the task file answers | 3 of 3 |
| Statically-checkable prohibitions typed `human_review` | 2 |

The four lost Completion expectations include all three consecutive single-clause
bullets that are #195's most load-bearing requirement — the ones naming a lossy
decomposer and a permissive decomposer as required failures. One scope exclusion
did worse than vanish: *"Deciding which type `record-run-provenance` should
carry"* came back as an open question asking the human to decide it.

Precision is ~1.0 and recall ~0.75. The deficit is recall only.

## This is DR-164's failure, one stage earlier

`partition.py` already records the mechanism: *a schema-constrained call degrades
by shedding work long before it runs out of context; what binds is how many
independent judgments one response is asked to carry.* Mapping shed 80 of 96
entries at 2.5% context utilisation and was fixed by partitioning judgments, on
the same model.

Decompose has the smallest prompt in the pipeline — no diff, ~2.5k tokens on
#195's task file. Size is not the constraint here either.

## The schema has nowhere to record "I considered requirement 7"

`_Decomposition` is `list[obligations] + list[open_questions]`. A response
covering 20 of 29 requirements is exactly as well-formed as one covering all 29,
so nothing downstream can notice — the same shape as mapping's schema-valid empty
`obligation_ids`.

The second half is the interchange gap: `requirement/obligations.py::_user_prompt`
returns `f"Task file:\n\n{parsed.source}"`. The pipeline runs `parse_task_file`,
computes typed spans for constraints, scope exclusions and completion
expectations, then discards them and pastes raw markdown for the model to
re-derive. Recorded as a standing invariant in CLAUDE.md (PR #201).

## Decisions

**1. Decompose returns a requirement → obligation mapping.** The mapping is part
of persisted review state and survives into the report, so coverage of the mandate
is readable at every later stage and in the rendered review.

**2. The relation is many-to-many, and an obligation may serve several
requirements.** Requirements are user input and are often redundant: two bullets
can state the same thing in different sections. Such a case is recorded as one
obligation mapped to both requirements. An obligation is never duplicated so that
each requirement can hold its own copy.

This reframes #144, which exists because a task file stating one requirement in
two sections produced two obligations. Under the mapping that is not a duplicate
to detect but two requirements linked to one obligation, and the judgment shifts
from *"are these two obligations the same?"* — fuzzy, with over-merging as the
worst outcome — to *"does this requirement restate one already covered?"*, which
is anchored to identified requirements and answered by adding a link rather than
by destroying an obligation.

Two of #144's open design points close as a result. **Where it runs:** a separate
pass, because partitioning by requirement batch means a prompt-level instruction
structurally cannot catch the main case — the Constraints statement and the
Completion-expectations statement of one requirement land in different batches.
**Merge vs. flag:** a merged obligation carrying two requirement links is itself
the record that a merge happened; no separate annotation is needed.

#144's deliverable upgrades from *union of `source_spans`* to *union of
requirement links*, and it is sequenced immediately after this change rather than
folded into it — de-duplication alters the obligation set, and mixing a behavioral
change into a representational one forfeits the control described under
*Sequencing*.

**3. Every requirement carries an explicit disposition.** Each resolves to exactly
one of: yielded obligations / deliberately yields none, with a reason / raised an
open question instead.

This is compatible with DR-164 decision 4, which refuses to ask a model whether it
erred. Nothing here asks that. Forcing an answer per requirement makes *silence*
unrepresentable; a wrong disposition remains wrong, but it is a claim a human can
reject at Gate 1 and a benchmark case can score.

> **Amended by M1.2.r2 (#217).** The implementation of this decision added a
> fourth disposition, `UNDISPOSED`, assigned by the code to any requirement the
> response failed to account for. It has been removed, and the set is again the
> three above.
>
> The fourth value was reached from two conditions: a response that never
> mentioned a requirement, and a response that labelled one `yielded` while
> naming no obligations. Both are malformed, and recording them as a disposition
> turned a malformed response into a soft finding that still reached a verdict.
> #216's Gate 1 is the demonstration: eight requirements came back `yielded`
> with an empty id list **and a substantive reason**, the reason was discarded
> in favour of a diagnostic string, and the run continued.
>
> The registry is derived from the parse and reconciliation walks it, so the
> code cannot drop a requirement — the worst reachable outcome is a poor-quality
> response. A disposition for "the response did not say" therefore encoded a
> state no correct run produces.
>
> **Completeness is now enforced at parse.** Each disposition is a distinct
> shape carrying only its own payload, so `yielded` structurally requires an
> obligation id and `no_obligation` structurally requires a reason; and
> reconciliation raises on a missing requirement, a duplicate, an id outside the
> registry, or a claim naming only outputs the response never produced. A
> response that does not account for the mandate produces no `RequirementMap`
> at all.
>
> Two implementation notes worth not rediscovering. The shapes are a plain
> `Union`, not a pydantic tagged union: a tagged union renders `oneOf` plus
> `discriminator`, and OpenAI strict mode accepts neither. "At least one id" is
> a required scalar field beside a list rather than a list with `min_length`,
> because strict mode rejects `minItems` — the guarantee has to be carried by
> the shape to survive onto the wire.

**4. Requirement ids are derived from the parse.** The work list comes from
`markdown-it`. A model-generated list of requirements would be built by the same
attention pass that produced 29 instead of 38.

**5. Obligation derivation is partitioned by requirement batch, with the whole
task file in every prompt.** The full file stays in context because the recurring
#178 defect is failure to reconcile across sections: a batch that sees only its
own bullets cannot notice that the ground-truth table settles run 4's reading.

DR-164 decision 2 declined to generalise partitioning past the mapping stage. It
applies here because the cost that blocked it does not:

| stage | shared context | partition cost |
|---|---|---|
| coverage, unrequested, recommendations | ~96% diff | ~3.8x tokens, no observed failure |
| decompose | task file, ~2.5k tokens | ~6x the smallest prompt in the pipeline, parallelisable |

**6. Obligation typing is its own pass.** A uniform per-obligation judgment with
the taxonomy and an explicit "statically checkable implies not `human_review`"
rule — small, repeated, independently scorable, and the recurring shape of #196.

**7. Open questions are a filtered pass, and each must cite where the task file
fails to answer it.** The citation is what makes the #178 case reviewable: a
question whose cited gap is contradicted by the file is a defect a reader can
point at.

**8. The decomposer is code-blind, and never receives the diff or head revision.**
Pinned by a test. If the mandate is decomposed in light of the delivered
implementation, a missing obligation and a missing implementation become
correlated errors, and the review loses the ability to detect the one thing it
exists to detect.

**9. Open-question resolution reads both the change and the repository at base
revision.** `resolve_open_questions` already receives the change set; this adds
the base revision. Decision 8 means the decomposer will raise questions whose
answers sit in already-committed code, and such a question resolves today only if
the diff happens to speak to it — while Gate 2 requires every open question
resolved. Without this, decision 8 manufactures permanent Gate 2 blockers, the
same shape as #153.

Resolution runs after the obligation set is fixed, so code access there carries
none of the contamination risk decision 8 guards against.

**The governing rule: code can tell the resolver what the mandate MEANS. It
cannot tell the resolver what the mandate REQUIRES.** Both revisions are evidence
of meaning and neither is evidence of a requirement — observing what the code does
never establishes what was asked for. Each resolution is recorded under one of
four dispositions, with its citation:

| disposition | basis | blocks Gate 2 |
|---|---|---|
| settled by the task file | the mandate answers it | no |
| settled by existing code | base revision fixes what a term denotes | no |
| delegated, and decided in the change | the mandate leaves the choice to the builder; the diff shows what was chosen | no |
| unresolved | none of the above | yes |

The third is CLAUDE.md's Gate 1 triage case 2 — an implementation detail
deliberately left to the coding agent — and it is why the change set matters here
and not only the base revision. Its discipline is that **delegation is established
from the mandate, never from the code**: the task file must show the choice was
the builder's to make, and the diff then supplies what was chosen. A question the
mandate did *not* delegate is not resolved by observing that the builder picked
something; that is a decision made where the mandate was silent, which is the
unrequested-change axis (DR-081) and must surface rather than close. Reversing
this makes the reviewer ratify the builder's choice — decision 8's correlated-error
failure, reappearing one stage later.

At Gate 1 there is no change set, so a delegated question correctly stays open;
CLAUDE.md's triage says take no action on it, not resolve it.

## Rejected on the way here, recorded so they are not re-derived

- **Upgrade the model.** Not a fix: the deficit is recall only, and making absence
  unrepresentable buys recall specifically. Worth measuring as a *diagnostic* of
  whether the cheap model suffices once judgments per call are reduced — but
  **after #195 merges, not before, and resampled rather than run once.** A single
  decompose run is not evidence by this repository's own findings: run 7 of the
  corpus warns against re-running and reading the prettier result, and DR-180
  establishes that instability does not license a conclusion from one sample. A
  model that recovers seven of the nine requirements on one run would say nothing.
  The scored form is `decompose_case` over #195's cases with `RunConfig.model`
  varied and #189's instability harness supplying the resampling — which also
  gives that harness its first live run.
- **Let the decomposer manage its own workload with tools and a todo list.**
  Reopens DR-164 decision 4 by asking the failing faculty to enumerate what its own
  attention dropped. Breaks replay: call N+1's request key would depend on call N's
  output, so the chain forks on any single-token variation — and per `llm.py`,
  Anthropic refuses `seed` and accepts only `temperature=1`, so on that provider it
  is not replayable at all. Bounded, fixed-round retrieval is a different thing and
  is not rejected here.
- **Chunk the task file by section.** Would worsen #178 rather than fix it. The
  wrong-question defect is failure to reconcile *across* sections.
- **Give the decomposer a repo map built from module docstrings.** Rejected as
  generalising from this repository — 25 source files with unusually explanatory
  docstrings. For an arbitrary codebase, retrieval is the baseline and a map is the
  special case that happens to fit. Recorded because the map is cheap enough to
  look obviously correct when measured on this repo alone.

## Scope exclusions may be losing to the prompt's own rule

Five of eight were dropped, and one returned inverted as a question. The system
prompt commands that every obligation be stated as a positive invariant and never
as a prohibition — and the Scope exclusions section is entirely prohibitions. A
model that cannot find a positive form for *"Deciding which type
`record-run-provenance` should carry"* has been instructed into a corner.

Untested hypothesis, cheap to test, recorded so it is not lost.

## Measurement

**Decomposition-accuracy figures are not comparable across this change**, for the
reason DR-164 states at `mapping_accuracy`: the question being asked of the model
changes, so figures before and after must not be plotted as a trend or cited as a
regression. State it where a reader meets the number.

Independently: the corpus is **one repository, one author, and unusually
well-sectioned mandates**. `task_file.py` keys off `## Constraints` /
`## Scope exclusions` / `## Completion expectations`; a real change mandate is a
ticket with none of those. The figure is decomposition accuracy on that
distribution, not in general, and belongs at the metric alongside the
non-comparability note.

## Sequencing

#195 lands first, unchanged. Its green suite is the control that proves this
change is representational: the mapping alters the shape of decompose's output,
not its content, so the suite should pass before and after (modulo re-record), and
a case that flips is the signal that something behavioral changed unintentionally.

Then the suite is rebuilt against the mapping. The inputs do not change — each
case still supplies its run's `current-task.md` — and the ground truth does not
change, since #195's labels are already phrased as *"requirements that produced no
obligation."* What changes is the assertion mechanism: a label binds to the
mapping directly instead of reconstructing it from obligations and `source_quote`.
That is a **superseding issue**, not an edit in place; #195's acceptance genuinely
passed.

Two transcript re-records are unavoidable — one for the mapping's schema change,
one for the quality work (decisions 5–7). Sequence each so the cost is paid once.

## Resolved after acceptance

**Requirement id stability — settled as an interim scheme (#202, deferred to
#209).** Ids are `section + ordinal` in parse order, zero-padded and assigned by
the code: `task-01`, `constraint-01`, `exclusion-03`, `completion-07`. The Task
section is ordinal-bearing like the others; an earlier draft spelled it bare
`task`, on the reasoning that there is at most one behavior statement — true only
because `parse_task_file` was discarding every paragraph after the first.

Neither candidate captures requirement *identity*, and that was the finding.
Positional ids cannot distinguish "the same requirement, reworded" from "a
different requirement in the same position"; content-derived ids cannot
distinguish "the same requirement, reworded" from "a new requirement". Identity
across versions is semantic — the `align_obligations` problem one level up — and
is out of scope for a representational change. #209 owns it.

Positional wins the interim on two grounds. It satisfies the acceptance
criterion as written, which is *within-version* determinism ("stable across two
runs over byte-identical task text"), and nothing in decision 1–4 needs more.
And its failure mode is the safe one: a content hash changes on a comma, so the
commonest edit in the corpus — rewording a bullet — would present as *this
requirement vanished and a new one appeared*, which is indistinguishable from
the recall defect this whole change exists to make visible. A positional id
shifting after an inserted bullet is mechanical, and the registry entry carries
the `TextSpan`, so a reader always sees the text an id points at.

**What this defers explicitly:** a requirement id is not comparable across two
versions of a task file. The Sequencing section's rebuild of #195's suite — so
labels bind to the mapping rather than reconstructing it from `source_quote` —
is where cross-version identity actually bites, and it is sequenced after #209.

## A parse may only be authoritative if it reports what it missed

Recorded because #202 learned it the expensive way, and because the
structured-interchange invariant in CLAUDE.md does not say it.

Decision 5 replaced `parsed.source` in the decomposer's prompt with typed,
identified fields. That is right. But `parse_task_file` kept only the **first**
paragraph under `# Task`, and while the model was handed the raw source that cost
nothing — it read the whole file regardless. The moment the parse became the only
thing the model sees, every gap in it became invisible data loss. The first
casualty was three paragraphs of #202's own mandate, including the sentence
stating what the change was; the decomposer then produced an obligation to
*preserve the flat list being removed*, which was a faithful reading of the only
Task text it had been given.

The general rule: **a lossy parse is safe exactly until it is authoritative.**
Any stage that stops passing source text and starts passing structure takes on an
obligation to report what its structure does not cover. #202 does this as
`RequirementMap.unread_source`, rendered by both the CLI and the §16 report — the
mandate-coverage story one hop further back, source text -> requirements ->
obligations, with the same failure mode of silence at each hop.

This also caught a second thing for free: `parse_task_file` has never read
markdown tables, so #195's own task file carried its ground truth invisibly. That
was already noted under Open below; it is now reported at runtime rather than
known only to this document.

## Open

- **Does the decomposer get base-revision context?** Own `decision` issue.
  Decision 9 moves the code-answerable case downstream, which may settle it. If it
  is ever built, the constraint is that grounding may sharpen wording, settle
  ambiguity and populate `observable_behavior`, but may not add or remove
  obligations — testable via `benchmark/alignment.py::align_obligations`.
- **Requirement-unit extraction from unstructured mandates.** The deterministic
  enumeration assumes §7.1 headings. Real tickets have none, and the ground-truth
  *tables* in #195's own task file are already invisible to `parse_task_file`.
- **Compound-clause splitting within a single bullet.** *"A case's input is the
  run's current-task.md. No task text is copied into the case."* lost its second
  half — the same shape as the run-4 truncation the corpus documents.

## Related

- `docs/DR-164-mapping-stage-request-partitioning.md` — the judgments-per-request
  finding this applies one stage earlier, and the partitioning mechanism reused.
- `docs/DR-081-unrequested-change-scoring.md` — the two-axis framing (obligation →
  code, code → obligation) that decision 1 applies one stage earlier.
- PR #201 — the structured-interchange invariant in CLAUDE.md.
- #144 — de-duplication of semantically duplicate obligations, reframed by
  decision 2 and sequenced immediately after this change.
- #153 — scope exclusions demanding evidence that cannot exist; decision 9 is the
  same family of Gate 2 blocker.
- #181 (umbrella), #178, #196, #193 — the tracked defects this addresses.
