# Task
Make the ids a model hands back verifiable against the ids it was given. Every
stage that asks the model to echo back an id we supplied types that id as
free-form text, so an id that does not exist is valid output. Four of those
stages then discard a foreign id without trace, leaving a result
indistinguishable from a substantive negative answer — the review reports that
nothing evidences an obligation when the truth is that the reviewer answered a
different question. Constrain each id-bearing response field to the ids actually
supplied for that call, and where an answer still cannot be honoured, record it
as an answer not obtained rather than as a negative judgment.

## Constraints
- The set of allowed ids is built per call, from the ids that call itself
  supplied — not from a fixed list.
- An id outside the supplied set is never accepted as a judgment about anything.
- An answer that could not be honoured must not read as a substantive negative
  answer — "no test evidences this obligation", "no hunk answers this question".
- One answer that cannot be honoured must not discard the usable judgments
  returned alongside it.

## Scope exclusions
- Ids the model invents rather than echoes back — the ids assigned to newly
  decomposed obligations — have no supplied set to constrain them to and are
  unchanged by this task.
- Verifying that a quoted span really appears in the task text is a different
  check against supplied input, and is not part of this task.
- An empty answer — a model that returns no ids at all — is schema-valid and
  indistinguishable from a correct negative judgment. No change is attempted
  here, and none is proposed.
- Prompt wording is unchanged except where the constraint itself requires it.

## Completion expectations
- Implementation
- Each model stage that echoes back a supplied id constrains that response field
  to the ids supplied for that call: test-to-obligation mapping, test
  recommendation, unrequested-change detection, coverage classification,
  open-question judgment, and discrimination judgment.
- The allowed-id set a call carries reflects that call's own supplied ids, so a
  stage whose request is partitioned constrains each call to its own partition.
- An id outside the supplied set is not accepted as a judgment, at every one of
  those stages.
- An item whose returned id cannot be honoured is recorded as having no usable
  answer, distinguishably from an item the model judged negatively.
- An obligation whose judgment could not be honoured is left indeterminate,
  rather than reported as an obligation lacking evidence.
- A review holding an indeterminate judgment does not reach a clean completion
  verdict.
- The usable judgments returned in the same response as one that cannot be
  honoured are retained.
- The review names the stage and the id that could not be honoured, so a reader
  can tell which judgment was not obtained and why.
