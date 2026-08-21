"""Test-to-obligation mapping (M4.2, §9.1).

Maps each candidate test (from M4.1 discovery) to the obligation(s) it
*purports* to evidence, and flags obligations with no mapped test. Discovery
is recall-forward — it surfaces every test that touches changed code (by call
graph, reference, import, or naming). This is the precision step: which
obligation(s), if any, is a test's *assertions* actually aimed at?

"Purports to evidence" is deliberately weaker than "proves": a test maps to an
obligation when its assertions target that obligation's observable behavior,
not when it does so *well*. Whether the test genuinely discriminates the
behavior (its strength) is M5's job, judged separately over this map.

The judgment is semantic, so it is a schema-constrained model call through the
M0.4 harness — recorded for replay, never a live call in tests. `apply_test_mapping`
then writes each obligation's mapped test ids into `Obligation.test_evidence`,
the field the §11.1 mapping-accuracy metric (scoring.py) already scores.
"""

from __future__ import annotations

from pydantic import Field

from acceptance.config import DEFAULT_MAPPING_BATCH_SIZE
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.review_state import Obligation
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog, constrain, scan

_STAGE = "test-to-obligation mapping"

_SYSTEM_PROMPT = """\
You map each candidate test to the acceptance obligation(s) it PURPORTS to
evidence. The candidate tests were found because they touch changed code (they
call, reference, import, or are named after a changed symbol) — that is a
RECALL signal, not proof they test any obligation. Your job is the precision
step: for each test, decide which obligation(s), if any, its assertions are
actually aimed at.

THE TEST, applied to one obligation at a time:

    Would this test be expected to FAIL if that obligation's behavior were
    missing or wrong?

If yes, the test evidences it. If no, it does not — however much the two have
in common. Map on what the test is AIMED at, not how strong it is: whether the
test genuinely discriminates the behavior is judged separately (later), not here.

- A test may evidence MULTIPLE obligations. Apply THE TEST to each obligation
  separately and return every id that passes it — not the single best one, and
  not every id that is nearby. "Touches the same file", "is about the same
  feature", "exercises code this obligation depends on" and "is thematically
  related" all FAIL the test. The assertions have to bear on that obligation's
  own behavior.
- Obligations are not guaranteed to be independent of one another. Two of them
  may state the same demand in different words, at different levels of detail,
  or from different angles — one may even be a demand for evidence about
  another. A test whose assertions bear on what several obligations are about
  passes THE TEST for each of them, and returning only the closest one leaves
  the rest looking untested while their evidence sits in the response.
  Do not choose between overlapping obligations.
  (One way overlap arises, as an illustration only — never assume the mandate is
  shaped this way: a mandate states a behavior, and separately asks that a test
  assert that behavior. Both become obligations and one test evidences both.)
  This is not licence to map widely. Every id returned must pass THE TEST on its
  own. The rule says an obligation that passes must not be dropped because a
  closer one exists — not that a near miss may be included because a hit does.
- A test may evidence NONE — it touches changed code only incidentally (setup,
  a helper, an unrelated assertion) and asserts nothing about any obligation.
  Return an empty `obligation_ids` for it; that is expected and correct.
  "Overlapping obligations get every id" does not weaken this: a test aimed at
  nothing still maps to nothing.

Most tests evidence one obligation or none. A test returning five or more ids is
usually a test whose ids were not each put to THE TEST — re-read it and drop the
ones that would still pass if that obligation's behavior vanished.

For each test return its `test_id`, the `obligation_ids` it purports to
evidence (possibly empty), and a short `rationale`. Use only obligation ids
from the list; use only test ids from the candidate list."""


class TestMapping(PersistableModel):
    """Which obligation(s) one candidate test purports to evidence."""

    __test__ = False  # not a pytest test class

    test_id: str
    obligation_ids: list[str]
    rationale: str


class MappingResult(PersistableModel):
    mappings: list[TestMapping]
    unmapped_obligation_ids: list[str]  # obligations no test purports to evidence
    # Obligations whose mapping could not be honoured. Disjoint from
    # `unmapped_obligation_ids` in meaning: unmapped is a substantive negative
    # answer, this is the absence of an answer.
    indeterminate_obligation_ids: list[str] = Field(default_factory=list)
    unusable_answers: list[UnusableAnswer] = Field(default_factory=list)


class _TestMapping(StrictResponseModel):
    test_id: str
    obligation_ids: list[str]
    rationale: str


class _Mappings(StrictResponseModel):
    mappings: list[_TestMapping]


def _obligations_block(obligations: list[Obligation]) -> Block:
    """Every obligation, in every batch — the part of a mapping request that does
    not move between the batches of one run.

    This is not `prompt.obligations_block`: mapping shows each obligation's
    observable behavior and no type, because it is matching tests to behavior
    rather than citing criteria against a diff. Different content, so a block of
    its own kind rather than a pretence of sharing with the coverage stages.
    """
    lines = ["## Obligations", ""]
    for obligation in obligations:
        lines.append(f"- id={obligation.id}: {obligation.description}")
        if obligation.observable_behavior:
            lines.append(f"  observable behavior: {obligation.observable_behavior}")
    return Block(BlockKind.OBLIGATIONS, "\n".join(lines))


def _tests_block(tests: list[DiscoveredTest]) -> Block:
    """This batch's candidate tests — the only thing that differs between the
    mapping calls of one run, which is why it goes last."""
    lines = ["## Candidate tests"]
    for test in tests:
        lines.append("")
        lines.append(f"### {test.test_id}")
        lines.append(test.source or "(source unavailable)")
    return Block(BlockKind.SUBJECT, "\n".join(lines))


def map_tests_to_obligations(
    obligations: list[Obligation],
    tests: list[DiscoveredTest],
    client: ModelClient,
    batch_size: int = DEFAULT_MAPPING_BATCH_SIZE,
    unusable: UnusableAnswerLog | None = None,
) -> MappingResult:
    """Map each candidate test to the obligation(s) it purports to evidence.

    The tests are partitioned across several calls, with every obligation
    repeated in each call, because one call asking for tests x obligations
    judgments sheds work silently past roughly a thousand of them (DR-164).
    Recall is unaffected: every test is still judged against every obligation,
    just not all in one response.
    """
    valid_obligation_ids = {o.id for o in obligations}
    if not tests:
        # No candidates to map — every obligation is unmapped. No model call.
        return MappingResult(mappings=[], unmapped_obligation_ids=sorted(valid_obligation_ids))

    mapped_obligation_ids: set[str] = set()
    mappings: list[TestMapping] = []
    seen_test_ids: set[str] = set()
    unusable_answers: list[UnusableAnswer] = []

    for batch in partition(tests, batch_size, key=lambda test: test.test_id):
        batch_test_ids = [test.test_id for test in batch.items]
        messages = assemble(
            [
                _obligations_block(obligations),
                Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
                _tests_block(list(batch.items)),
            ]
        )
        # Two id sets, and the difference between them is deliberate (#302).
        #
        # `detectable` is what a returned id is CHECKED against. `constrained` is
        # what the response SCHEMA restricts. They differ on `test_id`: its ids
        # are this batch's, so naming them in the schema gives every batch of a
        # run a different schema — and the provider's prompt-cache key covers the
        # schema, so no two batches could ever share a cached prefix. Measured:
        # 461 of 464 recorded mapping calls cached nothing, over the 1,729-token
        # prefix `_obligations_block` exists to keep in front.
        #
        # This stage and no other. Decompose's within-run prefix is 694 tokens
        # and linking's are 583 and 509, against a provider minimum of 1,024, so
        # neither can be served from cache whatever its schema does and both keep
        # their enums (`docs/DR-302-per-batch-id-enum.md`).
        #
        # `obligation_ids` is identical in every batch of a run, so constraining
        # it splits no prefix and it stays exactly as DR-163 left it — which is
        # the field #163's defect was actually about, the model naming
        # obligations it had read out of the pasted test sources.
        #
        # Dropping `test_id` from the schema costs nothing that was load-bearing:
        # the batch-membership check below predates the enum and outlives it, and
        # `scan` still records a foreign id. Parsed permissively either way, so
        # one unusable id costs one judgment and not the whole batch.
        detectable = {
            "test_id": batch_test_ids,
            "obligation_ids": sorted(valid_obligation_ids),
        }
        constrained = {"obligation_ids": detectable["obligation_ids"]}
        result = client.complete(
            messages,
            constrain(_Mappings, constrained),
            batch.request_partition(),
            parse_as=_Mappings,
            stage=_STAGE,
        )

        unusable_answers.extend(scan(result, detectable, _STAGE))

        batch_test_id_set = set(batch_test_ids)
        answered_in_batch: set[str] = set()
        for mapping in result.mappings:
            # A batch may only speak for its own tests. Without this, a model that
            # echoes tests from a neighbouring batch would have its duplicate
            # judgment merged in alongside the real one, and the merged mapping
            # would depend on which batch answered last.
            if mapping.test_id not in batch_test_id_set:
                continue
            if mapping.test_id in seen_test_ids:
                # Judged twice. Recorded rather than dropped: either the two
                # judgments agree, in which case the record is harmless, or they
                # disagree, in which case keeping the first silently is the tool
                # choosing between two answers it has no basis to choose between.
                unusable_answers.append(
                    UnusableAnswer(
                        stage=_STAGE,
                        field="test_id",
                        returned_id=mapping.test_id,
                        reason="judged more than once; the first judgment stands",
                    )
                )
                continue
            answered_in_batch.add(mapping.test_id)
            seen_test_ids.add(mapping.test_id)
            obligation_ids = [oid for oid in mapping.obligation_ids if oid in valid_obligation_ids]
            mapped_obligation_ids.update(obligation_ids)
            mappings.append(
                TestMapping(
                    test_id=mapping.test_id,
                    obligation_ids=obligation_ids,
                    rationale=mapping.rationale,
                )
            )

        # A batch can come back short: nothing in a list-shaped response requires
        # one entry per test, and no schema ever did — an enum restricts which
        # values may appear, never how many entries do. Left unrecorded, a
        # skipped test is indistinguishable from a test judged to evidence
        # nothing, and any obligation resting on it is then reported as having no
        # test at all. That is the #163 defect shape: the review telling the
        # reader their change is untested when the truth is that it went
        # unreviewed. Sorted so the record depends only on which answers were
        # missing, not on the order the response listed the others.
        for missing_test_id in sorted(batch_test_id_set - answered_in_batch):
            unusable_answers.append(
                UnusableAnswer(
                    stage=_STAGE,
                    field="test_id",
                    returned_id=missing_test_id,
                    reason="no judgment returned for this test",
                )
            )

    # Sorted, not left in response order, so the merged result depends only on
    # which judgments came back and not on the order the batches returned them.
    mappings.sort(key=lambda mapping: mapping.test_id)
    unmapped = sorted(valid_obligation_ids - mapped_obligation_ids)

    # An obligation that ended up unmapped, in a run where some answer could not
    # be honoured, is INDETERMINATE rather than unmapped. Every batch judges every
    # obligation, so the answer that would have mapped it may be exactly the one
    # we could not read — and "no test evidences this" is a substantive claim we
    # are no longer entitled to make. An obligation that WAS mapped keeps its
    # judgment: that is a positive answer we could honour.
    if unusable_answers:
        if unusable is not None:
            unusable.record(unusable_answers)
            unusable.mark_indeterminate(unmapped)
        return MappingResult(
            mappings=mappings,
            unmapped_obligation_ids=[],
            indeterminate_obligation_ids=unmapped,
            unusable_answers=unusable_answers,
        )
    return MappingResult(mappings=mappings, unmapped_obligation_ids=unmapped)


def apply_test_mapping(obligations: list[Obligation], result: MappingResult) -> list[Obligation]:
    """Return copies of `obligations` with `test_evidence` populated from the
    mapping — the join the §11.1 mapping-accuracy metric scores."""
    tests_by_obligation: dict[str, list[str]] = {}
    for mapping in result.mappings:
        for obligation_id in mapping.obligation_ids:
            tests_by_obligation.setdefault(obligation_id, []).append(mapping.test_id)

    return [
        obligation.model_copy(
            update={"test_evidence": sorted(tests_by_obligation.get(obligation.id, []))}
        )
        for obligation in obligations
    ]
