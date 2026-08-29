"""The summary pass, re-shaped: the model partitions the summary, then disposes each span.

`twophase.py` measures the summary pass as it stands — one call, free-text
`source_quote`, an unbounded list of obligations. Over 5 trials it returned 3
obligations every time, one of which restates `constraint-03`, and 4 of the 15
quotations did not land in the summary at all.

Every arm here changes the same three things, because they are one design:

1. **The response carries the partition.** `spans` first, then
   `span_dispositions`. The model must commit to a division of the summary
   before it says anything about coverage, and every span it wrote must be
   disposed exactly once. In the current shape the partition happens in the
   model's head and only its conclusions are visible.
2. **`source_quote` is never written by the model.** Code sets it from the span.
   The model cannot paraphrase a quotation it does not author, which is the
   failure `session-state/317.md` recorded on 2026-08-29 — the model repairs the
   task file's grammar when quoting, so the quote stops matching the source.
3. **The user message shows the derived obligations as id, description and type
   only.** No bullet text, no quotations. The bullets are what the summary
   elaborates, and showing them is what invites an answer about them.

A malformed response is rejected **whole** and retried once. Nothing is filtered
or rewritten by content: `findings.md` §5's drop rule is a different proposal,
and mixing it in here would make this arm unmeasurable.

## The arms

- **v4** (`work-sp`) — `covered`/`uncovered` union, the obligation carried inline
  on the uncovered shape. Result: 2 spans, both covered, 5/5 draws. Both genuine
  requirements lost.
- **v5** (`work-sp2`) — adds `covered_because` so the coverage argument is
  visible, and asks for a counterfactual test in prose. Result: 3 spans in 3 of 5
  draws, every span covered in 5 of 5. The arguments contain the gap ("later work
  **can** refer to them by identifier") and answer `covered` anyway.
- **v6** (`work-sp3`) — one flat shape per span, `counterexample` written BEFORE
  `disposition`, and the verdict is rejected when it disagrees with what was
  written. No obligation fields in the call at all; obligations for uncovered
  spans are authored afterwards by the ordinary per-bullet decomposer, which
  `findings.md` §2 measures as over-answering 0 times in 68 non-task batches.

An arm is selected with `--arm`, so a superseded arm stays runnable and its saved
draws stay readable rather than becoming a shape nothing can parse.

## Paired against the baseline, deliberately

Phase 1 is not re-run. Each draw reuses the obligations one saved
`twophase.py` trial derived, at that trial's seed, so every arm and the baseline
see the same five inputs and differ only in the summary pass. Phase 1 varied
across those trials (25, 26, 30, 25, 25 obligations), so re-running it would
confound the comparison and cost 20 further calls.

## The cache is bypassed

Like `draw.py` and `twophase.py`, this calls `ModelClient._live_call`, which
neither reads nor writes `.acceptance/cache/transcripts/`. A saved draw keeps the
response and the request key, never the request, so it is evidence rather than a
transcript.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

import draw
from pydantic import create_model

from acceptance.config import RunConfig
from acceptance.llm import Mode, StrictResponseModel, request_key
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.requirement.obligations import (
    _SYSTEM_PROMPT,
    _DecomposedObligation,
    _Decomposition,
    _user_prompt,
)
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import RequirementRef, RequirementSection
from acceptance.source_ref import TextSpan
from acceptance.supplied_ids import constrain

HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts-v2-baseline"

# Dropped from the obligation the v4/v5 arms ask for. `source_quote` because
# code sets it from the span; `explicit` because all 24 `explicit=false`
# obligations in the corpus are `task-*` and `findings.md` records that dropping
# it here is safe — `coverage/open_questions.py` still sets it where it means
# something. The v6 arm asks for no obligation fields at all.
_OMITTED_OBLIGATION_FIELDS = {"source_quote", "explicit"}


# --------------------------------------------------------------------------
# the response shapes


def _obligation_model() -> type:
    """`_DecomposedObligation` minus the two fields the v4/v5 arms do not ask for.

    Rebuilt from the real model's field set rather than hand-written, so a field
    added upstream reaches this experiment instead of silently diverging.
    """
    fields = {
        name: (field.annotation, ...)
        for name, field in _DecomposedObligation.model_fields.items()
        if name not in _OMITTED_OBLIGATION_FIELDS
    }
    return create_model("_SpanObligation", __base__=StrictResponseModel, **fields)


def _model_v5() -> type:
    """`spans`, then a union of a covered shape and an uncovered shape."""
    obligation = _obligation_model()
    covered = create_model(
        "_CoveredSpan",
        __base__=StrictResponseModel,
        disposition=(Literal["covered"], ...),
        span_index=(int, ...),
        covered_by=(list[str], ...),
        covered_because=(str, ...),
    )
    uncovered = create_model(
        "_UncoveredSpan",
        __base__=StrictResponseModel,
        disposition=(Literal["uncovered"], ...),
        span_index=(int, ...),
        not_covered_because=(str, ...),
        obligation=(obligation, ...),
    )
    return create_model(
        "_SummarySpans",
        __base__=StrictResponseModel,
        spans=(list[str], ...),
        span_dispositions=(list[covered | uncovered], ...),
    )


def _model_v6() -> type:
    """One flat shape per span, and `disposition` comes LAST.

    Field order is the point of this arm. The model writes `nearest`, then the
    `counterexample`, and only then the verdict — so the verdict is produced
    after the argument rather than justified backwards from it. A union would put
    the verdict in the shape selector, which is the opposite ordering, so there
    is no `anyOf` here.

    No obligation fields. `findings.md` §2 measures the ordinary per-bullet
    decomposer over-answering 0 times in 68 non-task batches, so authoring an
    obligation is given to that call rather than to this one.
    """
    verdict = create_model(
        "_SpanVerdict",
        __base__=StrictResponseModel,
        span_index=(int, ...),
        nearest=(list[str], ...),
        counterexample=(str, ...),
        disposition=(Literal["uncovered", "covered"], ...),
    )
    return create_model(
        "_SummarySpans",
        __base__=StrictResponseModel,
        spans=(list[str], ...),
        span_dispositions=(list[verdict], ...),
    )


# --------------------------------------------------------------------------
# the request


def _summary(root: Path):
    """The one `(task)` requirement this pass is about."""
    source = (root / draw.TASK_COPY).read_text(encoding="utf-8")
    registry = build_registry(parse_task_file(source))
    summaries = [r for r in registry if r.section is RequirementSection.TASK]
    if len(summaries) != 1:
        raise SystemExit(f"expected exactly one (task) requirement, found {len(summaries)}")
    return summaries[0]


def derived_obligations(trial_dir: Path) -> list[dict]:
    """id, description and type for every obligation a saved phase 1 yielded.

    Read from the saved phase-1 responses rather than from that trial's
    `obligations.json`, which carries only the description and the requirement it
    came from — the user message needs the id and the type as well.
    """
    listed: list[dict] = []
    for path in sorted((trial_dir / "phase1").glob("batch-*.json")):
        parsed = json.loads(json.loads(path.read_text(encoding="utf-8"))["response"])
        for entry in parsed["requirement_dispositions"]:
            if entry.get("disposition") != "yielded":
                continue
            for item in [entry.get("obligation")] + (entry.get("more_obligations") or []):
                if item:
                    listed.append(
                        {"id": item["id"], "type": item["type"], "description": item["description"]}
                    )
    return listed


def user_message(listed: list[dict], summary_text: str) -> str:
    lines = ["Obligations already derived from the bullets:", ""]
    for item in listed:
        lines.append(f"[{item['id']}] ({item['type']}) {item['description']}")
    lines.extend(["", "The summary:", "", summary_text])
    return "\n".join(lines)


def _messages(prompt: Path, listed: list[dict], summary_text: str) -> list[dict]:
    return assemble(
        [
            Block(BlockKind.INSTRUCTIONS, prompt.read_text(encoding="utf-8")),
            Block(BlockKind.SUBJECT, user_message(listed, summary_text)),
        ]
    )


# --------------------------------------------------------------------------
# rule 5 — reject whole, never filter by content


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _shared_reason(parsed: dict, summary_text: str) -> str | None:
    """The checks every arm applies.

    The substring test collapses runs of whitespace on both sides before
    comparing. The summary is hard-wrapped in the task file, so a character-for-
    character test would reject a span for containing a space where the source
    has a newline — a property of the file's line width, not of the answer. The
    report states the strict result as well, so the looseness is visible rather
    than assumed.
    """
    spans = parsed["spans"]
    haystack = _squash(summary_text)
    for index, span in enumerate(spans):
        if _squash(span) not in haystack:
            return f"span {index} is not a substring of the summary: {span!r}"

    seen: dict[int, int] = {}
    for entry in parsed["span_dispositions"]:
        index = entry["span_index"]
        if not 0 <= index < len(spans):
            return f"span_index {index} is out of range (spans: {len(spans)})"
        seen[index] = seen.get(index, 0) + 1
    for index in range(len(spans)):
        count = seen.get(index, 0)
        if count != 1:
            return f"span {index} was disposed {count} times, not once"
    return None


def _reason_v5(parsed: dict, summary_text: str, listed_ids: set[str]) -> str | None:
    shared = _shared_reason(parsed, summary_text)
    if shared:
        return shared
    for entry in parsed["span_dispositions"]:
        if entry["disposition"] != "covered":
            continue
        if not entry["covered_by"]:
            # Strict mode cannot express "at least one" on an array (`minItems`
            # is unsupported, which is why `_Yielded` splits head from rest), so
            # a `covered` span naming nothing is caught here.
            return f"span {entry['span_index']} is covered by nothing"
        for obligation_id in entry["covered_by"]:
            if obligation_id not in listed_ids:
                return f"covered_by names {obligation_id!r}, which was not on the list shown"
    return None


def _is_none(counterexample: str) -> bool:
    """The single word `none`, allowing surrounding space and a full stop."""
    return _squash(counterexample).lower().rstrip(".") == "none"


def _reason_v6(parsed: dict, summary_text: str, listed_ids: set[str]) -> str | None:
    shared = _shared_reason(parsed, summary_text)
    if shared:
        return shared
    for entry in parsed["span_dispositions"]:
        index = entry["span_index"]
        for obligation_id in entry["nearest"]:
            if obligation_id not in listed_ids:
                return f"nearest names {obligation_id!r}, which was not on the list shown"
        wrote_counterexample = not _is_none(entry["counterexample"])
        if entry["disposition"] == "covered" and wrote_counterexample:
            return (
                f"span {index} is covered but its counterexample is not the single "
                f"word 'none': {entry['counterexample']!r}"
            )
        if entry["disposition"] == "uncovered" and not wrote_counterexample:
            return f"span {index} is uncovered but wrote no counterexample"
    return None


ARMS = {
    "v5": {
        "prompt": PROMPTS / "phase2-system-v5-counterfactual.txt",
        "model": _model_v5,
        "reason": _reason_v5,
    },
    "v6": {
        "prompt": PROMPTS / "phase2-system-v6-counterexample-first.txt",
        "model": _model_v6,
        "reason": _reason_v6,
    },
    # v7 is v6's shape and rules exactly. Two things move: the partition rule
    # gains "do not split a qualifier from the predicate it qualifies" — v6 cut
    # "Before any test is looked at," off its own sentence in one draw and lost
    # the ordering property in two others — and the counterexample must be a
    # change that could actually be built, which is what v6's persists
    # counterexamples were not. The verdict call also moves to the larger model,
    # which on the v5 prompt got both of the mini's coverage errors right.
    "v7": {
        "prompt": PROMPTS / "phase2-system-v7-neutral-frame.txt",
        "model": _model_v6,
        "reason": _reason_v6,
    },
}

# Arms whose verdict call carries no obligation fields, so obligations for
# uncovered spans are authored by a second call.
_AUTHORING_ARMS = {"v6", "v7"}


# --------------------------------------------------------------------------
# scoring against the expected outcome
#
# The three claims the summary makes, each recognised by a phrase that appears
# in it once. A span carrying two markers has not been split, which is itself a
# difference from the expected outcome rather than a scoring failure — so it is
# reported as `mixed` instead of being forced into one claim.

_CLAIM_MARKERS = {
    "ordering": "before any test is looked at",
    "persists": "persists with the rest of the review",
    "identifier": "by its identifier",
}
EXPECTED = {"ordering": "uncovered", "persists": "covered", "identifier": "uncovered"}


def claim_of(span: str) -> str:
    text = _squash(span).lower()
    hits = [name for name, marker in _CLAIM_MARKERS.items() if marker in text]
    if not hits:
        return "other"
    return hits[0] if len(hits) == 1 else "mixed:" + "+".join(hits)


# --------------------------------------------------------------------------
# authoring obligations for uncovered spans (v6 only)


def _find_span(source: str, span: str) -> tuple[int, int]:
    """Where this span sits in the task file, tolerating the file's line wrapping.

    Returns the real offsets so the synthetic requirement carries an honest
    `TextSpan` rather than a fabricated one. Falls back to the whole summary's
    offsets only if the span cannot be located, which `_shared_reason` has
    already made impossible for a response that got this far.
    """
    pattern = r"\s+".join(re.escape(token) for token in span.split())
    match = re.search(pattern, source)
    return (match.start(), match.end()) if match else (0, len(source))


def _synthetic_registry(source: str, uncovered: list[dict]) -> list[RequirementRef]:
    """Each uncovered span as an ordinary requirement of its own.

    `section` is `constraint` because that is what the span now is to the
    decomposer — one short bullet-shaped statement. The whole point of authoring
    here rather than in the verdict call is to hit the shape that over-answers 0
    times in 68 non-task batches, and the section is what the prompt renders.
    The id keeps the span's provenance visible.
    """
    registry = []
    for item in uncovered:
        start, end = _find_span(source, item["span"])
        registry.append(
            RequirementRef(
                id=f"task-01-span-{item['span_index']}",
                section=RequirementSection.CONSTRAINT,
                ordinal=item["span_index"] + 1,
                span=TextSpan(text=item["span"], start=start, end=end),
            )
        )
    return registry


def author_obligations(client, source: str, uncovered: list[dict], summary=None) -> dict:
    """One ordinary decompose call over the uncovered spans, as if they were bullets.

    The real `_SYSTEM_PROMPT`, the real `_user_prompt` and the real
    `_Decomposition` with `requirement_id` constrained to the synthetic ids —
    the pipeline's own call, not a copy of it. `source_quote` is overwritten by
    code afterwards, so nothing the model writes there can miss the source.

    `summary` is added to the registry as CONTEXT ONLY, never in the answering
    set. Without it a span is handed over with nothing around it, and the
    decomposer has no antecedent for the span's pronouns: the v7 arm's identifier
    obligation came back as "each recorded criterion" in four draws of five and
    "each recorded item" in the fifth, where the summary means a recorded way of
    failing. Adding it as context is the measured-safe shape rather than a guess
    — `findings.md` §2 puts the over-answering rate at 0 of 68 for batches with
    no `task-*` requirement in the ANSWERING set, and all 68 of those were shown
    the task paragraph as context.
    """
    if not uncovered:
        return {"called": False, "obligations": []}
    registry = _synthetic_registry(source, uncovered)
    ids = [r.id for r in registry]
    if summary is not None:
        registry = [summary, *registry]
    by_id = {f"task-01-span-{item['span_index']}": item["span"] for item in uncovered}
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, _SYSTEM_PROMPT),
            Block(BlockKind.SUBJECT, _user_prompt(registry, set(ids))),
        ]
    )
    request = client.build_request(
        messages, constrain(_Decomposition, {"requirement_id": ids}), {"size": len(ids)}
    )
    record = client._live_call("", request)
    parsed = json.loads(record["response"])

    authored = []
    for entry in parsed["requirement_dispositions"]:
        requirement_id = entry.get("requirement_id", "")
        if entry.get("disposition") != "yielded":
            authored.append(
                {"requirement_id": requirement_id, "disposition": entry.get("disposition")}
            )
            continue
        for item in [entry.get("obligation")] + (entry.get("more_obligations") or []):
            if not item:
                continue
            item = dict(item)
            item["source_quote"] = by_id.get(requirement_id, "")
            authored.append({"requirement_id": requirement_id, "obligation": item})
    return {
        "called": True,
        "request_key": request_key(request),
        "span_ids": ids,
        "response": record["response"],
        "obligations": authored,
    }


# --------------------------------------------------------------------------


def check_schema(arm: str) -> None:
    """Print the emitted schema, without calling anything."""
    from acceptance.llm import inline_schema_refs

    schema = inline_schema_refs(ARMS[arm]["model"]().model_json_schema())
    print(f"arm {arm}")
    print("top-level property order:", list(schema["properties"]))
    item = schema["properties"]["span_dispositions"]["items"]
    if "anyOf" in item:
        for shape in item["anyOf"]:
            print(f"  {shape['title']} field order:", list(shape["properties"]))
    else:
        print(f"  {item['title']} field order:", list(item["properties"]))
    print(f"schema is {len(json.dumps(schema)):,} chars\n")
    print(json.dumps(schema, indent=2))


def preview(root: Path, arm: str, trial: str) -> None:
    summary = _summary(root)
    listed = derived_obligations(root / "trials" / trial)
    for index, message in enumerate(
        _messages(ARMS[arm]["prompt"], listed, summary.span.text), start=1
    ):
        print(f"--- message {index}  role={message['role']}  ({len(message['content'])} chars)\n")
        print(message["content"])
        print()


def run(
    root: Path,
    out_root: Path,
    arm: str,
    model: str,
    author_model: str,
    temperature: float,
    only: str | None,
    seed_offset: int,
) -> None:
    summary = _summary(root)
    source = (root / draw.TASK_COPY).read_text(encoding="utf-8")
    spec = ARMS[arm]
    schema = spec["model"]()
    out_root.mkdir(parents=True, exist_ok=True)

    trials = sorted((root / "trials").glob("trial-*"))
    if only:
        trials = [t for t in trials if t.name == only] or trials[:0]

    for trial_dir in trials:
        saved = json.loads((trial_dir / "phase2-task-01.json").read_text(encoding="utf-8"))
        # The trial's own seed by default, so a draw is paired with the baseline
        # draw over the same phase-1 obligations. `--seed-offset` takes a further
        # round over the same five inputs at fresh seeds, which is how the sample
        # grows without re-running phase 1 and changing what is being compared.
        seed = saved["seed"] + seed_offset
        listed = derived_obligations(trial_dir)
        listed_ids = {item["id"] for item in listed}
        client = RunConfig(
            model=model, mode=Mode.RECORD, temperature=temperature, seed=seed
        ).build_client()
        request = client.build_request(_messages(spec["prompt"], listed, summary.span.text), schema)

        attempts = []
        parsed = None
        for attempt in range(2):
            record = client._live_call("", request)
            parsed = json.loads(record["response"])
            reason = spec["reason"](parsed, summary.span.text, listed_ids)
            attempts.append(
                {
                    "attempt": attempt + 1,
                    "rejected": reason is not None,
                    "reason": reason,
                    "response": record["response"],
                    "usage": record.get("usage"),
                    "stop_reason": record.get("stop_reason"),
                }
            )
            print(
                f"  {trial_dir.name} seed={seed} attempt {attempt + 1}: "
                + (f"REJECTED — {reason}" if reason else "ok")
            )
            if reason is None:
                break

        authored: dict = {"called": False, "obligations": []}
        if arm in _AUTHORING_ARMS and parsed is not None and not attempts[-1]["rejected"]:
            uncovered = [
                {"span_index": e["span_index"], "span": parsed["spans"][e["span_index"]]}
                for e in parsed["span_dispositions"]
                if e["disposition"] == "uncovered"
            ]
            # Its own client: the verdict call and the authoring call are
            # separately priced experiments, and v7 runs them on different
            # models on purpose.
            author_client = RunConfig(
                model=author_model, mode=Mode.RECORD, temperature=temperature, seed=seed
            ).build_client()
            authored = author_obligations(author_client, source, uncovered, summary)
            if authored["called"]:
                print(
                    f"    authored {len(authored['obligations'])} obligation(s) "
                    f"for {len(uncovered)} uncovered span(s)"
                )

        name = trial_dir.name if not seed_offset else f"{trial_dir.name}-seed{seed}"
        (out_root / f"{name}.json").write_text(
            json.dumps(
                {
                    "arm": arm,
                    "request_key": request_key(request),
                    "model": request["model"],
                    "author_model": author_model,
                    "seed": seed,
                    "temperature": request["temperature"],
                    "listed_obligations": len(listed),
                    "attempts": attempts,
                    "authored": authored,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print()
    summarize(root, out_root)


def _verdict_cost(attempts: list[dict]) -> float | None:
    costs = [(a.get("usage") or {}).get("cost_usd") for a in attempts]
    priced = [c for c in costs if c is not None]
    return sum(priced) if priced else None


def summarize(root: Path, out_root: Path) -> None:
    summary = _summary(root)
    haystack_strict = summary.span.text
    rows = []
    for path in sorted(out_root.glob("trial-*.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        final = saved["attempts"][-1]
        parsed = json.loads(final["response"])
        spans = parsed["spans"]
        entries = sorted(parsed["span_dispositions"], key=lambda e: e["span_index"])
        covered = sum(1 for e in entries if e["disposition"] == "covered")
        rows.append(
            {
                "draw": path.stem,
                "arm": saved.get("arm", "v4"),
                "model": saved.get("model", ""),
                "seed": saved["seed"],
                "listed": saved["listed_obligations"],
                "spans": len(spans),
                "covered": covered,
                "uncovered": len(entries) - covered,
                "exact_substring": all(s in haystack_strict for s in spans),
                # What the VERDICT call cost, summed over its attempts. The
                # harness prices each call in `usage["cost_usd"]`; a provider
                # LiteLLM cannot price leaves it absent, and the column then
                # reads `n/a` rather than 0.00, which would be a false figure.
                "cost_usd": _verdict_cost(saved["attempts"]),
                "rejected_first": saved["attempts"][0]["rejected"],
                "retried": len(saved["attempts"]) > 1,
                "final_rejected": final["rejected"],
                "span_list": spans,
                "dispositions": entries,
                "authored": saved.get("authored", {"called": False, "obligations": []}),
            }
        )

    if not rows:
        print("no draws saved")
        return

    header = (
        f"{'draw':<12}{'seed':>5}{'listed':>8}{'spans':>7}{'covered':>9}"
        f"{'uncovered':>11}{'exact':>7}{'rejected':>10}{'retried':>9}{'verdict $':>11}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        cost = f"{row['cost_usd']:.4f}" if row["cost_usd"] is not None else "n/a"
        print(
            f"{row['draw']:<12}{row['seed']:>5}{row['listed']:>8}{row['spans']:>7}"
            f"{row['covered']:>9}{row['uncovered']:>11}"
            f"{row['exact_substring']!s:>7}{row['rejected_first']!s:>10}"
            f"{row['retried']!s:>9}{cost:>11}"
        )
    total = [row["cost_usd"] for row in rows if row["cost_usd"] is not None]
    if total:
        print(
            f"{'':<12}{'':>5}{'':>8}{'':>7}{'':>9}{'':>11}{'':>7}{'':>10}{'total':>9}"
            f"{sum(total):>11.4f}"
        )

    print("\n=== every span of every draw, with its argument and its verdict\n")
    for row in rows:
        print(f"--- {row['draw']}  ({row['spans']} spans, {row['model']})")
        for entry in row["dispositions"]:
            index = entry["span_index"]
            span = row["span_list"][index]
            print(f"  [{index}] {entry['disposition']}  (claim: {claim_of(span)})")
            print(f'      span: "{_squash(span)}"')
            if "nearest" in entry:
                print(f"      nearest: {', '.join(entry['nearest']) or '(none)'}")
                print(f"      counterexample: {entry['counterexample']}")
            elif entry["disposition"] == "covered":
                print(f"      covered_by: {', '.join(entry['covered_by'])}")
                print(f"      covered_because: {entry.get('covered_because', '(field absent)')}")
            else:
                print(f"      obligation: {entry['obligation']['description']}")
                print(f"      not_covered_because: {entry['not_covered_because']}")
        print()

    print("=== against the expected outcome\n")
    print("    expected: 3 spans — ordering uncovered, persists covered, identifier uncovered\n")
    for row in rows:
        seen: dict[str, list[str]] = {}
        for entry in row["dispositions"]:
            seen.setdefault(claim_of(row["span_list"][entry["span_index"]]), []).append(
                entry["disposition"]
            )
        differences = []
        if row["spans"] != 3:
            differences.append(f"{row['spans']} spans, not 3")
        for claim, want in EXPECTED.items():
            got = seen.get(claim)
            if got is None:
                differences.append(f"no span states the {claim} claim on its own")
            elif got != [want]:
                differences.append(f"{claim} came back {'+'.join(got)}, expected {want}")
        for claim in seen:
            if claim.startswith("mixed:"):
                differences.append(f"one span carries two claims ({claim[6:]})")
            elif claim == "other":
                differences.append("a span states none of the three claims")
        print(f"  {row['draw']}: " + ("matches" if not differences else "; ".join(differences)))

    if any(row["authored"]["called"] for row in rows):
        print("\n=== obligations authored for the uncovered spans\n")
        for row in rows:
            if not row["authored"]["called"]:
                continue
            print(f"--- {row['draw']}")
            for item in row["authored"]["obligations"]:
                if "obligation" not in item:
                    print(f"  {item['requirement_id']}: {item['disposition']}")
                    continue
                obligation = item["obligation"]
                print(f"  {item['requirement_id']} -> [{obligation['id']}] ({obligation['type']})")
                print(f"      {obligation['description']}")
                print(f'      source_quote: "{_squash(obligation["source_quote"])}"')
            print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spanpass")
    parser.add_argument("--dir", type=Path, default=HERE / "work-2p")
    parser.add_argument("--out", type=Path, default=HERE / "work-sp3")
    parser.add_argument("--arm", choices=sorted(ARMS), default="v6")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check-schema", help="print the emitted JSON schema; makes no calls")

    pre = sub.add_parser("preview", help="print the request; makes no calls")
    pre.add_argument("--trial", default="trial-001")

    live = sub.add_parser("run", help="one draw per saved trial, at that trial's seed")
    live.add_argument("--model", default=RunConfig().model, help="the verdict call")
    live.add_argument(
        "--author-model",
        default=RunConfig().model,
        help="the per-bullet decomposer that authors obligations for uncovered spans",
    )
    live.add_argument("--temperature", type=float, default=0.0)
    live.add_argument("--trial", default=None, help="only this trial, e.g. trial-001")
    live.add_argument(
        "--seed-offset",
        type=int,
        default=0,
        help="another round over the same five inputs at fresh seeds",
    )

    sub.add_parser("summarize", help="score the saved draws; makes no calls")

    args = parser.parse_args(argv)
    if args.command == "check-schema":
        check_schema(args.arm)
    elif args.command == "preview":
        preview(args.dir, args.arm, args.trial)
    elif args.command == "run":
        run(
            args.dir,
            args.out,
            args.arm,
            args.model,
            args.author_model,
            args.temperature,
            args.trial,
            args.seed_offset,
        )
    else:
        summarize(args.dir, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
