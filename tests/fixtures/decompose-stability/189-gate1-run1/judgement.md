# Run 1 — judgement

*First decompose of #189's task file. 24 obligations, 5 open questions.*

## Verdict at the time

**Not acceptable as a Gate 1 pass**, for duplication rather than for anything the
tool got wrong. Rewrote the task file and re-ran.

## Duplicate obligation pairs — my wording, not a tool defect

Roughly 8 pairs. Every one traces to the same authoring mistake: I stated the
requirement in the Task prose, again in Constraints, and again in Completion
expectations, so `decompose` faithfully emitted an obligation per mention.

| pair | source of the duplication |
|---|---|
| `report-measurement-conditions` / `report-includes-run-metadata` | near-verbatim; Constraints + Completion expectations |
| `caller-chooses-runs-and-models` / `caller-supplied-defaults` | Constraints + Completion expectations |
| `no-repository-trace` / `no-repo-writes` | Constraints + Completion expectations |
| `report-does-not-decide-acceptability` / `no-thresholding` | Task prose + Scope exclusions |
| `resample-variance-definition` / (covered by `distribution-per-obligation-per-model`) | Task prose bullet restating a deliverable |
| `perturbation-sensitivity-definition` / `perturbation-figure` | Task prose bullet + Completion expectations |
| `model-sensitivity-definition` / `cross-model-agreement` | Task prose bullet + Completion expectations |
| `separate-movement-sources` / the three per-axis obligations | umbrella statement plus its own parts |

This is #144 exactly, including its stated root cause. #144 is open and
**unimplemented** — confirmed by grep over `src/acceptance/requirement/`; there is
no dedup or merge pass anywhere in the decomposition path.

**Disposition:** attributed to #144 (tracked tool defect) *and* fixed at source by
rewriting the task file so each requirement is stated once. Both, because the
authoring error was real and the tool's lack of robustness to it is also real —
#144 itself argues the reviewer must tolerate restatement, since a mandate and its
acceptance criteria naturally overlap.

## Accuracy of the obligations

No invented obligations — all 24 trace to text I wrote. None of the real
requirements missing; all eight of #189's acceptance items are represented.
Labelling all-`explicit` is correct: the task file states each of these outright.

## Open-question triage

| question | case | disposition |
|---|---|---|
| `fixed-input-unspecified` — what fixed input, or how is it selected? | **fair** | Fixed the task file. I wrote "a fixed input" and never said who supplies it, though it is an input on the same footing as run count and model set. |
| `irrelevant-perturbation-unspecified` — which perturbations should be supported? | **fair** | Fixed the task file. I gave one example and never said whether the set was fixed, caller-supplied, or open. |
| `variance-path-interface-unspecified` — what interface should be reused? | implementation detail | No action required; the answer is `benchmark/scoring.py::disclose_variance` and the decomposer has no repo access to find it (the access gap measured in #162). Named the symbol in the task file anyway — cheap, and more precise. |
| `default-values-unspecified` — what defaults? | implementation detail | No action. Deliberately mine to choose. |
| `report-output-format-unspecified` — what output format, emitted where? | implementation detail | No action. **Third observation** of the "immaterial question about output format" mode under audit in session state. Not silenced. |

**No question fell in the "wrong question — stop and tell the human" case.** None
was answerable from the task file alone.
