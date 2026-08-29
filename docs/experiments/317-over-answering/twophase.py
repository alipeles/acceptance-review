"""Two-phase decomposition: batch the bullets, then ask the summary what is left.

The single-batch experiment (`draw.py`) measures the current shape. This one
measures a different shape, and it exists because every measurement now available
says the defect is specific to the `# Task` paragraph:

- 8 of 35 batches containing a `task-*` requirement over-answer; 0 of 68 without
  one (`findings.md` §2).
- Across 110 draws in `draw.py`'s four arms, every duplicated disposition and
  every foreign obligation was filed under `task-01`. The two exclusions in the
  same batch produced exactly one obligation each, 219 times out of 220.
- All 24 `explicit=false` obligations in the corpus are `task-*`.
- `task-01`'s obligation count is the only quantity any prompt change moved:
  6.58 per draw at baseline, 4.08, 2.80, 3.60 across the variants. The
  exclusions sat at 1.00 throughout.

So instead of asking one call to decompose a summary alongside the bullets that
elaborate it, this asks two questions:

**Phase 1** — every requirement EXCEPT the `(task)` ones, batched exactly as
today. No summary in any batch, so the trigger is absent by construction rather
than by instruction.

**Phase 2** — one call per `(task)` requirement, shown the obligations phase 1
derived and asked a residual question: *does the summary state anything checkable
that these do not already cover?* An empty answer is the expected one. Every
obligation it returns must cite the exact summary text that states it.

**Why the residual framing rather than dropping the summary.** `findings.md` §10
measured 173 of 738 obligations (23%) coming from `task-*` requirements, most
with low lexical overlap against any bullet-derived obligation. Silencing the
summary risks losing requirements, which is the failure this project treats as
worst. Asking what is left keeps them while removing the licence to restate.

**What to watch, per `findings.md` §10.** Residual judgements are unstable, and
the failure mode is the opposite of the current one: phase 2 answering "nothing
left" and swallowing a real requirement. The score below reports phase-2 output
per trial so a rate of zero is visible rather than assumed to be correct.

**No `_locate_quotation` shortcut for phase 2.** Its obligations are scored on
whether `source_quote` lands inside the `(task)` requirement itself — the
citation the prompt demands — not on batch membership, which is meaningless for
a call about one requirement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import draw
from pydantic import create_model

from acceptance.config import DEFAULT_DECOMPOSE_BATCH_SIZE, RunConfig
from acceptance.llm import Mode, StrictResponseModel, request_key
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.requirement.obligations import _DecomposedObligation, _locate_quotation
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import RequirementSection

HERE = Path(__file__).resolve().parent

PHASE2_SYSTEM = """\
You are checking one summary paragraph against work already done.

A task file states a change as an opening summary and then elaborates it as
bullets. Every bullet has already been decomposed into obligations, and you are
given all of them. You are given the summary. Nothing else is yours to answer
for.

Work through the summary one claim at a time. For each thing it states, decide
whether some listed obligation already requires that same thing. Return an
obligation for every claim none of them requires, and none for a claim one of
them does.

Two mistakes, and they are equally bad. Returning a claim the list already
covers duplicates work that is done. Omitting a claim the list does not cover
loses a requirement from the review altogether — and a summary routinely states
something no bullet repeats, because the bullets elaborate details while the
summary states the change itself. Judge each claim on its own merits. Do not
decide in advance how many there will be.

Each obligation you return carries:

- `source_quote`: the exact substring of the summary that states it. An exact
  substring, not a paraphrase — if you cannot quote it, the summary does not
  state it and there is no obligation.
- `not_covered_because`: which listed obligations come closest, and what this
  one requires that they do not.
- `id` (kebab-case), `description`, `type`, `importance` (critical or normal),
  `observable_behavior`, `required_evidence`, `required_evidence_reason`.

`type` is one of: functional, boundary, error_handling, invariant, regression,
compatibility, explanation_observability, docs_config, human_review,
test_demand. State each obligation as the positive property the delivered code
must hold, never as a prohibition.

`required_evidence` is one of code_and_tests (the default), code_only,
tests_only, neither. Anything other than code_and_tests needs a one-sentence
`required_evidence_reason`."""


def _phase1_user(registry: list, answer_for: list[str]) -> str:
    """The v2 subject layout, generated for an arbitrary answering set.

    Reproduces the hand-written `REQUEST-AS-SENT-v2.txt` structure rather than
    `obligations._user_prompt`'s: context-only requirements first, the ones being
    answered for collected at the end under their own heading, and the count and
    ids stated at both ends. That layout is the one under test, so phase 1 has to
    emit it for every batch rather than only for the batch it was written for.
    """
    wanted = set(answer_for)
    count = len(answer_for)
    listed = ", ".join(answer_for)

    lines = [
        f"You answer for {count} requirements: {listed}.",
        "",
        "The rest of the task file, for context only:",
        "",
    ]
    for requirement in registry:
        if requirement.id in wanted:
            continue
        lines.append(
            f"[{requirement.id}] ({requirement.section.value}) [context only] {requirement.text}"
        )
    lines.extend(["", "Your requirements:", ""])
    for requirement in registry:
        if requirement.id in wanted:
            lines.append(f"[{requirement.id}] ({requirement.section.value}) {requirement.text}")
    lines.extend(
        [
            "",
            f"Return exactly {count} dispositions, one for each of {listed}, and nothing",
            "for any other requirement. Every `source_quote` is a substring of one of",
            f"these {count}.",
        ]
    )
    return "\n".join(lines)


def _phase2_user(task_text: str, task_id: str, obligations: list[dict]) -> str:
    lines = ["Obligations already derived from this task file's bullets:", ""]
    for item in obligations:
        lines.append(f"  [{item['from']}] {item['description']}")
    lines.extend(
        [
            "",
            "The summary to check:",
            "",
            f"[{task_id}] (task) {task_text}",
            "",
            "Work through the summary claim by claim. Return an obligation for each",
            "claim the list above does not cover, quoting the summary exactly.",
        ]
    )
    return "\n".join(lines)


def _residual_model() -> type:
    """Phase 2's response shape: the obligation fields plus its justification.

    Built from `_DecomposedObligation`'s own fields, minus `explicit` (which the
    corpus shows fires only on `task-*` and which this design removes), plus
    `not_covered_because`. Derived rather than hand-written so a field added to
    the real model reaches this experiment instead of silently diverging.
    """
    fields = {
        name: (field.annotation, ...)
        for name, field in _DecomposedObligation.model_fields.items()
        if name != "explicit"
    }
    fields["not_covered_because"] = (str, ...)
    obligation = create_model("_ResidualObligation", __base__=StrictResponseModel, **fields)
    return create_model(
        "_Residual", __base__=StrictResponseModel, obligations=(list[obligation], ...)
    )


def _split(registry: list) -> tuple[list, list]:
    """Bullets and summaries, kept apart. The whole point of the design."""
    bullets = [r for r in registry if r.section is not RequirementSection.TASK]
    summaries = [r for r in registry if r.section is RequirementSection.TASK]
    return bullets, summaries


def materialize(task: Path, root: Path, batch_size: int, model: str) -> None:
    text = task.read_text(encoding="utf-8")
    registry = build_registry(parse_task_file(text))
    bullets, summaries = _split(registry)
    batches = partition(bullets, batch_size, key=lambda r: r.id)

    root.mkdir(parents=True, exist_ok=True)
    (root / draw.TASK_COPY).write_text(text, encoding="utf-8")
    client = RunConfig(model=model, mode=Mode.REPLAY).build_client()
    preamble = (HERE / "prompts-v2-baseline" / draw.PREAMBLE_FILE).read_text(encoding="utf-8")
    phase1_system = (HERE / "prompts-v2-baseline" / draw.SYSTEM_FILE).read_text(encoding="utf-8")

    print(f"task: {task}")
    print(f"  {len(registry)} requirements = {len(bullets)} bullets + {len(summaries)} summary")
    print(f"  phase 1: {len(batches)} batch(es) over bullets only — no summary in any of them")

    phase1 = root / "phase1"
    phase1.mkdir(exist_ok=True)
    for batch in batches:
        ids = [r.id for r in batch.items]
        batch_dir = phase1 / f"batch-{batch.index}"
        batch_dir.mkdir(exist_ok=True)
        (batch_dir / draw.PREAMBLE_FILE).write_text(preamble, encoding="utf-8")
        (batch_dir / draw.SYSTEM_FILE).write_text(phase1_system, encoding="utf-8")
        # The registry shown is the WHOLE one, summaries included, exactly as
        # today: the batch scopes what a call answers for, not what it may read
        # (#178). Only the answering set changed.
        (batch_dir / draw.USER_FILE).write_text(_phase1_user(registry, ids), encoding="utf-8")
        (batch_dir / draw.META_FILE).write_text(
            json.dumps(
                {
                    "phase": 1,
                    "batch_index": batch.index,
                    "batch_size": batch.size,
                    "batch_ids": ids,
                    "registry_ids": [r.id for r in registry],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"      batch-{batch.index}: {', '.join(ids)}")

    phase2 = root / "phase2"
    phase2.mkdir(exist_ok=True)
    (phase2 / draw.PREAMBLE_FILE).write_text(preamble, encoding="utf-8")
    (phase2 / draw.SYSTEM_FILE).write_text(PHASE2_SYSTEM, encoding="utf-8")
    (phase2 / draw.META_FILE).write_text(
        json.dumps(
            {
                "phase": 2,
                "summary_ids": [r.id for r in summaries],
                "model_at_materialize": model,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"  phase 2: {len(summaries)} residual call(s) — {', '.join(r.id for r in summaries)}")
    print("\n  phase 2's user message is built at run time from phase 1's output.")
    print("  render it against a saved phase-1 result with:  preview")

    _ = client, request_key  # kept for parity with draw.materialize's key report


def preview(root: Path, obligations_json: Path | None) -> None:
    """Render phase 2's exact request without issuing a call.

    `--from` takes a JSON list of `{from, description}` — phase 1's output, or
    obligations lifted out of recorded transcripts for the same task file, which
    is what makes this reviewable before anything is spent.
    """
    source = (root / draw.TASK_COPY).read_text(encoding="utf-8")
    registry = build_registry(parse_task_file(source))
    _bullets, summaries = _split(registry)
    obligations = (
        json.loads(obligations_json.read_text(encoding="utf-8")) if obligations_json else []
    )

    for summary in summaries:
        user = _phase2_user(summary.span.text, summary.id, obligations)
        messages = assemble(
            [
                Block(BlockKind.INSTRUCTIONS, (root / "phase2" / draw.SYSTEM_FILE).read_text()),
                Block(BlockKind.SUBJECT, user),
            ]
        )
        messages[0] = {
            **messages[0],
            "content": (root / "phase2" / draw.PREAMBLE_FILE).read_text(encoding="utf-8"),
        }
        print("=" * 78)
        print(f"PHASE 2 — residual call for {summary.id}")
        print(f"  {len(obligations)} obligation(s) from phase 1 shown as covered")
        print("=" * 78)
        for index, message in enumerate(messages, start=1):
            print(
                f"\n--- message {index}  role={message['role']}  ({len(message['content'])} chars)"
            )
            print()
            print(message["content"])
        schema = _residual_model().model_json_schema()
        print("\n--- response_format  json_schema name=_Residual  strict=true")
        print(f"--- {len(json.dumps(schema)):,} chars\n")
        print(json.dumps(schema, indent=2)[:1200] + "\n  … (truncated)")


def _phase2_messages(root: Path, summary, obligations: list[dict]) -> list[dict]:
    messages = assemble(
        [
            Block(
                BlockKind.INSTRUCTIONS,
                (root / "phase2" / draw.SYSTEM_FILE).read_text(encoding="utf-8"),
            ),
            Block(BlockKind.SUBJECT, _phase2_user(summary.span.text, summary.id, obligations)),
        ]
    )
    messages[0] = {
        **messages[0],
        "content": (root / "phase2" / draw.PREAMBLE_FILE).read_text(encoding="utf-8"),
    }
    return messages


def _save(record: dict, request: dict) -> dict:
    """A draw, minus the request — evidence rather than a transcript."""
    return {
        "request_key": request_key(request),
        "seed": request.get("seed"),
        "model": request["model"],
        "response": record["response"],
        "usage": record.get("usage"),
        "stop_reason": record.get("stop_reason"),
    }


def run(root: Path, trials: int, model: str, temperature: float, base_seed: int) -> None:
    source = (root / draw.TASK_COPY).read_text(encoding="utf-8")
    registry = build_registry(parse_task_file(source))
    _bullets, summaries = _split(registry)
    batch_dirs = sorted(
        p for p in (root / "phase1").glob("batch-*") if (p / draw.META_FILE).is_file()
    )
    residual_model = _residual_model()

    trials_root = root / "trials"
    trials_root.mkdir(exist_ok=True)
    done = len(list(trials_root.glob("trial-*")))

    for trial in range(trials):
        index = done + trial + 1
        seed = base_seed + done + trial
        client = RunConfig(
            model=model, mode=Mode.RECORD, temperature=temperature, seed=seed
        ).build_client()
        out = trials_root / f"trial-{index:03d}"
        (out / "phase1").mkdir(parents=True, exist_ok=True)
        print(f"trial-{index:03d}  seed={seed}")

        # ---- phase 1: the bullets, batched
        derived: list[dict] = []
        for batch_dir in batch_dirs:
            meta = json.loads((batch_dir / draw.META_FILE).read_text(encoding="utf-8"))
            ids = meta["batch_ids"]
            request = client.build_request(
                draw._messages(batch_dir),
                draw.response_model_for(ids, enum_ids=False, explicit=False),
                {"size": meta["batch_size"]},
            )
            record = client._live_call("", request)
            (out / "phase1" / f"{batch_dir.name}.json").write_text(
                json.dumps(_save(record, request), indent=2) + "\n", encoding="utf-8"
            )
            parsed = json.loads(record["response"])
            for entry in parsed["requirement_dispositions"]:
                if entry.get("disposition") != "yielded":
                    continue
                obs = [
                    o
                    for o in [entry.get("obligation")] + (entry.get("more_obligations") or [])
                    if o
                ]
                for ob in obs:
                    derived.append(
                        {"from": entry.get("requirement_id", ""), "description": ob["description"]}
                    )
            print(f"    phase1 {batch_dir.name}: {len(parsed['requirement_dispositions'])} entries")

        (out / "obligations.json").write_text(
            json.dumps(derived, indent=2) + "\n", encoding="utf-8"
        )

        # ---- phase 2: one residual call per summary
        for summary in summaries:
            request = client.build_request(_phase2_messages(root, summary, derived), residual_model)
            record = client._live_call("", request)
            (out / f"phase2-{summary.id}.json").write_text(
                json.dumps(_save(record, request), indent=2) + "\n", encoding="utf-8"
            )
            returned = json.loads(record["response"])["obligations"]
            print(f"    phase2 {summary.id}: {len(derived)} shown -> {len(returned)} residual")
    print()
    summarize(root)


def summarize(root: Path) -> None:
    source = (root / draw.TASK_COPY).read_text(encoding="utf-8")
    registry = build_registry(parse_task_file(source))
    _bullets, summaries = _split(registry)
    by_id = {r.id: r for r in registry}

    rows = []
    for out in sorted((root / "trials").glob("trial-*")):
        row: dict = {"trial": out.name, "phase1_foreign": 0, "phase1_dup": 0, "residual": []}
        for path in sorted((out / "phase1").glob("batch-*.json")):
            meta = json.loads(
                (root / "phase1" / path.stem / draw.META_FILE).read_text(encoding="utf-8")
            )
            expected = set(meta["batch_ids"])
            entries = json.loads(json.loads(path.read_text())["response"])[
                "requirement_dispositions"
            ]
            seen: dict[str, int] = {}
            for entry in entries:
                rid = entry.get("requirement_id", "")
                seen[rid] = seen.get(rid, 0) + 1
                for ob in [entry.get("obligation")] + (entry.get("more_obligations") or []):
                    if not ob:
                        continue
                    _span, owner = _locate_quotation(
                        registry, source, ob.get("source_quote", ""), rid
                    )
                    if owner is not None and owner.id not in expected:
                        row["phase1_foreign"] += 1
            row["phase1_dup"] += sum(1 for n in seen.values() if n > 1)
        for summary in summaries:
            path = out / f"phase2-{summary.id}.json"
            if not path.is_file():
                continue
            for ob in json.loads(json.loads(path.read_text())["response"])["obligations"]:
                quote = ob.get("source_quote", "")
                _span, owner = _locate_quotation(registry, source, quote, summary.id)
                row["residual"].append(
                    {
                        "description": ob["description"],
                        "cites_summary": owner is not None and owner.id == summary.id,
                        "landed_in": owner.id if owner else None,
                    }
                )
        rows.append(row)

    if not rows:
        print("no trials saved")
        return

    print(f"=== two-phase, {len(rows)} trial(s)")
    print("    phase 1 (bullets only, no summary in any batch)")
    print(f"       foreign obligations: {sum(r['phase1_foreign'] for r in rows)}")
    print(f"       duplicated dispositions: {sum(r['phase1_dup'] for r in rows)}")
    counts = [len(r["residual"]) for r in rows]
    miscited = sum(1 for r in rows for x in r["residual"] if not x["cites_summary"])
    print(f"    phase 2 (residual call on {', '.join(s.id for s in summaries)})")
    print(f"       residual obligations per trial: {counts}")
    print(f"       mean {sum(counts) / len(counts):.2f}   empty in {counts.count(0)}/{len(counts)}")
    print(f"       quotes not landing in the summary: {miscited}/{sum(counts)}")
    print("\n    what phase 2 returned:")
    tally: dict[str, int] = {}
    for row in rows:
        for item in row["residual"]:
            tally[item["description"]] = tally.get(item["description"], 0) + 1
    for description, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"       {n:>2}x  {description}")
    _ = by_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="twophase")
    parser.add_argument("--dir", type=Path, default=HERE / "work-2p")
    sub = parser.add_subparsers(dest="command", required=True)

    live = sub.add_parser("run", help="run N complete two-phase trials")
    live.add_argument("-n", "--trials", type=int, default=5)
    live.add_argument("--model", default=RunConfig().model)
    live.add_argument("--temperature", type=float, default=0.0)
    live.add_argument("--seed", type=int, default=0)

    sub.add_parser("summarize", help="score saved trials; makes no calls")

    mat = sub.add_parser("materialize")
    mat.add_argument("--task", type=Path, required=True)
    mat.add_argument("--batch-size", type=int, default=DEFAULT_DECOMPOSE_BATCH_SIZE)
    mat.add_argument("--model", default=RunConfig().model)

    pre = sub.add_parser("preview", help="render phase 2's request; makes no calls")
    pre.add_argument("--from", dest="source", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.command == "materialize":
        materialize(args.task, args.dir, args.batch_size, args.model)
    elif args.command == "run":
        run(args.dir, args.trials, args.model, args.temperature, args.seed)
    elif args.command == "summarize":
        summarize(args.dir)
    else:
        preview(args.dir, args.source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
