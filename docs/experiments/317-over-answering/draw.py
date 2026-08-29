"""Draw the decompose request repeatedly against an EDITABLE prompt, and score it.

Companion to `analyse.py` in this directory, and it answers the question that one
cannot. `analyse.py` mines the 1,748 recorded transcripts: it establishes what
the model already did, and `findings.md` is its write-up. It cannot tell you what
the model would do if the prompt said something different, because there is no
recording of a prompt nobody has sent.

This sends them. `materialize` writes the fully materialized request out as two
editable files; you rewrite them; `run` issues N live calls against whatever they
now say; `summarize` scores the answers with the same own/batch/foreign/unplaced
vocabulary `analyse.py` uses, so the numbers sit beside its table.

**Read `findings.md` before using this.** It already settles what the defect is
(the model answers for requirements it was shown as context, whenever the batch
contains the `# Task` paragraph — 8 of 35 such calls, against 0 of 68 without,
Fisher p = 0.0001), that the disposition count is a symptom rather than the
defect, and that a prompt change costs exactly what a schema change costs because
`request_key` hashes the messages. This tool is for §10 and §11 of that document
— the prompt fixes that must be measured before they are believed — not for
re-deriving §1 to §8.

## The cache is bypassed, deliberately

`ModelClient.complete` is content-addressed, so N identical requests would hit
the cache and return one answer N times. This calls `ModelClient._live_call`,
which neither reads nor writes `.acceptance/cache/transcripts/`. Every draw is a
live call, nothing here can orphan or pollute the recorded corpus, and
`analyse.py` will never see these draws in the transcript directory.

## Saved draws are not transcripts

A transcript embeds the full request as sent, which is why they are not
committed. A saved draw here keeps only the response, the usage, the stop reason,
the honoured controls, and the request KEY — never the request. So a run that is
worth keeping can be committed as evidence, exactly as
`265-cache-key-scope/result-2026-08-20.json` is.

## Fidelity

With the prompts unedited, the requests this builds are byte-identical to the
ones `decompose` sends. `materialize` prints each batch's request key and whether
a transcript for it is already on disk; on `dogfood-logs/313-gate1-run1/` all four
keys match the four transcripts that run recorded, `7d6f41d2…` being the batch
`findings.md` §1 dissects. Editing a prompt moves the key, which is the point.

## Private imports

`_SYSTEM_PROMPT`, `_user_prompt`, `_Decomposition` and `_locate_quotation` come
from `requirement/obligations.py` on purpose: the point is to send the real
prompt and resolve quotes with the real resolver, not copies that drift. A rename
breaks this loudly, which is correct.

`_locate_quotation` is used where `analyse.py` re-implements containment against
the registry text in the request. Same intent; this one is the pipeline's own
resolver, which searches the attributed requirement first and is
whitespace-insensitive, so it answers "where would the pipeline file this?"
rather than "where does this string appear?".
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import create_model

from acceptance.config import DEFAULT_DECOMPOSE_BATCH_SIZE, RunConfig
from acceptance.llm import Mode, StrictResponseModel, mark_reusable_opening, request_key
from acceptance.partition import partition
from acceptance.request_blocks import SHARED_PREAMBLE, Block, BlockKind, assemble
from acceptance.requirement.obligations import (
    _SYSTEM_PROMPT,
    _DecomposedObligation,
    _Decomposition,
    _locate_quotation,
    _NoObligation,
    _OpenQuestion,
    _RaisedOpenQuestion,
    _user_prompt,
    _Yielded,
)
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import constrain

HERE = Path(__file__).resolve().parent
PREAMBLE_FILE = "preamble.txt"
SYSTEM_FILE = "system.txt"
USER_FILE = "user.txt"
META_FILE = "meta.json"
TASK_COPY = "task.md"
RUNS_DIR = "runs"


def _drop_explicit(model: type) -> type:
    """`_DecomposedObligation` without its `explicit` field.

    Rebuilt rather than subclassed: pydantic can add a field to a model but not
    remove one, so the variant is constructed from the surviving field set. Every
    field stays required with no default, which is what `StrictResponseModel`'s
    docstring says strict mode demands.

    The name is preserved because the schema name is hashed into the request key
    and is what the provider is shown; keeping it makes the variant's request
    differ from the baseline's only in the ways under test.
    """
    fields = {
        name: (field.annotation, ...)
        for name, field in model.model_fields.items()
        if name != "explicit"
    }
    return create_model(model.__name__, __base__=StrictResponseModel, **fields)


def response_model_for(ids: list[str], *, enum_ids: bool, explicit: bool) -> type:
    """The response model this draw asks for.

    Two axes, because two of the changes under test are schema changes that no
    edit to `system.txt` or `user.txt` can express:

    `enum_ids=False` leaves `requirement_id` as free-text `str` — no `constrain`
    call, so nothing structurally stops the model naming a requirement outside
    the batch. That is the point of testing it: today the enum deflects the
    violation into `source_quote` rather than preventing it, so a free-text field
    should make the model's actual intent visible instead of hiding it behind a
    label it was forced to write.

    `explicit=False` drops `_DecomposedObligation.explicit`. Measured over the
    200 recorded `_Decomposition` calls, that field is `false` on 24 of 725
    obligations and **every one of them is filed under a `task-*` requirement**
    (14.4% there, 0 of 558 everywhere else). Obligations derived from a resolved
    open question set it in `coverage/open_questions.py`, which is untouched by
    this and is where the distinction carries meaning.
    """
    obligation = _DecomposedObligation if explicit else _drop_explicit(_DecomposedObligation)
    if explicit:
        model = _Decomposition
    else:
        yielded = create_model(
            _Yielded.__name__,
            __base__=StrictResponseModel,
            requirement_id=(str, ...),
            disposition=(Literal["yielded"], ...),
            obligation=(obligation, ...),
            more_obligations=(list[obligation], ...),
        )
        model = create_model(
            _Decomposition.__name__,
            __base__=StrictResponseModel,
            open_questions=(list[_OpenQuestion], ...),
            requirement_dispositions=(list[yielded | _NoObligation | _RaisedOpenQuestion], ...),
        )
    return constrain(model, {"requirement_id": ids}) if enum_ids else model


def _load_registry(root: Path) -> tuple[str, list]:
    """The task source and its registry, from the copy `materialize` saved.

    The saved copy rather than the original path: scoring resolves quotes against
    requirement spans, so it must see the file the prompts were built from.
    Editing the prompts is expected; editing the task file out from under a saved
    experiment would silently make the saved draws answers to another question.
    """
    source = (root / TASK_COPY).read_text(encoding="utf-8")
    return source, build_registry(parse_task_file(source))


def _messages(batch_dir: Path) -> list[dict]:
    """All three messages, every one of them editable.

    `assemble` writes `request_blocks.SHARED_PREAMBLE` into the `system` message
    itself, so without this the one message the model reads first would be the
    only part of the request a prompt experiment could not touch. That matters
    here: the preamble says the request carries *"material to judge and, after
    it, the instructions"*, while `assemble` in fact orders instructions before
    material — one of the three contradictions `findings.md` §6 names, and not
    testable while it is unreachable.

    `preamble.txt` is written by `materialize` and overrides it. A batch
    directory from before this existed has no such file and keeps the built-in,
    so older experiments are unaffected.
    """
    messages = assemble(
        [
            Block(BlockKind.INSTRUCTIONS, (batch_dir / SYSTEM_FILE).read_text(encoding="utf-8")),
            Block(BlockKind.SUBJECT, (batch_dir / USER_FILE).read_text(encoding="utf-8")),
        ]
    )
    override = batch_dir / PREAMBLE_FILE
    if override.is_file():
        messages[0] = {**messages[0], "content": override.read_text(encoding="utf-8")}
    return messages


def _batch_dirs(root: Path, only: str | None) -> list[Path]:
    found = sorted(p for p in root.glob("batch-*") if (p / META_FILE).is_file())
    if only is None:
        return found
    wanted = root / f"batch-{only}"
    if wanted not in found:
        raise SystemExit(f"no materialized batch-{only} under {root}")
    return [wanted]


# --------------------------------------------------------------------------


def materialize(task: Path, root: Path, batch_size: int, only: str | None, model: str) -> None:
    text = task.read_text(encoding="utf-8")
    registry = build_registry(parse_task_file(text))
    batches = partition(registry, batch_size, key=lambda requirement: requirement.id)

    root.mkdir(parents=True, exist_ok=True)
    (root / TASK_COPY).write_text(text, encoding="utf-8")
    client = RunConfig(model=model, mode=Mode.REPLAY).build_client()

    print(f"task: {task}   requirements: {len(registry)}   batches: {len(batches)}")
    for batch in batches:
        if only is not None and str(batch.index) != only:
            continue
        ids = [requirement.id for requirement in batch.items]
        batch_dir = root / f"batch-{batch.index}"
        batch_dir.mkdir(exist_ok=True)
        (batch_dir / PREAMBLE_FILE).write_text(SHARED_PREAMBLE, encoding="utf-8")
        (batch_dir / SYSTEM_FILE).write_text(_SYSTEM_PROMPT, encoding="utf-8")
        (batch_dir / USER_FILE).write_text(_user_prompt(registry, set(ids)), encoding="utf-8")

        key = request_key(
            client.build_request(
                _messages(batch_dir),
                constrain(_Decomposition, {"requirement_id": ids}),
                batch.request_partition(),
            )
        )
        (batch_dir / META_FILE).write_text(
            json.dumps(
                {
                    "task_file": str(task),
                    "batch_index": batch.index,
                    "batch_count": batch.count,
                    "batch_size": batch.size,
                    "batch_ids": ids,
                    "registry_ids": [r.id for r in registry],
                    "model_at_materialize": model,
                    "pipeline_request_key": key,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        seen = "already recorded" if client.store.read(key) is not None else "not in the cache"
        print(f"  batch-{batch.index}: {', '.join(ids)}")
        print(f"      key {key[:16]}…  ({seen})")
    print(f"\nedit {root}/batch-N/{{{SYSTEM_FILE},{USER_FILE}}}, then: run")


# --------------------------------------------------------------------------


def show(
    root: Path,
    only: str | None,
    model: str,
    as_json: bool,
    enum_ids: bool = True,
    explicit: bool = True,
) -> None:
    """Print the request exactly as the provider receives it.

    `system.txt` and `user.txt` are not the whole payload, and reading them alone
    misleads in three ways worth seeing for yourself:

    1. **A third piece of text.** `assemble` prepends `SHARED_PREAMBLE` from
       `request_blocks.py`, which lives in neither file and is the only message
       with role `system`.
    2. **`_SYSTEM_PROMPT` is sent as a `user` message**, despite its name — the
       one `system` message is the preamble.
    3. **The response schema is part of the request.** It carries the
       `requirement_id` enum, which is the only structural limit on what the
       model may answer for, and it is built from `meta.json`'s `batch_ids`
       rather than from anything in the two text files.

    `--json` prints the wire payload: the messages after
    `llm.mark_reusable_opening` has applied any provider cache breakpoint, plus
    `response_format` and the scalar controls. That is byte-for-byte what
    LiteLLM is handed.
    """
    for batch_dir in _batch_dirs(root, only):
        meta = json.loads((batch_dir / META_FILE).read_text(encoding="utf-8"))
        ids = meta["batch_ids"]
        client = RunConfig(model=model, mode=Mode.REPLAY).build_client()
        response_model = response_model_for(ids, enum_ids=enum_ids, explicit=explicit)
        request = client.build_request(
            _messages(batch_dir), response_model, {"size": meta["batch_size"]}
        )

        if as_json:
            print(
                json.dumps(
                    {
                        "model": request["model"],
                        "temperature": request["temperature"],
                        **({"seed": request["seed"]} if "seed" in request else {}),
                        "messages": mark_reusable_opening(request["messages"], request["model"]),
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": request["response_schema"]["name"],
                                "schema": request["response_schema"]["schema"],
                                "strict": True,
                            },
                        },
                    },
                    indent=2,
                )
            )
            continue

        print("=" * 78)
        print(f"{batch_dir.name} — asked for: {', '.join(ids)}")
        print(f"request key {request_key(request)}")
        print(
            f"model={request['model']}  temperature={request['temperature']}  "
            f"seed={request.get('seed')}"
        )
        print("=" * 78)
        for index, message in enumerate(request["messages"], start=1):
            body = message["content"]
            source = {
                1: f"{PREAMBLE_FILE}  — request_blocks.SHARED_PREAMBLE",
                2: f"{SYSTEM_FILE}    — obligations._SYSTEM_PROMPT",
                3: f"{USER_FILE}      — obligations._user_prompt",
            }.get(index, "")
            print(f"\n--- message {index}  role={message['role']}  ({len(body)} chars)")
            print(f"--- from: {source}\n")
            print(body)

        schema = request["response_schema"]
        print(f"\n--- response_format  json_schema name={schema['name']}  strict=true")
        # Stated from the schema rather than asserted: with `--no-enum` there is
        # no enum, and a header claiming one would be a false statement sitting
        # in the artifact this command exists to let someone check.
        limit = (
            "requirement_id is constrained to an enum of the batch's ids — the only "
            "structural limit on what may be answered for"
            if enum_ids
            else "requirement_id is FREE TEXT — nothing structurally limits what may be "
            "answered for"
        )
        print(f"--- {limit}\n")
        print(json.dumps(schema["schema"], indent=2))


def run(
    root: Path,
    only: str | None,
    draws: int,
    model: str,
    temperature: float,
    seed: int | None,
    vary_seed: bool,
    enum_ids: bool = True,
    explicit: bool = True,
) -> None:
    for batch_dir in _batch_dirs(root, only):
        meta = json.loads((batch_dir / META_FILE).read_text(encoding="utf-8"))
        ids = meta["batch_ids"]
        client = RunConfig(
            model=model, mode=Mode.RECORD, temperature=temperature, seed=seed
        ).build_client()
        base = client.build_request(
            _messages(batch_dir),
            response_model_for(ids, enum_ids=enum_ids, explicit=explicit),
            {"size": meta["batch_size"]},
        )

        runs_dir = batch_dir / RUNS_DIR
        runs_dir.mkdir(exist_ok=True)
        existing = len(list(runs_dir.glob("run-*.json")))
        print(
            f"{batch_dir.name}: {draws} draw(s), model={model} temperature={temperature} "
            f"seed={'vary' if vary_seed else seed} ({existing} already saved)"
        )
        print(
            f"    schema: requirement_id={'enum' if enum_ids else 'free text'}, "
            f"explicit field {'present' if explicit else 'REMOVED'}"
        )

        for draw in range(draws):
            request = dict(base)
            if vary_seed:
                request["seed"] = (seed or 0) + existing + draw
            index = existing + draw + 1
            try:
                # Neither reads nor writes the transcript cache. The key argument
                # is unused by `_live_call`.
                record = client._live_call("", request)
            except Exception as exc:  # noqa: BLE001 - a failed draw is a datum
                saved: dict[str, Any] = {"error": repr(exc)}
                print(f"  run-{index:03d}  FAILED: {exc}")
            else:
                # The request is deliberately dropped: keeping it would make this
                # a transcript, which may not be committed. The key identifies it.
                saved = {
                    "request_key": request_key(request),
                    # Which schema variant produced this draw. Recorded per draw,
                    # not per directory, so a `runs/` holding a mix stays
                    # readable rather than being quietly averaged.
                    "variant": {"enum_ids": enum_ids, "explicit": explicit},
                    "seed": request.get("seed"),
                    "temperature": request["temperature"],
                    "model": request["model"],
                    "response": record["response"],
                    "usage": record.get("usage"),
                    "stop_reason": record.get("stop_reason"),
                    "controls_applied": record.get("controls_applied"),
                }
                print(f"  run-{index:03d}  ok  ({record.get('stop_reason')})")
            (runs_dir / f"run-{index:03d}.json").write_text(
                json.dumps(saved, indent=2) + "\n", encoding="utf-8"
            )
    print()
    summarize(root, only)


# --------------------------------------------------------------------------


def _obligations_of(disposition: dict) -> list[dict]:
    if disposition.get("disposition") != "yielded":
        return []
    head = disposition.get("obligation")
    return ([head] if head else []) + list(disposition.get("more_obligations") or [])


def _score_draw(record: dict, source: str, registry: list, ids: list[str]) -> dict:
    """One draw's verdict. Every failure mode named, none collapsed.

    Obligations are classified with `analyse.py`'s vocabulary so the two tools'
    numbers are comparable: `own` (quote lands in the requirement it was filed
    under), `batch` (in another requirement this call was asked for), `foreign`
    (in one shown only as context — the defect), `unplaced` (in none).
    """
    if "error" in record:
        return {"status": "call_failed", "detail": record["error"]}
    try:
        response = record["response"]
        parsed = json.loads(response) if isinstance(response, str) else response
        dispositions = parsed["requirement_dispositions"]
    except Exception as exc:  # noqa: BLE001
        return {"status": "unparseable", "detail": repr(exc)}

    expected = set(ids)
    counts = Counter(d.get("requirement_id") for d in dispositions)
    tally = Counter()
    foreign_obligations: list[dict] = []

    for disposition in dispositions:
        attributed = disposition.get("requirement_id", "")
        for obligation in _obligations_of(disposition):
            _span, owner = _locate_quotation(
                registry, source, obligation.get("source_quote", ""), attributed
            )
            if owner is None:
                tally["unplaced"] += 1
            elif owner.id == attributed:
                tally["own"] += 1
            elif owner.id in expected:
                tally["batch"] += 1
            else:
                tally["foreign"] += 1
                foreign_obligations.append(
                    {
                        "obligation_id": obligation.get("id"),
                        "filed_under": attributed,
                        "quote_belongs_to": owner.id,
                    }
                )

    duplicated = {rid: n for rid, n in counts.items() if n > 1}
    missing = sorted(expected - set(counts))
    return {
        "status": "ok",
        "dispositions": len(dispositions),
        "expected": len(ids),
        "exact_count": not duplicated and not missing and not (set(counts) - expected),
        "duplicated": duplicated,
        "missing": missing,
        "obligations": sum(tally.values()),
        "own": tally["own"],
        "batch": tally["batch"],
        "foreign": tally["foreign"],
        "unplaced": tally["unplaced"],
        "foreign_obligations": foreign_obligations,
        "stop_reason": record.get("stop_reason"),
        "usage": record.get("usage"),
    }


def summarize(root: Path, only: str | None) -> None:
    source, registry = _load_registry(root)
    report: dict[str, Any] = {}

    for batch_dir in _batch_dirs(root, only):
        meta = json.loads((batch_dir / META_FILE).read_text(encoding="utf-8"))
        ids = meta["batch_ids"]
        files = sorted((batch_dir / RUNS_DIR).glob("run-*.json"))
        if not files:
            print(f"{batch_dir.name}: no runs saved")
            continue

        scored = [
            _score_draw(json.loads(p.read_text(encoding="utf-8")), source, registry, ids)
            for p in files
        ]
        usable = [s for s in scored if s["status"] == "ok"]

        print(f"=== {batch_dir.name} — asked for {len(ids)}: {', '.join(ids)}")
        print(f"    draws: {len(scored)}   usable: {len(usable)}")

        if usable:
            exact = sum(1 for s in usable if s["exact_count"])
            clean = sum(1 for s in usable if s["exact_count"] and not s["foreign"])
            counts = [s["dispositions"] for s in usable]
            leaks = [s["foreign"] for s in usable]
            print(f"    exact disposition count:  {exact}/{len(usable)}")
            print(f"    exact AND no foreign:     {clean}/{len(usable)}   <- the one that matters")
            print(
                f"    dispositions returned:    min {min(counts)}  "
                f"median {statistics.median(counts)}  max {max(counts)}   (expected {len(ids)})"
            )
            print(
                f"    foreign obligations:      {sum(leaks)} across "
                f"{sum(1 for n in leaks if n)}/{len(usable)} draw(s)"
            )
            print(
                "    obligations own/batch/foreign/unplaced:  "
                + "/".join(
                    str(sum(s[k] for s in usable)) for k in ("own", "batch", "foreign", "unplaced")
                )
            )

            repeated: Counter = Counter()
            stolen: Counter = Counter()
            for s in usable:
                repeated.update(s["duplicated"].keys())
                stolen.update(item["quote_belongs_to"] for item in s["foreign_obligations"])
            if repeated:
                print("    ids given more than one disposition, by draws affected:")
                for rid, n in repeated.most_common():
                    print(f"        {rid}: {n}")
            if stolen:
                print("    requirements answered for from OUTSIDE the batch:")
                for rid, n in stolen.most_common():
                    print(f"        {rid}: {n} obligation(s) across all draws")

        for path, s in zip(files, scored):
            if s["status"] != "ok":
                print(f"    {path.name}: {s['status']} — {s['detail'][:100]}")

        report[batch_dir.name] = {"batch_ids": ids, "draws": scored}

    if report:
        out = root / "summary.json"
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nper-draw detail: {out}")


# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="draw",
        description="Draw the decompose request repeatedly against an editable prompt.",
    )
    parser.add_argument("--dir", type=Path, default=HERE / "work")
    sub = parser.add_subparsers(dest="command", required=True)

    mat = sub.add_parser("materialize", help="write the request out as editable files")
    mat.add_argument("--task", type=Path, required=True)
    mat.add_argument("--batch-size", type=int, default=DEFAULT_DECOMPOSE_BATCH_SIZE)
    mat.add_argument("--batch", default=None, help="only this batch index")
    mat.add_argument("--model", default=RunConfig().model)

    live = sub.add_parser("run", help="issue N live calls and score them")
    live.add_argument("-n", "--runs", type=int, default=5)
    live.add_argument("--batch", default=None)
    live.add_argument("--model", default=RunConfig().model)
    live.add_argument("--temperature", type=float, default=0.0)
    live.add_argument("--seed", default=str(RunConfig().seed), help="integer, or 'none'")
    live.add_argument("--vary-seed", action="store_true", help="step the seed per draw")
    live.add_argument(
        "--no-enum",
        action="store_true",
        help="requirement_id as free text instead of an enum of the batch's ids",
    )
    live.add_argument(
        "--no-explicit",
        action="store_true",
        help="drop the obligation `explicit` field from the response schema",
    )

    rep = sub.add_parser("summarize", help="score the saved runs; makes no calls")
    rep.add_argument("--batch", default=None)

    see = sub.add_parser("show", help="print the request exactly as the provider gets it")
    see.add_argument("--batch", default=None)
    see.add_argument("--model", default=RunConfig().model)
    see.add_argument("--json", action="store_true", help="the wire payload, verbatim")
    see.add_argument("--no-enum", action="store_true")
    see.add_argument("--no-explicit", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "materialize":
        materialize(args.task, args.dir, args.batch_size, args.batch, args.model)
    elif args.command == "run":
        run(
            args.dir,
            args.batch,
            args.runs,
            args.model,
            args.temperature,
            None if str(args.seed).lower() == "none" else int(args.seed),
            args.vary_seed,
            enum_ids=not args.no_enum,
            explicit=not args.no_explicit,
        )
    elif args.command == "show":
        show(
            args.dir,
            args.batch,
            args.model,
            args.json,
            enum_ids=not args.no_enum,
            explicit=not args.no_explicit,
        )
    else:
        summarize(args.dir, args.batch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
