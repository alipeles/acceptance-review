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
from typing import Any

from acceptance.config import DEFAULT_DECOMPOSE_BATCH_SIZE, RunConfig
from acceptance.llm import Mode, request_key
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.requirement.obligations import (
    _SYSTEM_PROMPT,
    _Decomposition,
    _locate_quotation,
    _user_prompt,
)
from acceptance.requirement.registry import build_registry
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import constrain

HERE = Path(__file__).resolve().parent
SYSTEM_FILE = "system.txt"
USER_FILE = "user.txt"
META_FILE = "meta.json"
TASK_COPY = "task.md"
RUNS_DIR = "runs"


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
    return assemble(
        [
            Block(BlockKind.INSTRUCTIONS, (batch_dir / SYSTEM_FILE).read_text(encoding="utf-8")),
            Block(BlockKind.SUBJECT, (batch_dir / USER_FILE).read_text(encoding="utf-8")),
        ]
    )


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


def run(
    root: Path,
    only: str | None,
    draws: int,
    model: str,
    temperature: float,
    seed: int | None,
    vary_seed: bool,
) -> None:
    for batch_dir in _batch_dirs(root, only):
        meta = json.loads((batch_dir / META_FILE).read_text(encoding="utf-8"))
        ids = meta["batch_ids"]
        client = RunConfig(
            model=model, mode=Mode.RECORD, temperature=temperature, seed=seed
        ).build_client()
        base = client.build_request(
            _messages(batch_dir),
            constrain(_Decomposition, {"requirement_id": ids}),
            {"size": meta["batch_size"]},
        )

        runs_dir = batch_dir / RUNS_DIR
        runs_dir.mkdir(exist_ok=True)
        existing = len(list(runs_dir.glob("run-*.json")))
        print(
            f"{batch_dir.name}: {draws} draw(s), model={model} temperature={temperature} "
            f"seed={'vary' if vary_seed else seed} ({existing} already saved)"
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

    rep = sub.add_parser("summarize", help="score the saved runs; makes no calls")
    rep.add_argument("--batch", default=None)

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
        )
    else:
        summarize(args.dir, args.batch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
