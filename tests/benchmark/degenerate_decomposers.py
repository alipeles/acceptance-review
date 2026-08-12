"""Degenerate decomposers for the #195 regression suite.

Three clients, because two are not enough to prove anything. A suite that only
checks that bad decomposers score badly passes just as happily when the metric
is broken and returns zero for everyone — so `faithful_decomposer` exists to
show the metrics can reach 1.0 at all, and the other two are the failures the
issue names:

    faithful    emits exactly the ground truth
    lossy       drops content, and raises nothing
    permissive  keeps everything, invents more, and raises every question

The two failures are different defects and must be caught by different numbers.
A lossy decomposer is caught by recall; a permissive one is invisible to recall
by construction — it emits every ground-truth obligation — and is caught by
precision. "Stop raising questions" and "raise everything" are both fixes that
pass a one-directional suite, and #195 requires both to fail.

Neither is a stand-in for the real decomposer. The corpus holds rendered CLI
output, not transcripts, so the seven runs cannot be replayed (the same reason
`benchmark/corpus.py` gives for the rating-stability cases). What these exercise
is the scoring path over a decomposition whose content is known exactly.

Ids and text are seeded from the case's own labels rather than parsed out of the
prompt: the ground truth is what the decomposition is being scored against, so
seeding from it is what makes the score mean what it says.
"""

from __future__ import annotations

import json
import tempfile
from typing import Any

from acceptance.benchmark.case import GroundTruthLabels
from acceptance.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_MODEL
from acceptance.llm import Mode, ModelClient, TranscriptStore
from tests.support import (
    _EMPTY_BY_SCHEMA,
    _fake_response,
    _nest_obligations,
    _supplied_enum,
    constant_embedding_fn,
)

# Obligations the permissive decomposer adds on top of a faithful set, standing
# in for "splits every sentence into its own obligation". They align to nothing
# in any ground truth, which is what makes them cost precision.
_INVENTIONS = 6


def _obligation(oid: str, description: str, obligation_type: str) -> dict[str, Any]:
    return {
        "id": oid,
        "description": description,
        "type": obligation_type,
        "importance": "critical",
        "explicit": True,
        "observable_behavior": "...",
        "source_quote": description[:60],
    }


def _question(qid: str, question: str) -> dict[str, Any]:
    return {
        "id": qid,
        "question": question,
        "importance": "normal",
        "source_quote": question[:60],
    }


def _faithful(labels: GroundTruthLabels) -> dict[str, Any]:
    """Exactly the ground truth: every obligation with the type and symbols it
    is required to carry, and exactly the questions that should be raised."""
    obligations = []
    for o in labels.obligations:
        # An obligation whose type the corpus judged gets that type; one it took
        # no position on gets `functional`, which no case scores.
        obligation_type = o.expected_type.value if o.expected_type else "functional"
        obligations.append(_obligation(o.id, o.description, obligation_type))
    return {
        "obligations": obligations,
        "open_questions": [
            _question(q.id, q.description) for q in labels.open_questions if q.should_be_raised
        ],
        # Filled in by `decomposer`'s completion_fn, which can see the
        # requirement ids the call supplied; a label-seeded builder cannot.
        "requirement_dispositions": [],
    }


def _lossy(labels: GroundTruthLabels) -> dict[str, Any]:
    """Drops the last obligation and every open question.

    Dropping one obligation rather than all of them is deliberate: a decomposer
    that emits nothing is caught by any metric at all, including a broken one. A
    decomposer that emits almost everything is the realistic loss — it is what
    the corpus actually documents, where 19 of 20 obligations were fine and the
    twentieth had lost half its content.
    """
    faithful = _faithful(labels)
    return {
        "obligations": faithful["obligations"][:-1],
        "open_questions": [],
        "requirement_dispositions": [],
    }


def _permissive(labels: GroundTruthLabels) -> dict[str, Any]:
    """Keeps every ground-truth obligation, invents more, raises every question.

    Loses nothing, so its recall is perfect and #195's warning applies directly:
    absence of loss is not sufficient on its own. Every question is raised
    including the ones the task file answers, which is #178's defect and must
    not be rewarded here.
    """
    faithful = _faithful(labels)
    inventions = [
        _obligation(
            f"invented-fragment-{i}",
            f"An obligation split out of a clause that states no separate requirement ({i}).",
            "functional",
        )
        for i in range(_INVENTIONS)
    ]
    return {
        "obligations": faithful["obligations"] + inventions,
        "open_questions": [_question(q.id, q.description) for q in labels.open_questions],
        "requirement_dispositions": [],
    }


_BEHAVIOURS = {"faithful": _faithful, "lossy": _lossy, "permissive": _permissive}


def decomposer(labels: GroundTruthLabels, *, behaviour: str) -> ModelClient:
    """A decomposer whose output is decided by `behaviour`, not by the task."""
    build = _BEHAVIOURS[behaviour]
    # Derivation is partitioned by requirement (#204), so a task file of any
    # size draws several calls. The label-seeded payload models the decomposer's
    # WHOLE output, so it is emitted on the first call only — a real partitioned
    # decomposer emits each obligation and question in exactly one batch, and
    # repeating the set per batch would multiply it, with `_unique` renaming the
    # copies (`report-format`, `report-format-2`, ...). The union across calls is
    # what these cases score, and it is the ground truth exactly once.
    emitted = {"done": False}

    def completion_fn(**kwargs):
        spec = kwargs["response_format"]["json_schema"]
        name = spec["name"]
        if name == "_Decomposition":
            response = (
                {"obligations": [], "open_questions": [], "requirement_dispositions": []}
                if emitted["done"]
                else build(labels)
            )
            emitted["done"] = True
            # Seeded from a case's LABELS, which name obligations and questions
            # but no requirement ids — those come from the parse a double
            # bypasses. Every requirement is therefore declined, which leaves
            # the obligation and open-question content these cases score
            # untouched while keeping the response well-formed. Since M1.2.r2 a
            # response disposing nothing does not parse, so the empty list these
            # doubles used to send is no longer a neutral choice.
            # Seeded from a case's LABELS, which name obligations and questions
            # but no requirement ids — those come from the parse a double
            # bypasses. Since #204 an obligation is carried inside the
            # disposition that derived it, so it must have an owner: the whole
            # label set is attached to the first requirement this call was
            # given, and the rest are declined.
            #
            # Ownership is not what these cases score. They score the obligation
            # ids, descriptions and types, and the questions raised — all
            # untouched by which requirement carries them. Before #204 the
            # obligations sat in a flat list owned by nobody, which is no longer
            # representable.
            supplied = _supplied_enum("requirement_id", **kwargs)
            obligations = response.get("obligations", [])
            dispositions = []
            if supplied and obligations:
                dispositions.append(
                    {
                        "requirement_id": supplied[0],
                        "disposition": "yielded",
                        "obligation_id": obligations[0]["id"],
                        "more_obligation_ids": [o["id"] for o in obligations[1:]],
                    }
                )
            dispositions.extend(
                {
                    "requirement_id": rid,
                    "disposition": "no_obligation",
                    "reason": "seeded from ground-truth labels, which carry no requirement ids",
                }
                for rid in supplied[1 if (supplied and obligations) else 0 :]
            )
            response = {**response, "requirement_dispositions": dispositions}
            return _fake_response(json.dumps(_nest_obligations(response)))
        return _fake_response(json.dumps(_EMPTY_BY_SCHEMA[name]))

    return ModelClient(
        model=DEFAULT_MODEL,
        # RECORD because an injected completion_fn is only reached on the live
        # path; a REPLAY double would find an empty store and raise. No network
        # call happens — completion_fn stands in for the provider.
        mode=Mode.RECORD,
        store=TranscriptStore(tempfile.mkdtemp()),
        temperature=0.0,
        completion_fn=completion_fn,
        # As in `degenerate_judges`: the pipeline embeds before linking
        # (#259), and neutral vectors keep the degenerate DECOMPOSER the
        # only variable.
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        embedding_fn=constant_embedding_fn,
    )
