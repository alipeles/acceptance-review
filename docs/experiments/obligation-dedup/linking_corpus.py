"""Read the recorded obligation-linking calls out of the transcript cache.

The shared extraction step for any de-duplication experiment. DR-259's threshold
analysis used an ad-hoc version of this; it is factored out here because the
parsing is where that analysis went wrong twice, and both mistakes are cheap to
inherit.

Run it directly for a survey of what the cache currently holds:

    .venv/bin/python docs/experiments/obligation-dedup/linking_corpus.py

**The cache is not an archive.** Transcripts are evicted. DR-259 lost #244's and
#228's linking calls mid-analysis and could not recover them, so an experiment
that depends on a particular run should start by checking it is still here — and
should copy what it needs somewhere durable before it begins.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CACHE = Path(".acceptance/cache/transcripts")

# The linking stage's response model. Identify calls by THIS, never by prompt
# text: the phrase "de-duplicating a set of obligations" also appears in
# recommendation and strength prompts whose content happens to discuss
# de-duplication (#144's own task file triggers it), and a text key is hostage to
# the next prompt reword besides. Measured on a 1,204-transcript cache, the text
# filter returned 180 calls where the schema filter returns 172.
LINKING_SCHEMA = "_Verdicts"

# The pre-#144-revision linking schema, listing obligations rather than pairs.
# Present in small numbers and NOT comparable — it asked a different question.
LEGACY_LINKING_SCHEMA = "_Links"


@dataclass
class Obligation:
    id: str
    description: str = ""
    behavior: str = ""

    def embedding_text(self) -> str:
        """What DR-259 embedded, and what its threshold is calibrated against.

        Must stay identical to `linking.embedding_text` in the product code.
        Changing what goes in here moves every distance and silently invalidates
        the 0.10 default without changing it.
        """
        return f"{self.description} {self.behavior}".strip()


@dataclass
class Pair:
    pair_id: str
    left: str
    right: str
    same_requirement: bool | None = None
    reason: str = ""

    def key(self) -> frozenset:
        return frozenset((self.left, self.right))


@dataclass
class Sweep:
    """One linking run over one obligation set, reassembled from its batches."""

    obligations: dict[str, Obligation] = field(default_factory=dict)
    pairs: list[Pair] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    @property
    def confirmed(self) -> list[Pair]:
        return [p for p in self.pairs if p.same_requirement]

    def distinct_pairs(self) -> dict[frozenset, Pair]:
        """Deduplicated on pair CONTENT.

        DR-259 initially conflated three runs of one task file into a single
        group — 33 calls where 11 were expected, 275 pair ids over 218 distinct
        pairs — which inflated every count. Dedupe before reporting anything.
        """
        out: dict[frozenset, Pair] = {}
        for pair in self.pairs:
            out.setdefault(pair.key(), pair)
        return out


def _prompt_of(request: dict) -> str:
    return "\n".join(
        m.get("content", "")
        for m in request.get("messages", [])
        if isinstance(m.get("content"), str)
    )


def _parse_batch(prompt: str) -> tuple[dict[str, Obligation], list[Pair]]:
    obligations: dict[str, Obligation] = {}
    pairs: list[Pair] = []
    current_pair: str | None = None
    current_ob: str | None = None

    for raw in prompt.splitlines():
        line = raw.strip()
        if line.startswith("[pair-"):
            current_pair = line.strip("[]")
            pairs.append(Pair(pair_id=current_pair, left="", right=""))
        elif line.startswith("A: [") or line.startswith("B: ["):
            current_ob = line.split("[", 1)[1].split("]", 1)[0]
            obligations.setdefault(current_ob, Obligation(id=current_ob))
            if pairs:
                if line.startswith("A: ["):
                    pairs[-1].left = current_ob
                else:
                    pairs[-1].right = current_ob
        elif line.startswith("description:") and current_ob:
            obligations[current_ob].description = line.split(":", 1)[1].strip()
        elif line.startswith("observable behavior:") and current_ob:
            obligations[current_ob].behavior = line.split(":", 1)[1].strip()

    return obligations, [p for p in pairs if p.left and p.right]


def load_batches(cache: Path = DEFAULT_CACHE) -> list[tuple[str, dict, list[Pair]]]:
    """Every recorded linking batch as (transcript name, obligations, pairs)."""
    batches = []
    for path in sorted(Path(cache).glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        request = record.get("request") or {}
        if (request.get("response_schema") or {}).get("name") != LINKING_SCHEMA:
            continue

        obligations, pairs = _parse_batch(_prompt_of(request))

        # The response is a JSON *string*, not a dict. Reading it as a dict
        # yields no verdicts and every pair silently looks unanswered — this
        # cost DR-259 a full wrong analysis pass before it was noticed.
        response = record.get("response")
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError:
                response = None
        verdicts = {}
        if isinstance(response, dict):
            verdicts = {v.get("pair_id"): v for v in response.get("verdicts", [])}

        for pair in pairs:
            verdict = verdicts.get(pair.pair_id)
            if verdict is not None:
                pair.same_requirement = bool(verdict.get("same_requirement"))
                pair.reason = verdict.get("reason", "")

        batches.append((path.name, obligations, pairs))
    return batches


def group_into_sweeps(batches, overlap: int = 5) -> list[Sweep]:
    """Reassemble batches into the runs they came from.

    Transcripts carry no run label, so the only signal is shared obligation ids:
    within one sweep batches share many, across sweeps they share one or two by
    slug collision, and the gap separates cleanly. `overlap` is that cut.
    """
    sweeps: list[Sweep] = []
    for name, obligations, pairs in batches:
        ids = set(obligations)
        for sweep in sweeps:
            if len(set(sweep.obligations) & ids) >= overlap:
                sweep.obligations.update(obligations)
                sweep.pairs.extend(pairs)
                sweep.calls.append(name)
                break
        else:
            sweep = Sweep(obligations=dict(obligations), pairs=list(pairs), calls=[name])
            sweeps.append(sweep)

    # Groups can become connected only after later batches join them.
    changed = True
    while changed:
        changed = False
        for i in range(len(sweeps)):
            for j in range(i + 1, len(sweeps)):
                if len(set(sweeps[i].obligations) & set(sweeps[j].obligations)) >= overlap:
                    sweeps[i].obligations.update(sweeps[j].obligations)
                    sweeps[i].pairs.extend(sweeps[j].pairs)
                    sweeps[i].calls.extend(sweeps[j].calls)
                    del sweeps[j]
                    changed = True
                    break
            if changed:
                break
    return sorted(sweeps, key=lambda s: -len(s.obligations))


def attribute_to_dogfood_runs(sweep: Sweep, logs: Path = Path("dogfood-logs")) -> list[str]:
    """Which committed dogfood runs this sweep's obligations appear in.

    A sweep with no match is still usable, but it has no committed task file
    behind it, so it cannot become a benchmark case.
    """
    matches = []
    for log in sorted(Path(logs).glob("*/output.log")):
        try:
            text = log.read_text()
        except OSError:
            continue
        if not text.strip():
            continue
        hits = sum(1 for oid in sweep.obligations if oid in text)
        if hits >= 5:
            matches.append(f"{log.parent.name} ({hits})")
    return matches


def main() -> None:
    cache = DEFAULT_CACHE
    if not cache.is_dir():
        print(f"no transcript cache at {cache}")
        return

    schemas = Counter()
    for path in sorted(cache.glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        request = record.get("request") or {}
        if request.get("kind") == "embedding":
            schemas["<embedding>"] += 1
        else:
            schemas[(request.get("response_schema") or {}).get("name", "<none>")] += 1

    print("transcripts by response schema:")
    for name, count in schemas.most_common():
        marker = "  <- linking" if name == LINKING_SCHEMA else ""
        if name == LEGACY_LINKING_SCHEMA:
            marker = "  <- legacy linking, NOT comparable"
        print(f"  {count:5d}  {name}{marker}")

    sweeps = group_into_sweeps(load_batches(cache))
    usable = [s for s in sweeps if len(s.obligations) >= 10]
    print(f"\n{len(sweeps)} sweeps, {len(usable)} with 10+ obligations:\n")
    for sweep in usable:
        distinct = sweep.distinct_pairs()
        merges = sum(1 for p in distinct.values() if p.same_requirement)
        runs = attribute_to_dogfood_runs(sweep)
        print(
            f"  {len(sweep.obligations):3d} obligations  "
            f"{len(distinct):4d} distinct pairs  "
            f"{merges:3d} merges  {len(sweep.calls):3d} calls"
        )
        print(f"       runs: {', '.join(runs) if runs else '(no committed dogfood log matches)'}")


if __name__ == "__main__":
    main()
