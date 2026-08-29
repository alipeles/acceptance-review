"""Deciding, per requirement, what a run may take from the run it continues (#269).

Four outcomes, and the whole feature is the difference between them:

| the requirement | what happens |
|---|---|
| text unchanged | **carried** — no model call, obligations verbatim |
| text edited | **revised** — one call carrying old text, new text and prior obligations |
| no counterpart | **derived** — fresh, with nothing to anchor on |
| gone | **removed** — obligations dropped, and the removal reported |

**Identity is content, not position.** Requirement ids are `section-ordinal`
(`registry.py`), so inserting one bullet renames every later requirement in its
section while changing none of them. Matching on id would report a whole section
as edited every time a bullet is inserted above it. Matching on text is exact,
free, and needs no model call — which is what makes the unchanged case cost
nothing.

**The residue needs a judgement, and only the residue.** After exact matching,
what is left is requirements that changed and requirements that are new, and
telling those apart is #209's problem. That is the one place a model call is
issued, over two short lists, and only when both sides are non-empty. No
similarity threshold is involved: DR-259's *"0.10 is a clean separator"* was
withdrawn, and #211 exists to settle it.

**Anchoring bias is defeated by not asking.** The model is never shown its own
prior answer for approval. Either the input did not change and there is no call
at all, or it changed and there is a real diff to justify against. A stale
carry-over is caught in code rather than by trusting the model to notice it:
every carried obligation's source span must still be found in the new
requirement text (`stale_spans`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from acceptance.carry import decide
from acceptance.llm import ModelClient
from acceptance.review_state import RequirementRef

from .ledger import (
    DECOMPOSE_STAGE_LOGIC_VERSION,
    Derivation,
    LedgerEntry,
    RequirementDerivation,
)

# This step issues a model call, so it names itself in the run's per-stage cost
# footer like every other (#264). Its own name, not `decompose`: it fires only on
# a continued run whose requirement text moved, and folding it into decompose
# would hide a cost that appears on some runs and not others.
_STAGE = "requirement carry alignment"


@dataclass(frozen=True)
class CarryPlan:
    """What each requirement in the current registry is owed.

    `carried` and `revised` are keyed by the *current* requirement id and hold the
    prior derivation they draw on. `derived` is the set of ids with nothing to
    draw on. `removed` are prior derivations whose requirement is gone.
    """

    carried: dict[str, RequirementDerivation] = field(default_factory=dict)
    revised: dict[str, RequirementDerivation] = field(default_factory=dict)
    derived: tuple[str, ...] = ()
    removed: tuple[RequirementDerivation, ...] = ()
    # The key each current requirement's derivation is valid under, carried on
    # the plan so the ledger records what this run would re-derive against rather
    # than recomputing it and risking a different answer.
    keys: dict[str, str] = field(default_factory=dict)

    @property
    def issues_calls_for(self) -> set[str]:
        """Requirement ids this run must ask the model about."""
        return set(self.derived) | set(self.revised)

    def is_fresh(self) -> bool:
        """True when nothing was taken from a prior run — today's behaviour."""
        return not self.carried and not self.revised


def stale_spans(derivation: RequirementDerivation, requirement_text: str) -> bool:
    """True when some carried obligation quotes text the requirement no longer has.

    `_locate_quotation` already enforces that an obligation's quotation lands
    inside a requirement's span when it is first derived. The same rule is what
    catches an obligation carried over from an older wording: if its span text is
    no longer present, the obligation is describing text that is gone, and it is
    re-derived rather than carried.

    Whitespace-insensitive for the same reason `_locate_quotation` is — task prose
    is hard-wrapped, so a reflowed paragraph is not a changed one.
    """
    haystack = " ".join(requirement_text.split())
    for obligation in derivation.obligations:
        for span in obligation.source_spans:
            needle = " ".join(span.text.split())
            if needle and needle not in haystack:
                return True
    return False


def plan_carry(
    registry: list[RequirementRef],
    prior: LedgerEntry | None,
    current_keys: dict[str, str],
    client: ModelClient | None = None,
) -> CarryPlan:
    """Decide what each requirement in `registry` may take from `prior`.

    `current_keys` maps requirement id to the carry key this run would record for
    it — computed by the caller, which is the only place that knows the prompt and
    the response schema.

    With no prior, everything is derived and nothing is removed: that is today's
    behaviour exactly, and it is what "no signal means no carry-forward" reduces
    to in code.
    """
    if prior is None:
        return CarryPlan(
            derived=tuple(requirement.id for requirement in registry),
            keys=dict(current_keys),
        )

    # An entry recorded under different stage logic is not carried. The request
    # key cannot see a change to what we do with an unchanged response, so this
    # is the only thing that can (`ledger.DECOMPOSE_STAGE_LOGIC_VERSION`).
    # Removals are still reported: whether a requirement disappeared is a fact
    # about the two task files, not about the tool that read them.
    usable = prior.stage_logic_version == DECOMPOSE_STAGE_LOGIC_VERSION

    prior_by_text = prior.by_text()
    carried: dict[str, RequirementDerivation] = {}
    revised: dict[str, RequirementDerivation] = {}
    derived: list[str] = []
    matched_prior: set[str] = set()

    unmatched: list[RequirementRef] = []
    for requirement in registry:
        candidate = prior_by_text.get(requirement.text)
        if candidate is None:
            unmatched.append(requirement)
            continue

        matched_prior.add(candidate.text)
        # Text is identical, so the only question left is whether the answer on
        # file can still stand. `carry.decide` asks it — the tool moved under the
        # entry, the request that produced it would not be reissued, or it quotes
        # text the requirement no longer has. If it cannot stand the entry is not
        # carried, but it is also not *revised*: nothing about the requirement
        # changed, so it is derived fresh like any other the tool has no valid
        # answer for.
        decision = decide(
            requirement.id,
            prior=candidate,
            prior_key=candidate.carry_key,
            current_key=current_keys.get(requirement.id),
            stage_logic_matches=usable,
            still_applies=not stale_spans(candidate, requirement.text),
        )
        if decision.carried:
            carried[requirement.id] = candidate
        else:
            derived.append(requirement.id)

    # What is left on each side is the residue: requirements whose text moved, and
    # requirements that are new. Only a judgement can tell those apart.
    residue_prior = [
        derivation for derivation in prior.derivations if derivation.text not in matched_prior
    ]
    if unmatched and residue_prior and usable and client is not None:
        from acceptance.benchmark.alignment import align_obligations

        # ground truth = the prior wordings, reviewer = this run's. The returned
        # map is `current text -> prior text`, and it is bijective, so an inserted
        # requirement is left unmatched and correctly derived fresh.
        alignment = align_obligations(
            [derivation.text for derivation in residue_prior],
            [requirement.text for requirement in unmatched],
            client,
            stage=_STAGE,
        )
        prior_by_residue_text = {derivation.text: derivation for derivation in residue_prior}
        for requirement in unmatched:
            prior_text = alignment.get(requirement.text)
            candidate = prior_by_residue_text.get(prior_text) if prior_text else None
            if candidate is None:
                derived.append(requirement.id)
            else:
                revised[requirement.id] = candidate
                matched_prior.add(candidate.text)
    else:
        derived.extend(requirement.id for requirement in unmatched)

    removed = tuple(
        derivation for derivation in prior.derivations if derivation.text not in matched_prior
    )
    # Registry order, so two runs over the same input plan identically.
    order = {requirement.id: index for index, requirement in enumerate(registry)}
    return CarryPlan(
        carried=carried,
        revised=revised,
        derived=tuple(sorted(set(derived), key=lambda id_: order.get(id_, 0))),
        removed=removed,
        keys=dict(current_keys),
    )


def describe_removals(plan: CarryPlan) -> list[str]:
    """One line per dropped requirement, for the run's own report.

    A removal that is not reported is indistinguishable from a requirement that
    was never there, which is the whole reason this is not simply dropped on the
    floor.
    """
    return [
        f"{derivation.requirement_id}: {derivation.text.strip()} "
        f"({len(derivation.obligations)} obligation(s) dropped)"
        for derivation in plan.removed
    ]


def derivation_kind(plan: CarryPlan, requirement_id: str) -> Derivation:
    """How `requirement_id` was settled in this run."""
    if requirement_id in plan.carried:
        return Derivation.CARRIED
    if requirement_id in plan.revised:
        return Derivation.REVISED
    return Derivation.DERIVED
