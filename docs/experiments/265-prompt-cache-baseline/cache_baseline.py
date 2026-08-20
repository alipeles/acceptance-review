"""Prompt-cache baseline for #265, measured off the local transcript corpus.

Run it:

    .venv/bin/python docs/experiments/265-prompt-cache-baseline/cache_baseline.py
    .venv/bin/python docs/experiments/265-prompt-cache-baseline/cache_baseline.py --json out.json

No model calls: it reads `.acceptance/cache/transcripts/` and nothing else.

## Why the cached figure is solved rather than read

No recording carries a cached-token count. `_extract_usage` only began keeping
`prompt_tokens_details` in #285 (`82e4ec7`), so every transcript written before
that date reports prompt/completion/total and `cost_usd` and nothing about the
cache. `cost_usd` is itself cache-aware, so `cached` is the only unknown in

    cost = in*(prompt - cached) + cached_rate*cached + out*completion

and can be solved per call:

    cached = (in*prompt + out*completion - cost) / (in - cached_rate)

Rates come from litellm's own price table — the table that produced `cost_usd`
in the first place, so the solve stays consistent with what generated the number.

**Once recordings made after #285 dominate the corpus, delete this solve and read
`usage["cached_tokens"]` directly.** `measured_share` in the output says how far
along that transition is.

## Why the corpus is not reproducible, and what is committed instead

`.acceptance/cache/` is gitignored and machine-local, so nobody else can re-run
this over the same inputs. That is why the computed output is committed beside
this script: the artifact is the finding, not the ability to recompute it. The
`corpus` block fingerprints what was read, so a later run that disagrees can be
told apart from a run over a different corpus.

Two properties of the corpus to keep in mind when reading any figure:

- it spans many runs, task files and prompt generations over roughly a month, so
  every number is a fleet average and not one run's profile;
- most of it is orphaned — recorded under prompts that are no longer in the tree,
  because a prompt edit re-keys its stage's requests and leaves the old records
  on disk. `current_prompt_share` reports how much is still live.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import litellm

TRANSCRIPTS = Path(".acceptance/cache/transcripts")

# Modules that issue model calls. The review pipeline's ten stages carry a
# `_STAGE` constant since #285; the two benchmark modules do not, because the
# harness is deliberately not part of a review run.
CALLING_MODULES = [
    "acceptance.requirement.obligations",
    "acceptance.requirement.linking",
    "acceptance.evidence.mapping",
    "acceptance.evidence.discrimination",
    "acceptance.coverage.classify",
    "acceptance.coverage.open_questions",
    "acceptance.coverage.unrequested",
    "acceptance.coverage.disposition",
    "acceptance.coverage.recommendations",
    "acceptance.coverage.declaration_comparison",
    "acceptance.benchmark.alignment",
    "acceptance.benchmark.instability",
]

# OpenAI caches only prefixes at or above this length, so a stage whose calls
# share less than this cannot cache however well its prompt is ordered. Verified
# against the provider's documentation on 2026-08-20; it is model-dependent and
# worth re-checking when the model moves.
MIN_CACHEABLE_PREFIX_TOKENS = 1024

# Where a stage's invariant section ends, for stages that mark one. Used to group
# sibling calls from a single run, which is the only grouping under which a
# shared prefix means anything.
INVARIANT_MARKERS = {
    "You map each candidate test": "## Candidate tests",
}


def stage_by_prompt() -> dict[str, str]:
    """Current system-prompt text -> the stage that sends it."""
    prompts: dict[str, str] = {}
    for name in CALLING_MODULES:
        module = importlib.import_module(name)
        stage = getattr(module, "_STAGE", None) or f"[harness] {name.rsplit('.', 1)[-1]}"
        for attr in dir(module):
            if "SYSTEM_PROMPT" not in attr:
                continue
            value = getattr(module, attr)
            if isinstance(value, str) and value.strip():
                prompts[value] = stage
    return prompts


def rates_for(model: str) -> tuple[float, float, float] | None:
    """(input, output, cache-read) per-token rates, or None if unpriced."""
    entry = litellm.model_cost.get(model) or litellm.model_cost.get(model.split("/", 1)[-1])
    if not entry:
        return None
    trio = (
        entry.get("input_cost_per_token"),
        entry.get("output_cost_per_token"),
        entry.get("cache_read_input_token_cost"),
    )
    return None if any(rate is None for rate in trio) else trio  # type: ignore[return-value]


def tokens_in(text: str, model: str) -> int:
    try:
        return int(litellm.token_counter(model=model, text=text))
    except Exception:
        return len(text) // 4  # only ever used for a threshold comparison


@dataclass
class Call:
    model: str
    system: str
    user: str
    prompt_tokens: int
    completion_tokens: int
    cost: float
    full_cost: float
    cached: float
    measured: bool
    recorded_at: datetime


def load_calls() -> tuple[list[Call], dict[str, int]]:
    skipped: dict[str, int] = defaultdict(int)
    calls: list[Call] = []

    for path in sorted(TRANSCRIPTS.glob("*.json")):
        record = json.loads(path.read_text())
        request = record.get("request") or {}
        usage = record.get("usage") or {}
        messages = request.get("messages")
        model = request.get("model", "")

        if not isinstance(messages, list) or not messages:
            skipped["not a chat completion"] += 1
            continue
        rates = rates_for(model)
        if rates is None:
            skipped["unpriced model"] += 1
            continue
        in_rate, out_rate, cached_rate = rates

        system = messages[0].get("content") if isinstance(messages[0], dict) else ""
        user = messages[1].get("content") if len(messages) > 1 else ""
        prompt_tokens = usage["prompt_tokens"]
        completion_tokens = usage["completion_tokens"]
        cost = usage["cost_usd"]
        full = in_rate * prompt_tokens + out_rate * completion_tokens

        # A recording made after #285 states the answer; anything older is solved.
        # Never default a missing count to zero: "this provider said nothing about
        # caching" and "nothing was served from cache" are different claims.
        recorded = usage.get("cached_tokens")
        if recorded is None:
            cached = max(0.0, (full - cost) / (in_rate - cached_rate))
            measured = False
        else:
            cached, measured = float(recorded), True

        calls.append(
            Call(
                model=model,
                system=system if isinstance(system, str) else "",
                user=user if isinstance(user, str) else "",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                full_cost=full,
                cached=cached,
                measured=measured,
                recorded_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
            )
        )
    return calls, dict(skipped)


@dataclass
class Cluster:
    snippet: str
    stage: str
    calls: list[Call] = field(default_factory=list)

    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def cached(self) -> float:
        return sum(c.cached for c in self.calls)

    @property
    def hit_rate(self) -> float:
        return 100 * self.cached / self.prompt_tokens if self.prompt_tokens else 0.0

    @property
    def zero_hits(self) -> int:
        return sum(1 for c in self.calls if c.cached < 0.5)

    @property
    def saved(self) -> float:
        return sum(c.full_cost - c.cost for c in self.calls)


def cluster(calls: list[Call], live: dict[str, str]) -> dict[str, Cluster]:
    """Group by system prompt, not by stage.

    Exact-matching the current `_SYSTEM_PROMPT` constants attributes only the
    live slice of the corpus. Clustering keeps the orphaned recordings visible
    and lets one stage's successive prompt versions be compared against each
    other, which is where the sharpest finding came from.
    """
    clusters: dict[str, Cluster] = {}
    for call in calls:
        key = hashlib.sha256(call.system.encode()).hexdigest()[:12]
        if key not in clusters:
            clusters[key] = Cluster(
                snippet=" ".join(call.system.split())[:58],
                stage=live.get(call.system, "—"),
            )
        clusters[key].calls.append(call)
    return clusters


def shared_prefix_tokens(entries: list[Call]) -> tuple[int, int]:
    """(tokens shared by the largest sibling group, size of that group).

    Sibling calls in ONE run share the invariant head of the user message; across
    runs they share only the system prompt. Stages that mark where their invariant
    section ends are grouped on it, which is a genuine within-run figure. The rest
    fall back to the common prefix over every call, which is a cross-run FLOOR and
    understates what a single run shares.
    """
    model = entries[0].model
    system_tokens = tokens_in(entries[0].system, model)
    flat = " ".join(entries[0].system.split())
    marker = next((m for opener, m in INVARIANT_MARKERS.items() if flat.startswith(opener)), None)

    if marker:
        groups: dict[str, list[Call]] = defaultdict(list)
        for call in entries:
            groups[call.user.split(marker)[0]].append(call)
        head, members = max(groups.items(), key=lambda kv: len(kv[1]))
        return system_tokens + tokens_in(head, model), len(members)

    users = [c.user for c in entries]
    first, last = min(users), max(users)
    shared = first
    for index, char in enumerate(first):
        if index >= len(last) or last[index] != char:
            shared = first[:index]
            break
    return system_tokens + tokens_in(shared, model), len(entries)


def build_report(calls: list[Call], skipped: dict[str, int]) -> dict[str, Any]:
    live = stage_by_prompt()
    clusters = cluster(calls, live)
    ranked = sorted(clusters.values(), key=lambda c: -c.prompt_tokens)

    prompt_tokens = sum(c.prompt_tokens for c in calls)
    cached = sum(c.cached for c in calls)
    cost = sum(c.cost for c in calls)
    full = sum(c.full_cost for c in calls)
    live_tokens = sum(c.prompt_tokens for c in ranked if c.stage != "—")

    fingerprint = hashlib.sha256(
        f"{len(calls)}:{prompt_tokens}:{round(cost, 6)}".encode()
    ).hexdigest()[:16]

    return {
        "corpus": {
            "fingerprint": fingerprint,
            "calls": len(calls),
            "distinct_system_prompts": len(clusters),
            "skipped": skipped,
            "current_prompt_share": round(100 * live_tokens / prompt_tokens, 1)
            if prompt_tokens
            else 0.0,
            "measured_share": round(100 * sum(1 for c in calls if c.measured) / len(calls), 1)
            if calls
            else 0.0,
        },
        "totals": {
            "prompt_tokens": prompt_tokens,
            "cached_tokens": int(cached),
            "cached_share_pct": round(100 * cached / prompt_tokens, 2) if prompt_tokens else 0.0,
            "recorded_cost_usd": round(cost, 4),
            "full_price_cost_usd": round(full, 4),
            "saved_usd": round(full - cost, 4),
            "saved_pct": round(100 * (full - cost) / full, 2) if full else 0.0,
            "calls_with_no_cache_hit": sum(1 for c in calls if c.cached < 0.5),
        },
        "clusters": [
            {
                "stage": c.stage,
                "opens": c.snippet,
                "calls": len(c.calls),
                "prompt_tokens": c.prompt_tokens,
                "mean_prompt_tokens": c.prompt_tokens // len(c.calls),
                "hit_rate_pct": round(c.hit_rate, 1),
                "calls_with_no_cache_hit": c.zero_hits,
                "saved_usd": round(c.saved, 4),
                "first_recorded": min(x.recorded_at for x in c.calls).strftime("%Y-%m-%d"),
                "last_recorded": max(x.recorded_at for x in c.calls).strftime("%Y-%m-%d"),
                "shared_prefix_tokens": shared_prefix_tokens(c.calls)[0]
                if len(c.calls) > 1
                else None,
                "within_run_prefix": any(
                    " ".join(c.calls[0].system.split()).startswith(opener)
                    for opener in INVARIANT_MARKERS
                ),
            }
            for c in ranked
        ],
        "provider_minimum_prefix_tokens": MIN_CACHEABLE_PREFIX_TOKENS,
    }


def render(report: dict[str, Any]) -> None:
    corpus, totals = report["corpus"], report["totals"]
    print(f"corpus {corpus['fingerprint']} — {corpus['calls']} calls, ", end="")
    print(f"{corpus['distinct_system_prompts']} distinct system prompts")
    print(f"  {corpus['current_prompt_share']}% of prompt tokens under a CURRENT prompt")
    print(f"  {corpus['measured_share']}% of calls carry a measured cached-token count")
    for reason, count in corpus["skipped"].items():
        print(f"  skipped {count}: {reason}")

    print(
        f"\n{totals['prompt_tokens']:,} prompt tokens | "
        f"{totals['cached_tokens']:,} cached ({totals['cached_share_pct']}%) | "
        f"${totals['recorded_cost_usd']} vs ${totals['full_price_cost_usd']} at full price | "
        f"saved ${totals['saved_usd']} ({totals['saved_pct']}%)"
    )
    print(f"{totals['calls_with_no_cache_hit']} of {corpus['calls']} calls cached nothing at all\n")

    head = (
        f"{'calls':>6}{'prompt tok':>12}{'mean':>8}{'hit%':>7}{'zero':>6}"
        f"{'prefix':>9}  {'stage':<28}opens"
    )
    print(head)
    print("-" * 124)
    for row in report["clusters"][:16]:
        prefix = row["shared_prefix_tokens"]
        flag = ""
        if prefix is not None and prefix < report["provider_minimum_prefix_tokens"]:
            flag = "!" if row["within_run_prefix"] else "?"
        print(
            f"{row['calls']:>6}{row['prompt_tokens']:>12,}{row['mean_prompt_tokens']:>8,}"
            f"{row['hit_rate_pct']:>6.1f}%{row['calls_with_no_cache_hit']:>6}"
            f"{(prefix if prefix is not None else 0):>8,}{flag:<1}  {row['stage']:<28}{row['opens']}"
        )
    print(
        f"\nprefix column: tokens sibling calls share. Under "
        f"{report['provider_minimum_prefix_tokens']:,} the provider cannot cache them at all.\n"
        "  ! measured within one run — the stage marks where its invariant section ends\n"
        "  ? a cross-run floor; one run may share more. Needs the direct measurement."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="also write the report here")
    args = parser.parse_args()

    if not TRANSCRIPTS.is_dir():
        raise SystemExit(f"no transcript corpus at {TRANSCRIPTS} — run from the repository root")

    calls, skipped = load_calls()
    if not calls:
        raise SystemExit("no priced chat completions in the corpus")

    report = build_report(calls, skipped)
    render(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
