"""Incremental re-run against a new head (M7.5, §13.5 #9).

The revision cycle this serves: a review reports gaps, an agent addresses them
and produces a new head, and the checker runs again. Starting over on every
re-run is wrong in two ways — it re-bills judgments about code nobody touched
(§17), and it lets those judgments *drift*, because the request key hashes the
whole change set, so an unrelated hunk elsewhere invalidates the transcript for
an obligation whose own code and tests are identical.

So a re-run carries unaffected judgments forward and re-derives the rest.

**What "unaffected" means changed in #293, and this module no longer decides it.**
It used to be `stale_obligation_ids`: an obligation was affected if the change
touched any file it cited, for both review axes at once. Appending a test to a
module leaves every existing test in it byte-identical and still tripped that
rule, and re-judging is not free of consequence — 33 obligations came back a tier
lower in #269's Gate 2 on exactly that. The rule is deleted. The test-evidence
rating is now carried per criterion by `evidence/rejudge.py`, comparing the
criterion's requirement text, mapped tests and those tests' contents;
implementation coverage is re-derived every run. What remains here is
`derivation_changed`, which forbids reuse on either axis when the obligation set
itself moved.

Three things make carrying safe rather than a way to launder stale conclusions:

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
    Obligation,
    ObligationChange,
    Review,
    ReviewDelta,
    TaskSource,
    TestRecommendation,
    UnobtainedRecommendation,
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
        check=False,
    )
    return result.returncode == 0


def _commit_distance(ancestor: str, head: str, repo: Path) -> int | None:
    """Commits between `ancestor` and `head`, or None if git cannot say."""
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{ancestor}..{head}"],
        capture_output=True,
        text=True,
        cwd=repo,
        check=False,
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


def changed_paths(change_set: ChangeSet) -> set[str]:
    """Every path the new work touched, including a rename's old path."""
    paths: set[str] = set()
    for changed in change_set.files:
        paths.add(changed.path)
        if changed.old_path is not None:
            paths.add(changed.old_path)
    return paths


def _linking_inputs(obligations: list[Obligation]) -> list[tuple[str, str, str]]:
    """What the linking pass is shown about each obligation, in order."""
    return [
        (obligation.id, obligation.description, obligation.observable_behavior)
        for obligation in obligations
    ]


def derivation_changed(prior: Review, derived: list[Obligation]) -> bool:
    """Whether stage 1's output moved since the prior review (#144).

    It matters because linking can merge a different pair over an unchanged id.
    An obligation that survived both runs under the same id may have absorbed a
    different set of requirements, which makes it a different obligation wearing
    a familiar slug, and carrying a prior judgment onto it would launder a stale
    conclusion. So this forbids **every** reuse, on either axis.

    **It is now the only staleness question this module asks** (#293). It used to
    be the second of two: the first, `stale_obligation_ids`, marked an obligation
    stale whenever any file it cited was touched, and decided implementation
    coverage and the test-evidence rating together. That predicate is deleted.
    The rating is now carried per criterion by comparing what the criterion
    actually depends on — see `evidence/rejudge.py` — and implementation coverage
    is classified for every obligation on every run.

    The two axes are decided apart because they fail apart: #167's Gate 2 produced
    a byte-identical mapped set with a flipped judgement over it, so one question
    could never have stood in for the other.

    Always re-deriving coverage is nearly free — `classify_coverage` is a single
    batched call over the whole obligation set, so narrowing the list shortens one
    prompt and never removes a call — and it errs toward re-deriving, where the
    deleted rule's danger ran the other way, reporting a stale judgement as
    current. It is still the blunt answer; #305 is the sharp one, comparing the
    contents of the cited implementation spans the way the test axis now compares
    mapped tests. Deliberately left there, since #293 excluded narrowing any stage
    other than test-evidence judgement.

    A prior review recorded before `derived_obligation_map` existed reports
    unchanged, and that is correct rather than merely convenient: the risk this
    question guards against is a slug whose meaning moved because linking merged
    a different set behind it, and linking did not run for such a review.
    """
    if not prior.derived_obligation_map:
        return False
    return _linking_inputs(prior.derived_obligation_map) != _linking_inputs(derived)


def carried_recommendations(
    prior: Review, unobtained: list[UnobtainedRecommendation]
) -> list[TestRecommendation]:
    """Prior prescriptions for defects this run was owed one for and did not get.

    **The axis moved from the criterion to the defect** (#316). It used to carry
    for criteria keeping a stored test-evidence rating, because a criterion that
    was not re-judged produced no prescription. That case is gone: the rating is
    now derived arithmetic over pair verdicts, so every criterion is classified
    on every run and every uncovered defect is prescribed for on every run.

    What is left is the one way a prescription can still be owed and missing —
    the stage asked and the model returned nothing for that defect (#275). The
    prior run's prescription for the same defect is still the right instruction,
    because a defect that changed would carry a different id: ids are composed
    from the obligation id and the defect's slug, so a reworded criterion or a
    re-enumerated set produces new ids rather than reusing stale ones.

    Without this, a single omitted answer would delete a still-open instruction
    from the report — the silent loss this function has always existed to stop,
    arriving through a new door.

    There is no matching `carried_findings`. Findings here are coverage findings,
    and coverage is re-derived for every obligation on every run, so no gap can
    be dropped by not looking.
    """
    owed = {entry.defect_id for entry in unobtained}
    return [
        recommendation
        for recommendation in prior.recommendations
        if recommendation.defect_id in owed
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
