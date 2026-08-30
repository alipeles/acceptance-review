"""The decompose ledger: what each run derived, and what it carried (#269).

Decomposition used to be re-derived from scratch on every run. `rerun.py` states
the rule it worked under — *"A changed task invalidates everything. Obligations
are a function of the task text, so if that changed, nothing carries forward"* —
so one edited character discarded a whole prior decomposition and asked the model
for all of it again. #191 measured the cost: three runs over one unchanged task
file differing only by seed produced 38 distinct criterion wordings across ~20
criteria, with identifiers re-minted alongside them, and zero content difference.
The criterion text is the prompt for every later stage, so that churn is a floor
under every downstream stability number.

This module holds the record that makes carrying forward possible.

**Why a ledger and not the review store.** `ReviewStore` writes one file per
reviewed revision and overwrites it in place, and an uncommitted run stores under
the literal `<working-tree>` — so the Gate 1 loop, which is exactly where this
feature earns its keep, keeps no history at all. `decompose` also never
constructs a `Review`, so there is no review to read on that path. The ledger is
therefore both the log and the carry-forward store: it holds the derivations
themselves, not pointers to them.

**Append-only, one file per run.** Three worktrees run concurrently in this
repository, and a single shared file would have three writers. It lives outside
`.acceptance/cache/` so that clearing the cache cannot take it — DR-259 lost two
runs that way.

**No wall-clock reaches review state.** `Review` deliberately carries no
timestamp: it would break the byte-identical guarantee (M0.5), which is why
ordering came from git ancestry instead. Ordering lives here, where byte
stability is not claimed, and is never read back as an input to a review.

**Identity is a parent pointer, not a shared lineage id.** Each run mints its own
`run_id` and records the run it continues as `parent_run_id`. A lineage is the
transitive closure of those pointers, derived rather than stored. The alternative
— one id shared by every run in a lineage — needs "the latest run in the lineage"
to select a prior, which needs ordering, which needs wall-clock or a sequence
number. A parent pointer never reads time at all.
"""

from __future__ import annotations

import hashlib
import secrets
from enum import Enum
from pathlib import Path

from pydantic import Field

from acceptance.carry import carry_key as shared_carry_key
from acceptance.model_base import PersistableModel
from acceptance.review_state import (
    DefectSet,
    Disposition,
    Obligation,
    OpenQuestion,
    PairVerdict,
)
from acceptance.serialization import canonical_json

DEFAULT_LEDGER_ROOT = Path(".acceptance/ledger")

# Decompose behaviour that changes the output without changing the request.
#
# The request key already invalidates a carried entry when the prompt, the
# response schema, the model or the seed moves — that is what makes a minor tool
# update lose no work. It cannot see a code change that alters what we do with an
# unchanged response: post-processing a quotation differently, marking
# `satisfied_by_absence` from a different signal, changing how ids are uniqued.
# Bump this by hand when that happens. It is deliberately an integer and not a
# hash of the module: a hash would invalidate on every comment edit, which is the
# failure mode that trains people to clear the ledger instead of reading it.
#
# 2 (#317): a call answers for one requirement and can only quote that
# requirement's own spans, so the attribution step that re-filed an obligation
# onto whichever requirement its quotation landed in is gone; the opening summary
# is accounted for by a separate step over spans of its own words; and
# `satisfied_by_absence` is read off the answering requirement's section rather
# than the quotation's owner.
DECOMPOSE_STAGE_LOGIC_VERSION = 2


class Derivation(str, Enum):
    """How a requirement's obligations came to be, for this run."""

    DERIVED = "derived"
    """Asked of the model in this run — a new requirement, or a re-derivation."""

    CARRIED = "carried"
    """Taken verbatim from the continued run; no model call was issued."""

    REVISED = "revised"
    """The requirement's text changed, so it was re-asked against its old text."""


class RequirementDerivation(PersistableModel):
    """One requirement's outcome in one run.

    `text` is the requirement's exact text, and it is the identity used to decide
    whether a later run may carry this entry. Not the requirement id: ids are
    positional (`section-ordinal`), so inserting one bullet renames every later
    requirement in its section while changing none of them.
    """

    requirement_id: str
    text: str
    carry_key: str
    derivation: Derivation
    disposition: Disposition
    reason: str | None = None
    carried_from: str | None = None
    revision_reason: str | None = Field(
        default=None,
        description=(
            "Why this requirement was re-asked: the old wording it had in the run "
            "this one continues. A requirement revision, never a git revision."
        ),
    )
    obligations: list[Obligation] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)

    def digest(self) -> str:
        """Content digest of this derivation, for `carried_from`.

        What a later run records when it carries this entry forward. A run id
        would be the obvious thing to record and is the wrong one: it is minted
        randomly, so putting it in review state would make two runs over the same
        input differ in their bytes. This digest is a function of the derivation's
        content alone, so it is stable, and it is the more useful value anyway —
        it identifies *what* was carried rather than which run happened to hold it.
        """
        payload = {
            "carry_key": self.carry_key,
            "text": self.text,
            "disposition": self.disposition.value,
            "obligations": [obligation.to_dict() for obligation in self.obligations],
            "open_questions": [question.to_dict() for question in self.open_questions],
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def obligation_fingerprint(obligation: Obligation) -> str:
    """What makes an obligation the same obligation, for a merge decision.

    The triple `rerun.py::_linking_inputs` already compares — id, description,
    observable behaviour — because those are exactly the fields the linking prompt
    shows the model. Two obligations with the same triple were shown identically,
    so the answer that came back is still the answer to this question. A field the
    prompt never renders cannot change the verdict and is deliberately not here.
    """
    payload = {
        "id": obligation.id,
        "description": obligation.description,
        "observable_behavior": obligation.observable_behavior,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class MergeDecision(PersistableModel):
    """One answered "are these the same requirement?" pair.

    Keyed by the two obligations' fingerprints rather than their ids, and stored
    sorted, so the decision is about the two obligations rather than about the
    order they happened to be enumerated in. Pair ids cannot be used: they are
    positional (`pair-0007`), assigned before filtering, so carrying one
    obligation forward renumbers every pair after it.
    """

    left: str
    right: str
    same_requirement: bool

    @classmethod
    def between(cls, left: Obligation, right: Obligation, same_requirement: bool) -> MergeDecision:
        pair = sorted((obligation_fingerprint(left), obligation_fingerprint(right)))
        return cls(left=pair[0], right=pair[1], same_requirement=same_requirement)

    @property
    def key(self) -> tuple[str, str]:
        return (self.left, self.right)


class LedgerEntry(PersistableModel):
    """One run's record. Written once, never rewritten."""

    run_id: str
    parent_run_id: str | None = None
    stage_logic_version: int = DECOMPOSE_STAGE_LOGIC_VERSION
    task_digest: str = ""
    calls_issued: int = 0
    derivations: list[RequirementDerivation] = Field(default_factory=list)
    merge_decisions: list[MergeDecision] = Field(default_factory=list)
    # The defect sets this run enumerated, so `--continue` carries them (#313).
    # Empty on a `decompose` run, which has no change set and therefore nothing
    # to enumerate against — and empty on every entry written before #313, which
    # reads as "nothing to carry" and re-enumerates. That is the conservative
    # direction, the same one an absent `evidence_carry_key` takes.
    #
    # Keyed on obligation TEXT inside each set rather than on its position here,
    # so a run that renamed an obligation still finds its set.
    defect_sets: list[DefectSet] = Field(default_factory=list)
    # The (defect, test) verdicts this run judged, so `--continue` carries them
    # (#314). Empty on a `decompose` run and on every entry written before #314,
    # both of which read as "nothing to carry" and re-judge — the same
    # conservative direction `defect_sets` takes.
    #
    # Keyed inside each verdict on the defect's CONTENT and the test's id, not on
    # position here and not on the defect id: defect ids are composed from the
    # obligation id, so rewording a requirement moves every id beneath it and a
    # position-keyed carry would hand a verdict to the wrong pair.
    pair_verdicts: list[PairVerdict] = Field(default_factory=list)

    def decisions_by_pair(self) -> dict[tuple[str, str], bool]:
        """Every merge decision this run holds, keyed by fingerprint pair."""
        return {decision.key: decision.same_requirement for decision in self.merge_decisions}

    def by_text(self) -> dict[str, RequirementDerivation]:
        """This run's derivations keyed by requirement text — the join a later
        run makes to decide what it may carry.

        Later entries win on a duplicate text, which cannot arise from
        `build_registry` (two identical bullets would be two requirements with the
        same text and the same obligations, so either answer is the same answer).
        """
        return {derivation.text: derivation for derivation in self.derivations}

    def carried_count(self) -> int:
        return sum(1 for entry in self.derivations if entry.derivation is Derivation.CARRIED)

    def derived_count(self) -> int:
        return sum(1 for entry in self.derivations if entry.derivation is Derivation.DERIVED)

    def revised_count(self) -> int:
        return sum(1 for entry in self.derivations if entry.derivation is Derivation.REVISED)


def new_run_id() -> str:
    """A fresh run identifier.

    Random, not derived from content: two runs over identical input are two runs,
    and the ledger has to be able to tell them apart to stay append-only. This is
    also exactly why a run id must never reach `Review` — see `LedgerEntry`.
    """
    return secrets.token_hex(8)


def carry_key(
    *,
    system_prompt: str,
    response_schema: dict,
    model: str,
    temperature: float,
    seed: int | None,
    stage_logic_version: int,
    requirement_text: str,
) -> str:
    """Decomposition's carry key: `carry.carry_key` with this stage's own input.

    The rule and the reasoning now live in `acceptance.carry`, which no stage
    names (#251, #286). What stays here is the one decompose-specific fact — that
    a requirement's own input is its text, and nothing else about the registry
    (#178, `docs/DR-269-carry-key-excludes-registry-context.md`).

    Spreading `inputs` rather than nesting it keeps this byte-identical to the
    key #269 computed, so every ledger entry already on disk still matches.
    """
    return shared_carry_key(
        system_prompt=system_prompt,
        response_schema=response_schema,
        model=model,
        temperature=temperature,
        seed=seed,
        stage_logic_version=stage_logic_version,
        inputs={"requirement_text": requirement_text},
    )


class LedgerStore:
    """Append-only run records under `root`, one file per run."""

    def __init__(self, root: Path | str = DEFAULT_LEDGER_ROOT) -> None:
        self.root = Path(root)

    def path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def write(self, entry: LedgerEntry) -> Path:
        """Write one run's record.

        Refuses to overwrite. The append-only property is what lets a later
        feature count how many runs a decomposition took to settle, and it is
        worth an error rather than a silent clobber — a run id collision means
        something minted one twice, which is a bug worth hearing about.
        """
        path = self.path_for(entry.run_id)
        if path.exists():
            raise FileExistsError(f"ledger entry already written for run {entry.run_id}")
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(entry.to_dict()) + "\n", encoding="utf-8")
        return path

    def read(self, run_id: str) -> LedgerEntry:
        path = self.path_for(run_id)
        if not path.exists():
            raise FileNotFoundError(f"no ledger entry for run {run_id}")
        import json

        return LedgerEntry.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def read_if_present(self, run_id: str | None) -> LedgerEntry | None:
        """The continued run's record, or None.

        None means no carry-forward, which is today's behaviour exactly. The
        default is fresh and the failure mode of the default is lost work, never
        imported work — so an unreadable or absent prior is not an error here.
        """
        if not run_id:
            return None
        try:
            return self.read(run_id)
        except (FileNotFoundError, ValueError):
            return None
