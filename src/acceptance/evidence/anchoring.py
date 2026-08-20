"""What a re-judged criterion is anchored to, and the changes it may rest on (#292).

#269's Gate 2 is the case this exists for: run 5 differed from run 4 by one
commit that added nine tests and changed no source, and `strongly supported`
collapsed from 37 obligations to 4. Nothing about those criteria had got worse.
The judge was simply asked again and answered differently, and a verdict that is
a function of how many times an obligation has been looked at is not a verdict.

So a criterion whose inputs changed is re-judged *with its previous rating and
the specific changes that could justify moving it*, and a judgement that moves
the rating without naming one of those changes is rejected. The stored rating
stands. That is a constraint on the answer, enforced where the answer is read —
not an instruction in the prompt, which a model is free to ignore.

**Why showing the prior rating is not the anchoring `DR-269` refused.** That
decision kept decomposition's own previous answer away from the model, on the
grounds that anchoring bias is defeated by not asking. The difference is that an
evidence class is **ordinal**: "it got worse" is a claim with a direction, so it
can be interrogated and a justification for it can be demanded. Decomposition's
output has no such order, so there was nothing to demand. #286 asks whether this
generalises; this is the first real answer, and `DR-292` records it.

**The granularity is deliberately coarse, and deliberately temporary.** A
criterion's dependencies are its requirement text, the tests mapped to it, and
those tests' contents. Comparing test *contents* is #293's deliverable and does
not exist yet, so the changes named here are file-level: which files holding this
criterion's mapped tests or implementation were touched. #293 sharpens them.

**A criterion with no nameable change is not anchored at all.** Anchoring it
would make its rating unmovable — no change to rest on means every move is
rejected — and the file-level view above cannot yet see a change that is real but
sub-file. Freezing a rating we cannot explain is the same failure as moving one
we cannot explain, pointing the other way, so the anchor is only applied where
there is something to name.
"""

from __future__ import annotations

from acceptance.model_base import PersistableModel
from acceptance.rerun import changed_paths
from acceptance.review_state import ChangeSet, EvidenceClassification, Obligation, Review

REQUIREMENT_TEXT = "requirement-text"


class DependencyChange(PersistableModel):
    """One change to a criterion's inputs, with the id the judge may cite.

    `id` is what goes into the response schema as an allowed value, so it has to
    be stable across two runs over the same input — it is built from sorted paths
    and never from iteration order.
    """

    id: str
    description: str


class RatingAnchor(PersistableModel):
    """The rating a criterion already had, and what changed under it."""

    obligation_id: str
    stored_class: EvidenceClassification
    changes: list[DependencyChange]

    @property
    def change_ids(self) -> set[str]:
        return {change.id for change in self.changes}


def _test_file(test_identifier: str) -> str:
    """The file part of a pytest node id (`path::test_name` -> `path`)."""
    return test_identifier.split("::", 1)[0]


def _changes_for(
    previous: Obligation, fresh: Obligation, touched: set[str]
) -> list[DependencyChange]:
    changes: list[DependencyChange] = []
    if previous.description != fresh.description:
        changes.append(
            DependencyChange(
                id=REQUIREMENT_TEXT,
                description="the criterion's own requirement text was reworded",
            )
        )
    test_files = {_test_file(test) for test in previous.test_evidence}
    for path in sorted(test_files & touched):
        changes.append(
            DependencyChange(
                id=f"mapped-test-file:{path}",
                description=f"{path}, which holds a test mapped to this criterion, was changed",
            )
        )
    code_files = {ref.split("#", 1)[0] for ref in previous.coverage_refs}
    for path in sorted(code_files & touched):
        changes.append(
            DependencyChange(
                id=f"implementation-file:{path}",
                description=f"{path}, cited as this criterion's implementation, was changed",
            )
        )
    return changes


def build_anchors(
    prior: Review, obligations: list[Obligation], change_set: ChangeSet
) -> dict[str, RatingAnchor]:
    """Anchors for the criteria in `obligations` that the prior review rated.

    A criterion is anchored only when all three hold: the prior review knows it,
    the prior review gave it a rating to hold, and at least one change to its
    dependencies can be named. The last condition is the load-bearing one — see
    the module docstring.
    """
    touched = changed_paths(change_set)
    previous_by_id = {obligation.id: obligation for obligation in prior.obligation_map}
    anchors: dict[str, RatingAnchor] = {}
    for fresh in obligations:
        previous = previous_by_id.get(fresh.id)
        if previous is None or previous.evidence_class is None:
            continue
        changes = _changes_for(previous, fresh, touched)
        if not changes:
            continue
        anchors[fresh.id] = RatingAnchor(
            obligation_id=fresh.id,
            stored_class=previous.evidence_class,
            changes=changes,
        )
    return anchors
