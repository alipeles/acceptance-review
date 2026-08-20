# Judgement — #251 Gate 1, run 1

First decomposition of the #251 mandate. `decompose --mode record` at `01a1061`.
34 requirements is the run-3 figure; this run had 33, because two Completion
expectations were still bundled as one.

**Result: not accepted.** Two findings, both real, both acted on before run 2.

## Finding 1 — one requirement produced two obligations with identical text

`completion-02` ("A criterion whose requirement text, mapped test set and mapped
test contents are unchanged keeps its stored rating **and** issues no
evidence-judgement call") yielded two obligations,
`criterion-unchanged-keeps-stored-rating` and
`criterion-unchanged-no-evidence-judgement-call`, whose descriptions are
byte-identical to each other and to the requirement. Splitting a two-claim
requirement into two obligations is right; giving both the whole requirement text
as their description is not, because nothing downstream can then tell them apart.

**Disposition: task file reworded.** The requirement bundled two claims, which is
the wording weakness the gate's tie-break says to fix. Split into `completion-02`
(keeps its stored rating) and `completion-03` (issues no evidence-judgement
call). The duplicate-description behaviour is queued separately as a tool defect
— splitting a requirement is legitimate, copying the text into both halves is
not.

## Finding 2 — a Scope exclusion's trailing clause inverted the obligation

`exclusion-05` read "Selecting which stored earlier state a repeated review
continues, **which is done over git ancestry**." The obligation came back as "The
change does not select which stored earlier state a repeated review continues
over git ancestry" — which prohibits the thing `rerun.py::find_prior_review`
already does and must keep doing. The relative clause was promoted into the
prohibition and the main clause lost.

The same shape decomposed correctly at #269's Gate 1: `exclusion-03` there read
"Prior-review selection for stages other than decomposition, which
`rerun.py::find_prior_review` performs over git ancestry" and produced "The change
does not perform prior-review selection for stages other than decomposition" —
clause correctly dropped (`dogfood-logs/269-gate1-run3/output.log:228`).

**Disposition: task file reworded** (trailing clause deleted), **and queued as a
tool defect**, since the same input shape decomposed correctly once and
incorrectly once.

## Open questions

None raised. The header line reports `raised a question: N` when there are any
and omitted it here.
