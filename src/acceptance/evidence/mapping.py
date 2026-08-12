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

from acceptance.config import DEFAULT_MAPPING_BATCH_SIZE
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import ModelClient, StrictResponseModel
from acceptance.model_base import PersistableModel
from acceptance.partition import partition
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

A test evidences an obligation when its assertions check that obligation's
observable behavior — the test would be expected to fail if that behavior were
missing or wrong. Map on what the test is AIMED at, not how strong it is:
whether the test genuinely discriminates the behavior is judged separately
(later), not here.

- A test may evidence MULTIPLE obligations — return several ids.
- A test may evidence NONE — it touches changed code only incidentally (setup,
  a helper, an unrelated assertion) and asserts nothing about any obligation.
  Return an empty `obligation_ids` for it; that is expected and correct.

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
    indeterminate_obligation_ids: list[str] = []
    unusable_answers: list[UnusableAnswer] = []


class _TestMapping(StrictResponseModel):
    test_id: str
    obligation_ids: list[str]
    rationale: str


class _Mappings(StrictResponseModel):
    mappings: list[_TestMapping]


def _render_prompt(obligations: list[Obligation], tests: list[DiscoveredTest]) -> str:
    lines = ["## Obligations", ""]
    for obligation in obligations:
        lines.append(f"- id={obligation.id}: {obligation.description}")
        if obligation.observable_behavior:
            lines.append(f"  observable behavior: {obligation.observable_behavior}")
    lines.append("")
    lines.append("## Candidate tests")
    for test in tests:
        lines.append("")
        lines.append(f"### {test.test_id}")
        lines.append(test.source or "(source unavailable)")
    return "\n".join(lines)


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
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _render_prompt(obligations, list(batch.items))},
        ]
        # Asked for with the ids of THIS batch: every obligation (each batch
        # judges all of them) but only this batch's tests. Parsed permissively so
        # one unusable id costs one judgment, not the whole batch — see
        # `supplied_ids`.
        allowed = {
            "test_id": batch_test_ids,
            "obligation_ids": sorted(valid_obligation_ids),
        }
        result = client.complete(
            messages,
            constrain(_Mappings, allowed),
            batch.request_partition(),
            parse_as=_Mappings,
            stage=_STAGE,
        )

        unusable_answers.extend(scan(result, allowed, _STAGE))

        batch_test_id_set = set(batch_test_ids)
        for mapping in result.mappings:
            # A batch may only speak for its own tests. Without this, a model that
            # echoes tests from a neighbouring batch would have its duplicate
            # judgment merged in alongside the real one, and the merged mapping
            # would depend on which batch answered last.
            if mapping.test_id not in batch_test_id_set:
                continue
            if mapping.test_id in seen_test_ids:
                continue  # already judged, in its own batch
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
