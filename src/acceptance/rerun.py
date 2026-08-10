"""Incremental re-run against a new head (M7.5, §13.5 #9).

The revision cycle this serves: a review reports gaps, an agent addresses them
and produces a new head, and the checker runs again. Starting over on every
re-run is wrong in two ways — it re-bills judgments about code nobody touched
(§17), and it lets those judgments *drift*, because the request key hashes the
whole change set, so an unrelated hunk elsewhere invalidates the transcript for
an obligation whose own code and tests are identical.

So a re-run carries unaffected judgments forward and re-derives the rest. Three
things make that safe rather than a way to launder stale conclusions:

- **The prior review is found by git ancestry, not by recency.** The store is
  keyed by revision and holds no ordering, and `Review` carries no timestamp —
  deliberately, since wall-clock state would break the byte-identical-re-run
  invariant (M0.5). Asking git which stored revisions are ancestors of the new
  head is deterministic and needs no new state.
- **A carried-forward judgment is labelled** with the revision it was
  established against (`Obligation.carried_forward_from`), so the report can
  never present evidence about an older head as current.
- **A changed task invalidates everything.** Obligations are a function of the
  task text, so if that changed, nothing carries forward. This needs the review
  to record the task it judged, which it previously did not.

Byte-identical determinism still holds: it is a property of runs over the same
input, and an incremental re-run has an extra input (the prior review), so it is
a different run — not the same one producing different bytes.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from pydantic import ValidationError

from acceptance.review_state import (
    ChangeSet,
    Finding,
    Obligation,
    ObligationChange,
    Review,
    ReviewDelta,
    TaskSource,
    TestRecommendation,
)
from acceptance.review_store import ReviewStore


def task_digest(task_text: str) -> str:
    """Content address for a task file, so a re-run can tell it changed."""
    return hashlib.sha256(task_text.encode("utf-8")).hexdigest()


def task_source_for(task_text: str, identifier: str) -> TaskSource:
    return TaskSource(
        kind="local_file",
        identifier=identifier,
        snapshot=task_digest(task_text),
        text=task_text,
    )


def _is_ancestor(candidate: str, head: str, repo: Path) -> bool:
    """Whether `candidate` is an ancestor of `head` (git's own answer)."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate, head],
        capture_output=True,
        text=True,
        cwd=repo,
    )
    return result.returncode == 0


def _commit_distance(ancestor: str, head: str, repo: Path) -> int | None:
    """Commits between `ancestor` and `head`, or None if git cannot say."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{ancestor}..{head}"],
        capture_output=True,
        text=True,
        cwd=repo,
    )
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def find_prior_review(
    store: ReviewStore,
    head_revision: str,
    repo: Path,
    task_text: str,
    ancestry_ref: str | None = None,
) -> Review | None:
    """The nearest stored review of an ancestor of `head_revision`.

    `ancestry_ref` is the revision git measures ancestry against, when that is
    not `head_revision` itself. A working-tree review (§5.1) is recorded under
    `<working-tree>`, which git cannot resolve — so without this the feature is
    unreachable from the primary local path, where a check runs before a commit
    exists. The working tree descends from HEAD, so HEAD is the anchor, and a
    stored review *of* HEAD is a legitimate predecessor: you reviewed the commit,
    then kept editing.

    Nearest by commit distance, not by write time: two reviews written in either
    order over the same history must pick the same predecessor. A review of a
    revision that is not an ancestor of this head belongs to a different line of
    work and is ignored rather than merged (divergent branches are out of scope).

    A prior review whose task digest differs is not returned at all: its
    obligations came from a different task, so nothing in it can carry forward.
    """
    if not store.root.is_dir():
        return None

    anchor = ancestry_ref or head_revision
    digest = task_digest(task_text)
    nearest: tuple[int, Review] | None = None
    for path in sorted(store.root.glob("*.json")):
        revision = path.stem
        if revision == head_revision:
            continue  # this head's own earlier review, not a predecessor
        try:
            review = store.read(revision)
        except ValidationError:
            # A review written under an older schema. The store accumulates
            # across versions, so scanning it must be best-effort: a review this
            # build cannot parse is one it cannot build on, and crashing the run
            # would mean any change to the review schema bricks the tool for
            # every existing cache. Skipping falls back to a full re-run, which
            # is the conservative direction — it re-derives rather than carrying
            # anything forward on a guess.
            continue
        if review is None or review.task_source is None:
            continue
        if review.task_source.snapshot != digest:
            continue
        if not _is_ancestor(revision, anchor, repo):
            continue
        distance = _commit_distance(revision, anchor, repo)
        if distance is None:
            continue
        if nearest is None or distance < nearest[0]:
            nearest = (distance, review)
    return nearest[1] if nearest is not None else None


def _test_file(test_identifier: str) -> str:
    """The file part of a pytest node id (`path::test_name` -> `path`)."""
    return test_identifier.split("::", 1)[0]


def changed_paths(change_set: ChangeSet) -> set[str]:
    """Every path the new work touched, including a rename's old path."""
    paths: set[str] = set()
    for changed in change_set.files:
        paths.add(changed.path)
        if changed.old_path is not None:
            paths.add(changed.old_path)
    return paths


def stale_obligation_ids(prior: Review, change_set: ChangeSet) -> set[str]:
    """Ids of prior obligations the new work could have affected.

    File-level, not hunk-level. A hunk header shifts when unrelated lines change
    above it, so matching on hunks would claim a precision `coverage_refs` does
    not have. Over-invalidating costs a re-derivation; under-invalidating reports
    a stale judgment as current, so the comparison is deliberately coarse.

    An obligation with neither code nor test citations is always stale: there is
    nothing to prove the new work missed it.
    """
    touched = changed_paths(change_set)
    stale: set[str] = set()
    for obligation in prior.obligation_map:
        cited = {ref.split("#", 1)[0] for ref in obligation.coverage_refs}
        cited |= {_test_file(test) for test in obligation.test_evidence}
        if not cited or cited & touched:
            stale.add(obligation.id)
    return stale


def _linking_inputs(obligations: list[Obligation]) -> list[tuple[str, str, str]]:
    """What the linking pass is shown about each obligation, in order."""
    return [
        (obligation.id, obligation.description, obligation.observable_behavior)
        for obligation in obligations
    ]


def derivation_changed(prior: Review, derived: list[Obligation]) -> bool:
    """Whether stage 1's output moved since the prior review (#144).

    The second staleness question, and it is asked separately from
    `stale_obligation_ids` on purpose. That one asks whether the *change* could
    have affected an obligation's judgment; this asks whether the obligation set
    itself was computed from different inputs. The stages fail independently —
    #167's Gate 2 showed a byte-identical mapped set with a flipped judgement
    over it — so one question cannot stand in for the other.

    It matters because linking can merge a different pair over an unchanged id.
    An obligation that survived both runs under the same id may have absorbed a
    different set of requirements, which makes it a different obligation wearing
    a familiar slug, and carrying a prior judgment onto it would launder a stale
    conclusion.

    A prior review recorded before `derived_obligation_map` existed reports
    unchanged, and that is correct rather than merely convenient: the risk this
    question guards against is a slug whose meaning moved because linking merged
    a different set behind it, and linking did not run for such a review. With no
    merges there is no hidden change of meaning, and the older staleness question
    still covers everything else.
    """
    if not prior.derived_obligation_map:
        return False
    return _linking_inputs(prior.derived_obligation_map) != _linking_inputs(derived)


def obligations_to_rederive(
    fresh: list[Obligation],
    prior: Review,
    change_set: ChangeSet,
    derived: list[Obligation] | None = None,
) -> list[Obligation]:
    """The fresh obligations this run must judge from scratch: those the new work
    could have affected, plus any the prior review never saw.

    Matched by obligation id, a stable slug over the task text — so the same task
    yields the same ids and a prior judgment lands on the obligation it was
    actually made about.

    When `derived` is supplied and stage 1's output moved, nothing is carried
    forward: every id is suspect, because the same slug may now stand for a
    different set of merged requirements (#144).
    """
    if derived is not None and derivation_changed(prior, derived):
        return list(fresh)
    stale = stale_obligation_ids(prior, change_set)
    prior_ids = {obligation.id for obligation in prior.obligation_map}
    return [
        obligation
        for obligation in fresh
        if obligation.id in stale or obligation.id not in prior_ids
    ]


def merge_carried_forward(
    fresh: list[Obligation], judged: list[Obligation], prior: Review
) -> list[Obligation]:
    """Judged obligations where this run re-derived them, prior ones elsewhere.

    A prior judgment is taken wholesale — coverage status, evidence class,
    citations, tier — rather than field by field: splicing a prior evidence class
    onto fresh citations would produce a judgment no run ever actually made, and
    the tier would no longer describe how the classification was reached.
    """
    judged_by_id = {obligation.id: obligation for obligation in judged}
    prior_by_id = {obligation.id: obligation for obligation in prior.obligation_map}
    merged = []
    for obligation in fresh:
        if obligation.id in judged_by_id:
            merged.append(judged_by_id[obligation.id])
            continue
        previous = prior_by_id[obligation.id]
        merged.append(
            previous.model_copy(
                update={
                    # Keep the ORIGINAL revision when carrying a carried judgment
                    # forward again, so the label names where the judgment was
                    # established rather than the last run that happened to reuse it.
                    "carried_forward_from": (
                        previous.carried_forward_from or prior.reviewed_revision
                    )
                }
            )
        )
    return merged


def carried_findings(prior: Review, carried: list[Obligation]) -> list[Finding]:
    """Prior findings about obligations this run did not re-derive.

    Without these a re-run would silently *drop* the gap it reported last time
    for code nobody touched — the verdict reads gaps off findings, so an
    unaddressed obligation would look resolved simply because it was not
    re-examined. Matched on `related_obligation`, which coverage findings set to
    the obligation's description.
    """
    descriptions = {obligation.description for obligation in carried}
    return [finding for finding in prior.findings if finding.related_obligation in descriptions]


def carried_recommendations(prior: Review, carried: list[Obligation]) -> list[TestRecommendation]:
    """Prior test recommendations for obligations this run did not re-derive —
    otherwise the agent loses the instruction for a gap that is still open."""
    carried_ids = {obligation.id for obligation in carried}
    return [
        recommendation
        for recommendation in prior.recommendations
        if recommendation.obligation_id in carried_ids
    ]


def compute_delta(prior: Review, obligations: list[Obligation], verdict: str | None) -> ReviewDelta:
    """What moved between `prior` and this run's obligations/verdict."""
    prior_by_id = {obligation.id: obligation for obligation in prior.obligation_map}
    changes = []
    for obligation in obligations:
        previous = prior_by_id.get(obligation.id)
        if previous is None:
            continue  # new obligation: nothing to compare it against
        if (
            previous.coverage_status == obligation.coverage_status
            and previous.evidence_class == obligation.evidence_class
        ):
            continue
        changes.append(
            ObligationChange(
                obligation_id=obligation.id,
                description=obligation.description,
                previous_coverage_status=previous.coverage_status,
                coverage_status=obligation.coverage_status,
                previous_evidence_class=previous.evidence_class,
                evidence_class=obligation.evidence_class,
            )
        )
    return ReviewDelta(
        prior_reviewed_revision=prior.reviewed_revision,
        previous_verdict=prior.completion.verdict.value if prior.completion else None,
        verdict=verdict,
        obligation_changes=changes,
        carried_forward_obligation_ids=sorted(
            obligation.id for obligation in obligations if obligation.carried_forward_from
        ),
    )
