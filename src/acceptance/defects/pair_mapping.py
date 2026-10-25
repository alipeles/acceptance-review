"""Judge each (defect, test) pair: would this test fail if the code had this defect?

The second stage of the defect-first shape (#312, #314), and the one that
replaces the question #312 exists to retire. The old mapping stage asked whether
a test *purports to evidence* an obligation — a judgement with no fact of the
matter, so a miss was unrecoverable and no rating could be traced back to it.
This asks something existential with an answer, per pair.

**These verdicts are the review's test-evidence rating** (#316).
`defects/support.py` reduces them to the class itself.

## Who answers (#385, DR-379)

**Jev first, one pair per call.** Jev is shown targeted context
(`jev_context.py`): the delivered code around the defect with its lines
marked, the test with its imports and helpers, and the project code the test
calls, plus the requirement and the defect's description. Its probability that
the test fails decides the pair on its own at `JEV_FAILS_AT` or more and at
`JEV_SURVIVES_AT` or less.

**The model for the pairs in between, one pair per call**, with the
requirement text, the delivered code and the defect's description. It answers
yes or no in a schema with nothing else in it; no token probability is read.
When it gives no usable answer, the pair is recorded as unanswered, which a
rating counts as unknown. DR-379 had Jev's probability decide at 0.5 instead;
in the band where the model is asked that always reads "survives", turning a
judgement nobody obtained into a negative (owner's decision, 2026-10-25).

DR-379 measured this rule against the judge it replaces: 85.9% on 92 held-out
cases against 66.3%, at about a sixth of the cost per judgement. The cut-offs
were fitted there and are not re-fitted here. Two things differ from what it
measured, and both are recorded rather than hidden: the fallback was GPT-5.4
Mini, not the default model (amended 2026-10-24, after #412), and the cases
showed Jev a concrete edit where a pair here has only a described defect.

**Neither judge gives reasoning.** A verdict either produced carries an empty
`reason` and says who decided it in `judged_by`, and Jev's probability is kept
beside it. Findings stay at the static tier.

## Carry

Carry is per pair, and its key deliberately excludes everything about the
other pairs judged in the same run (DR-269): a verdict must not re-derive
because an unrelated pair was asked about. The unit carries while the defect's
own content, that test's source digest, the requirement and the code Jev is
shown are all unchanged — per TEST, never per file (DR-293).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from pathlib import Path

from pydantic import BaseModel, Field

from acceptance.carry import carry_key, decide
from acceptance.concurrency import map_calls
from acceptance.defects.jev_context import CodeIndex, TargetedContext, build_context
from acceptance.defects.pair_ranking import rank_pairs
from acceptance.defects.reachability import Pair, form_pairs, prefilter
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.jev import JEV_MODEL, JevProvider
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectSet,
    Obligation,
    PairJudge,
    PairVerdict,
    UnjudgedCause,
    UnjudgedPair,
)
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog

__all__ = [
    "JEV_FAILS_AT",
    "JEV_STAGE",
    "JEV_SURVIVES_AT",
    "PAIR_STAGE_LOGIC_VERSION",
    "PairMappingResult",
    "defect_text",
    "judge_pairs",
    "requirement_text",
    "source_digest",
]

# The model's stage, for the pairs Jev is unsure of. The name is the one the
# batched judge used, so a run's usage and its configured stage models keep
# reading under the same row.
_STAGE = "defect-to-test pair mapping"
JEV_STAGE = "defect-to-test pair judgement (Jev)"

# DR-379's rule. Fitted on 137 tuning cases and probably overfit — re-fit them
# when more labelled cases exist, never by moving them here to make a review
# come out differently.
JEV_FAILS_AT = 0.34
JEV_SURVIVES_AT = 0.24

# Bumped when this stage's own logic changes in a way that makes a stored verdict
# untrustworthy even though the defect and the test are untouched. 2: Jev, then
# the model, replaced the batched judge (#385).
PAIR_STAGE_LOGIC_VERSION = 2

# How many of a defect's tests the first ranked round asks about (#348). It
# used to also be how many tests shared one request; requests are one pair each
# since #385, so ranking is the only thing it still sizes.
DEFAULT_TESTS_PER_BATCH = 4

_JEV_SITUATION = (
    "We are checking which tests would catch which defects in a code change. A defect is "
    "one specific way the delivered code could be wrong. It is described, not applied: the "
    "code shown is the code as delivered, with the lines the defect concerns marked. Every "
    "defect is checked against many tests, so most tests were not written with it in mind, "
    "and many never execute the marked lines at all. A test catches a defect only when both "
    "are true: (1) with its own inputs, the test actually executes the marked lines; and (2) "
    "the defect would change something the test asserts on, so an assertion would fail or an "
    "error would be raised. The requirement, the test with its imports and helpers, the "
    "delivered code with the defect's lines marked, the code the test calls, and the defect "
    "are shown."
)

_JEV_QUESTIONS = {
    "fails": {
        "type": "noul",
        "instructions": (
            "If the delivered code had this defect, would this test fail? Judge both parts: "
            "does the test, with its own inputs, actually execute the marked lines; and if it "
            "does, would the defect change something the test asserts on?"
        ),
        "criteria": {
            "true": (
                "The test executes the marked lines, and the defect would change a value or "
                "behaviour the test checks, so an assertion would fail or an error would be "
                "raised."
            ),
            "false": (
                "The test never executes the marked lines (it calls other code, or its inputs "
                "always take a branch that skips them), or it executes them but nothing it "
                "asserts on would change."
            ),
        },
    }
}

_SYSTEM_PROMPT = """\
You are given one DEFECT — a specific way the delivered code could be wrong —
and one TEST from the same codebase, with the requirement the defect concerns
and the delivered code, the defect's lines marked.

THE QUESTION:

    If the delivered code contained THIS DEFECT, would THIS TEST fail?

Answer it as a matter of fact about the test's assertions, not about what the
test is named or what it appears to be about. A test fails on a defect only when
it executes the code the defect concerns and the defect changes something the
test actually asserts on. A test that exercises the defective code but asserts
nothing affected by the defect does NOT fail, and neither does one that stubs
out the defective behaviour.

Return `fails`: true if this test would fail on this defect, false if it would
not."""


class PairMappingResult(PersistableModel):
    """Every pair judged, every pair left unjudged, and every unusable answer.

    Kept together because they are one accounting of the pairs the stage was
    given: a pair in neither list was never formed, which is a third thing and
    not the same claim as either.
    """

    __test__ = False  # not a pytest test class

    verdicts: list[PairVerdict] = Field(default_factory=list)
    unjudged: list[UnjudgedPair] = Field(default_factory=list)
    unusable_answers: list[UnusableAnswer] = Field(default_factory=list)


class _Fails(StrictResponseModel):
    """The model's whole answer about one pair: yes or no, and nothing else."""

    fails: bool


class _LenientFails(BaseModel):
    """The answer as *parsed*, admitting one the schema forbids.

    A reply missing `fails`, or carrying something that is not a boolean, is
    no usable answer rather than an error that stops the review: the pair is
    recorded as unanswered and the rest of the run goes on. Parsing
    leniently is also what lets such a reply be recorded, so a replayed review
    reaches the same outcome without a call (`llm.py::_persist_live_call` keeps
    only what parses).
    """

    fails: object = None


def defect_text(defect: Defect) -> str:
    """The identity a verdict is carried on.

    Everything about the defect the prompt renders, and only that. The `id` is
    excluded on purpose: ids are composed from the obligation id, so rewording a
    requirement moves every defect id beneath it, and keying on one would
    re-judge defects whose content never changed. Same reasoning as
    `DefectSet.obligation_text`.
    """
    return canonical_json(
        {
            "type": defect.type.value,
            "description": defect.description,
            "code_refs": sorted(defect.code_refs),
        }
    )


def source_digest(test: DiscoveredTest) -> str:
    """Content digest of one test's own source.

    Per test, never per file (DR-293): a file-level digest re-judges every test
    in a module when any one of them is edited, and #314's headline behaviour is
    that adding one test costs only that test's pairs.
    """
    return hashlib.sha256((test.source or "").encode("utf-8")).hexdigest()


def requirement_text(obligation: Obligation) -> str:
    """The mandate text an obligation was derived from, else its description."""
    quoted = " ".join(span.text for span in obligation.source_spans if span.text)
    return quoted or obligation.description


def _defect_prose(defect: Defect) -> str:
    lines = [defect.description]
    if defect.expected_behavior:
        lines.append(f"What the code must do: {defect.expected_behavior}")
    if defect.defective_behavior:
        lines.append(f"What it would do instead: {defect.defective_behavior}")
    return "\n".join(lines)


def _test_name(test: DiscoveredTest) -> str:
    return test.test_id.split("::", 1)[1] if "::" in test.test_id else test.test_id


def _jev_state(pair: Pair, requirement: str, context: TargetedContext) -> dict[str, str]:
    return {
        "situation": _JEV_SITUATION,
        "change_request": requirement,
        "test": context.test,
        "test_name": _test_name(pair.test),
        "code": context.code,
        "code_the_test_calls": context.called,
        "defect": _defect_prose(pair.defect),
    }


def _subject(pair: Pair, requirement: str, context: TargetedContext) -> str:
    """Everything about this one pair the model is shown."""
    return "\n".join(
        [
            "## Requirement",
            "",
            requirement or "(no requirement text)",
            "",
            "## Defect",
            "",
            _defect_prose(pair.defect),
            "",
            "## Delivered code, the defect's lines marked",
            "",
            context.code or "(the defect names no code in this change)",
            "",
            "## Code the test calls",
            "",
            context.called or "(none found)",
            "",
            f"## Test {pair.test.test_id}",
            "",
            context.test or pair.test.source or "(source unavailable)",
        ]
    )


def _key(client: ModelClient, pair: Pair, requirement: str, context: TargetedContext) -> str:
    """What a stored verdict is valid under.

    Both judges' questions, the cut-offs and the pair's own inputs. The code Jev
    is shown is folded in as a digest: it reaches past the test and the defect,
    so a change to a function the test calls moves the answer and must move the
    key, which `defect_text` and `source_digest` alone would miss.
    """
    shown = canonical_json({"code": context.code, "test": context.test, "called": context.called})
    return carry_key(
        system_prompt=canonical_json(
            {"jev": [_JEV_SITUATION, _JEV_QUESTIONS], "model": _SYSTEM_PROMPT}
        ),
        response_schema=_Fails.model_json_schema(),
        model=client.model_for(_STAGE),
        temperature=client.temperature,
        seed=client.seed,
        stage_logic_version=PAIR_STAGE_LOGIC_VERSION,
        inputs={
            "defect_text": defect_text(pair.defect),
            "source_digest": source_digest(pair.test),
            "requirement": requirement,
            "shown_digest": hashlib.sha256(shown.encode("utf-8")).hexdigest(),
            "jev": {
                "model": JEV_MODEL,
                "fails_at": JEV_FAILS_AT,
                "survives_at": JEV_SURVIVES_AT,
            },
        },
    )


class _Decision:
    """One pair's outcome, handed back to the caller to record in pair order.

    `kills` is `None` when no judge produced an answer, and `unusable` then
    says why.
    """

    __slots__ = ("judged_by", "kills", "probability", "unusable")

    def __init__(
        self,
        kills: bool | None,
        judged_by: PairJudge,
        probability: float,
        unusable: UnusableAnswer | None = None,
    ) -> None:
        self.kills = kills
        self.judged_by = judged_by
        self.probability = probability
        self.unusable = unusable


def _decide_all(
    items: list[tuple[Pair, str, TargetedContext]],
    client: ModelClient,
    jev: JevProvider,
) -> list[_Decision]:
    """Jev, then the model where Jev is unsure, for every (pair, requirement,
    context) in `items`, returned in the same order.

    **Each distinct question is asked once.** Two pairs can put the same
    question: two defects with the same description and regions, against the
    same test. Asked concurrently, both would miss the store, both would call,
    and the recording would keep whichever answer was written last — so the run
    that recorded would use two answers where its replay uses one, and the two
    would differ (found scoring #385 on DR-379's held-out cases, where two
    mutants of one bug read identically once described). Asking once and
    sharing the answer makes the recording run and every replay agree.

    Records nothing (`concurrency.py`, rule 2): calls finish in any order, and
    the caller records in pair order.
    """
    states = [canonical_json(_jev_state(pair, req, ctx)) for pair, req, ctx in items]
    first_by_state: dict[str, int] = {}
    for index, state in enumerate(states):
        first_by_state.setdefault(state, index)
    jev_order = sorted(first_by_state.values())

    def ask_jev(index: int) -> float:
        pair, req, ctx = items[index]
        return jev.ask(
            client,
            _jev_state(pair, req, ctx),
            _JEV_QUESTIONS,
            JEV_STAGE,
            label=f"{pair.defect.id}/{pair.test.test_id}",
        )["fails"].probability

    asked = dict(zip(jev_order, map_calls(jev_order, ask_jev)))
    probabilities = [asked[first_by_state[state]] for state in states]

    unsure = [
        index
        for index, probability in enumerate(probabilities)
        if JEV_SURVIVES_AT < probability < JEV_FAILS_AT
    ]
    subjects = {index: _subject(*items[index]) for index in unsure}
    first_by_subject: dict[str, int] = {}
    for index in unsure:
        first_by_subject.setdefault(subjects[index], index)
    model_order = sorted(first_by_subject.values())

    def ask_model(index: int) -> object:
        pair, _, _ = items[index]
        return client.complete(
            assemble(
                [
                    Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
                    Block(BlockKind.SUBJECT, subjects[index]),
                ]
            ),
            _Fails,
            parse_as=_LenientFails,
            stage=_STAGE,
            label=f"{pair.defect.id}/{pair.test.test_id}",
        ).fails

    answered = dict(zip(model_order, map_calls(model_order, ask_model)))

    decisions: list[_Decision] = []
    for index, (pair, _, _) in enumerate(items):
        probability = probabilities[index]
        if probability >= JEV_FAILS_AT:
            decisions.append(_Decision(True, PairJudge.JEV, probability))
            continue
        if probability <= JEV_SURVIVES_AT:
            decisions.append(_Decision(False, PairJudge.JEV, probability))
            continue
        fails = answered[first_by_subject[subjects[index]]]
        if isinstance(fails, bool):
            decisions.append(_Decision(fails, PairJudge.MODEL, probability))
            continue
        decisions.append(
            _Decision(
                None,
                PairJudge.MODEL,
                probability,
                UnusableAnswer(
                    stage=_STAGE,
                    field="fails",
                    returned_id=f"{pair.defect.id}/{pair.test.test_id}",
                    reason=(
                        f"the answer carried no yes or no ({fails!r}), and Jev was unsure "
                        f"({probability:.3f}), so the pair has no verdict"
                    ),
                ),
            )
        )
    return decisions


def judge_pairs(
    defect_sets: list[DefectSet],
    tests: list[DiscoveredTest],
    change_set: ChangeSet,
    client: ModelClient,
    repo: Path = Path("."),
    unusable: UnusableAnswerLog | None = None,
    prior: list[PairVerdict] | None = None,
    tests_per_batch: int = DEFAULT_TESTS_PER_BATCH,
    skipped: Mapping[tuple[str, str], str] | None = None,
    stop_after_kills: int | None = None,
    requirements: Mapping[str, str] | None = None,
    jev: JevProvider | None = None,
) -> PairMappingResult:
    """Judge every pair the prefilter does not prove unreachable.

    `requirements` maps an obligation id to its requirement text, which both
    judges are shown; a defect whose obligation is missing from it is judged
    with none. `jev` replaces the Jev provider, for tests.

    With `stop_after_kills`, each defect's pairs are asked in order of
    similarity between the test and the defect's description, in rounds, and a
    defect is asked about no further once that many of its tests are recorded as
    catching it (#348). The rest are returned as `DEFECT_ALREADY_COVERED`. A
    defect that never reaches the number has every pair asked, as without it.
    `None` asks every pair in one pass, which is how the stage ran before.

    With `prior`, a verdict whose defect content, test source, requirement and
    shown code are all unchanged is reused and no judgement is issued for it —
    so adding one test between two continued runs costs that test's pairs and
    nothing else.

    `skipped` maps a pair to the sentence saying why the injection run already
    answered it well enough to spend the call elsewhere (#340,
    `mutation/verdicts.py::pairs_not_worth_asking`). Those pairs are not offered
    to the judge and are returned as `PASSED_UNDER_EDIT`.

    **With one exception, and it is the reason this runs in two passes.** If a
    defect's remaining pairs — the ones whose tests failed under the edit —
    produce no kill, the run has given nothing usable about that defect, and its
    skipped pairs are asked after all. That is the same reasoning that stops a
    `survived` attempt skipping anything, arriving one step later: a saving that
    bought nothing must not also cost the defect its judgement. It has to happen
    here rather than in the caller, because the rating is derived from what this
    returns and must never see the intermediate state.
    """
    defects = [defect for entry in defect_sets for defect in entry.defects]
    pairs = form_pairs(defects, tests)
    judged, unjudged = prefilter(pairs, repo, change_set)

    # AFTER the prefilter, so a pair it proves unreachable keeps that cause. The
    # two are different claims and the prefilter's is the stronger one.
    skipped = skipped or {}
    held_back = [pair for pair in judged if pair.key in skipped]
    judged = [pair for pair in judged if pair.key not in skipped]

    prior_by_identity = {(entry.defect_text, entry.test_id): entry for entry in (prior or [])}

    # Ranked once over every pair either pass could ask, so a pair's rank means
    # the same thing in both and the recorded rank is its place among ALL of its
    # defect's candidate tests, not among whichever subset one pass saw.
    ranks = rank_pairs(judged + held_back, client, _STAGE) if stop_after_kills is not None else {}

    # Built lazily, and once: the walk reads every module, so a run that judges
    # nothing should not pay for it.
    index: list[CodeIndex] = []

    def code_index() -> CodeIndex:
        if not index:
            index.append(CodeIndex(repo))
        return index[0]

    def _judge(offered: list[Pair]) -> tuple[list[PairVerdict], list[UnjudgedPair]]:
        """Carry what can be carried, ask about the rest, read the answers.

        Factored out because #340's second pass reuses every step of it. It
        appends nothing to the enclosing lists, so the two passes cannot
        interleave their results by accident.
        """

        def ask(pairs: list[Pair]) -> tuple[list[PairVerdict], list[UnjudgedPair]]:
            return _carry_and_ask(
                pairs,
                client,
                jev or JevProvider(),
                change_set,
                code_index,
                requirements or {},
                prior_by_identity,
                unusable,
            )

        if stop_after_kills is None:
            return ask(offered)
        return _walk_ranked(offered, ranks, stop_after_kills, tests_per_batch, ask)

    verdicts, unanswered = _judge(judged)
    unjudged.extend(unanswered)

    # The exception in the docstring. A defect whose asked pairs produced a kill
    # keeps its saving; one that produced none pays for the full judgement.
    killed = {entry.defect_id for entry in verdicts if entry.kills}
    revisit = [pair for pair in held_back if pair.defect.id not in killed]
    dropped = [pair for pair in held_back if pair.defect.id in killed]

    if revisit:
        more_verdicts, more_unanswered = _judge(revisit)
        verdicts.extend(more_verdicts)
        unjudged.extend(more_unanswered)

    unjudged.extend(
        UnjudgedPair(
            defect_id=pair.defect.id,
            test_id=pair.test.test_id,
            cause=UnjudgedCause.PASSED_UNDER_EDIT,
            reason=skipped[pair.key],
        )
        for pair in dropped
    )

    # Sorted on the pair identity rather than on the order pairs were formed in,
    # so a carried verdict and a fresh one land in the same place. Byte-identical
    # reruns depend on it.
    return PairMappingResult(
        verdicts=sorted(verdicts, key=lambda entry: (entry.defect_id, entry.test_id)),
        unjudged=sorted(unjudged, key=lambda entry: (entry.defect_id, entry.test_id)),
        unusable_answers=[],
    )


def _walk_ranked(
    offered: list[Pair],
    ranks: Mapping[tuple[str, str], int],
    stop_after_kills: int,
    tests_per_batch: int,
    ask: Callable[[list[Pair]], tuple[list[PairVerdict], list[UnjudgedPair]]],
) -> tuple[list[PairVerdict], list[UnjudgedPair]]:
    """Ask each defect's pairs best-ranked first, in rounds, until it is covered.

    **Rounds grow.** The first asks each uncovered defect's top `tests_per_batch`
    tests, and every round after asks twice as many as the one before. A covered
    defect stops after its first round or two, where the measured first kill sits
    (median rank 1 to 3), and a defect with no kill among several hundred tests
    is walked in about seven rounds rather than a hundred. Rounds are sequential
    because each one depends on the kills the last one found; the calls within a
    round are still issued concurrently.

    **A pair not asked is recorded, never dropped** (DR-314): as
    `DEFECT_ALREADY_COVERED`, naming its rank and the tests that covered the
    defect. It can only be produced for a defect that reached `stop_after_kills`,
    because a defect that did not has had every pair asked by the time its queue
    runs out.
    """
    queues: dict[str, list[Pair]] = {}
    for pair in offered:
        queues.setdefault(pair.defect.id, []).append(pair)
    for pairs in queues.values():
        pairs.sort(key=lambda pair: (ranks[pair.key], pair.test.test_id))

    kills: dict[str, list[str]] = {defect_id: [] for defect_id in queues}
    asked_up_to = dict.fromkeys(queues, 0)
    verdicts: list[PairVerdict] = []
    unjudged: list[UnjudgedPair] = []

    def open_defects() -> list[str]:
        return sorted(
            defect_id
            for defect_id, pairs in queues.items()
            if asked_up_to[defect_id] < len(pairs) and len(kills[defect_id]) < stop_after_kills
        )

    width = max(1, tests_per_batch)
    while pending := open_defects():
        round_pairs: list[Pair] = []
        for defect_id in pending:
            start = asked_up_to[defect_id]
            round_pairs.extend(queues[defect_id][start : start + width])
            asked_up_to[defect_id] = start + width
        round_verdicts, round_unjudged = ask(round_pairs)
        verdicts.extend(round_verdicts)
        unjudged.extend(round_unjudged)
        for verdict in round_verdicts:
            if verdict.kills:
                kills[verdict.defect_id].append(verdict.test_id)
        width *= 2

    for defect_id, pairs in queues.items():
        remaining = pairs[asked_up_to[defect_id] :]
        if not remaining:
            continue
        covered_by = sorted(kills[defect_id])
        for pair in remaining:
            rank = ranks[pair.key]
            unjudged.append(
                UnjudgedPair(
                    defect_id=defect_id,
                    test_id=pair.test.test_id,
                    cause=UnjudgedCause.DEFECT_ALREADY_COVERED,
                    reason=(
                        f"not asked: ranked {rank} by similarity to the defect, below "
                        f"{len(covered_by)} test(s) already recorded as catching it"
                    ),
                    rank=rank,
                    covered_by=covered_by,
                )
            )
    return verdicts, unjudged


def _carry_and_ask(
    judged: list[Pair],
    client: ModelClient,
    jev: JevProvider,
    change_set: ChangeSet,
    code_index: Callable[[], CodeIndex],
    requirements: Mapping[str, str],
    prior_by_identity: dict[tuple[str, str], PairVerdict],
    unusable: UnusableAnswerLog | None,
) -> tuple[list[PairVerdict], list[UnjudgedPair]]:
    """The judgement itself, over exactly the pairs handed to it.

    A pair comes back unjudged only when Jev was unsure and the model gave no
    usable answer: recorded as `UNANSWERED`, never defaulted to *survives*,
    because a rating counts it as unknown and that is the honest reading.
    """
    carried: list[PairVerdict] = []
    to_ask: list[tuple[Pair, str, TargetedContext, str]] = []
    for pair in judged:
        requirement = requirements.get(pair.defect.obligation_id, "")
        context = build_context(pair.defect, pair.test, change_set, code_index())
        current = _key(client, pair, requirement, context)
        candidate = prior_by_identity.get((defect_text(pair.defect), pair.test.test_id))
        decision = decide(
            f"{pair.defect.id}/{pair.test.test_id}",
            prior=candidate,
            prior_key=candidate.carry_key if candidate else None,
            current_key=current,
        )
        if decision.carried:
            # Re-identified onto this run's defect id, which may differ from the
            # one the verdict was recorded under: the carry matched on content.
            carried.append(
                candidate.model_copy(
                    update={"defect_id": pair.defect.id, "carried_from": candidate.carry_key}
                )
            )
        else:
            to_ask.append((pair, requirement, context, current))

    # Issued concurrently and consumed in pair order, so the verdicts and the
    # unusable-answer log read the same however the calls finished.
    decisions = _decide_all([(pair, req, ctx) for pair, req, ctx, _ in to_ask], client, jev)

    fresh: list[PairVerdict] = []
    unjudged: list[UnjudgedPair] = []
    for (pair, _, _, key), decision in zip(to_ask, decisions):
        if decision.unusable is not None and unusable is not None:
            unusable.record([decision.unusable])
        if decision.kills is None:
            unjudged.append(
                UnjudgedPair(
                    defect_id=pair.defect.id,
                    test_id=pair.test.test_id,
                    cause=UnjudgedCause.UNANSWERED,
                    reason=decision.unusable.reason if decision.unusable else "no answer",
                )
            )
            continue
        fresh.append(
            PairVerdict(
                defect_id=pair.defect.id,
                test_id=pair.test.test_id,
                kills=decision.kills,
                defect_text=defect_text(pair.defect),
                test_digest=source_digest(pair.test),
                carry_key=key,
                judged_by=decision.judged_by,
                jev_probability=decision.probability,
            )
        )
    return carried + fresh, unjudged
