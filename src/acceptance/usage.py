"""Per-stage token, cost and cache accounting for one run (#264).

We spend real money on live runs, and until this existed not a cent of it was
attributable: `llm.py` recorded usage into each transcript, but nothing
aggregated it and nothing retained which stage had issued the call.

**Two quantities, and confusing them produces a false number.** A replayed call
makes no request and costs this run nothing, while the transcript it replays
holds what that call cost *when it was recorded*. Both are wanted — "what did
this run spend" and "what did this evidence cost to produce" — so both are
reported, separately and by name:

- `run_spend_usd` counts only calls answered by the provider. It is the bill.
- `evidence_cost_usd` counts every call, whenever it was paid for. It is what
  producing this review's evidence cost in total.

`run_spend_usd <= evidence_cost_usd` always, and on a fully replayed run the
first is zero while the second is not.

**None of this may enter review state or the rendered report.** Cost varies
between two recordings of the same review, so a byte-identical rerun (M0.5) is
impossible if it does. This module is consumed by the CLI, which prints it to
stderr for exactly the reason the run id goes there.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from acceptance.llm import SERVED_FROM_PROVIDER

# Every token field an aggregate sums. Cache-creation and cache-write counts are
# summed but not shown per stage — they explain a cost figure when one is being
# investigated, and cluttering the common case with them helps nobody.
_TOKEN_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_tokens",
    "cache_creation_tokens",
    "cache_write_tokens",
)


class StageUsage(BaseModel):
    """What one pipeline stage cost, and where its answers came from."""

    stage: str
    provider_calls: int = 0
    replayed_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_write_tokens: int = 0
    run_spend_usd: float = 0.0
    evidence_cost_usd: float = 0.0

    # Cached-token accounting is kept over only the calls that REPORTED it, so a
    # provider that says nothing about caching cannot be mistaken for one
    # reporting a 0% hit rate. `cached_prompt_tokens` is None when no call in the
    # stage reported anything.
    cached_tokens: int | None = None
    measured_prompt_tokens: int = 0

    @property
    def calls(self) -> int:
        return self.provider_calls + self.replayed_calls

    @property
    def cached_prompt_share(self) -> float | None:
        """Fraction of this stage's prompt tokens the provider served from cache.

        `None` means unmeasured — either no call reported a cached-token count,
        or the calls that did reported no prompt tokens to divide by. It is
        deliberately not 0.0: "we did not measure" and "nothing was cached" are
        the two answers this whole feature exists to tell apart.
        """
        if self.cached_tokens is None or self.measured_prompt_tokens <= 0:
            return None
        return self.cached_tokens / self.measured_prompt_tokens


class RunUsage(BaseModel):
    """Every stage that issued a call, plus the run's two totals."""

    stages: list[StageUsage] = []

    @property
    def run_spend_usd(self) -> float:
        return sum(stage.run_spend_usd for stage in self.stages)

    @property
    def evidence_cost_usd(self) -> float:
        return sum(stage.evidence_cost_usd for stage in self.stages)

    @property
    def provider_calls(self) -> int:
        return sum(stage.provider_calls for stage in self.stages)

    @property
    def replayed_calls(self) -> int:
        return sum(stage.replayed_calls for stage in self.stages)


def _number(usage: Mapping[str, Any], name: str) -> float | None:
    """One numeric usage field, or None if it is missing or not a number.

    Transcripts are long-lived: one recorded before a field existed simply lacks
    it, and one recorded by an injected completion_fn may hold anything. Neither
    is an error — the figure is an annotation, and losing it must never fail a
    review that otherwise completed.
    """
    value = usage.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def summarize(calls: Iterable[Mapping[str, Any]]) -> RunUsage:
    """Fold `ModelClient.observed_calls` into a per-stage aggregate.

    Stages come out sorted by name so that two runs over the same input produce
    the same rows in the same order — the footer is on stderr and out of the
    byte-identical guarantee, but a report that reshuffles itself between runs is
    unreadable regardless.
    """
    by_stage: dict[str, StageUsage] = {}

    for call in calls:
        stage_name = call.get("stage") or ""
        stage = by_stage.setdefault(stage_name, StageUsage(stage=stage_name))
        usage = call.get("usage") or {}
        from_provider = call.get("served_from") == SERVED_FROM_PROVIDER

        if from_provider:
            stage.provider_calls += 1
        else:
            stage.replayed_calls += 1

        for field in _TOKEN_FIELDS:
            value = _number(usage, field)
            if value is None:
                continue
            if field == "cached_tokens":
                # Tracked against its own denominator — see `cached_prompt_share`.
                stage.cached_tokens = (stage.cached_tokens or 0) + int(value)
                prompt = _number(usage, "prompt_tokens")
                if prompt is not None:
                    stage.measured_prompt_tokens += int(prompt)
            else:
                setattr(stage, field, getattr(stage, field) + int(value))

        cost = _number(usage, "cost_usd")
        if cost is not None:
            stage.evidence_cost_usd += cost
            if from_provider:
                stage.run_spend_usd += cost

    return RunUsage(stages=[by_stage[name] for name in sorted(by_stage)])


def _share(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def render(usage: RunUsage) -> str:
    """The footer, as the CLI prints it.

    Says "recorded" rather than "spent" for the second money column on purpose:
    a reader glancing at a replayed run must not read a dollar figure as a bill
    they just incurred.
    """
    if not usage.stages:
        return "Model usage: no model call was made."

    rows = [
        (
            stage.stage,
            f"{stage.calls} ({stage.provider_calls} live / {stage.replayed_calls} replayed)",
            f"{stage.prompt_tokens:,}",
            f"{stage.completion_tokens:,}",
            _share(stage.cached_prompt_share),
            f"${stage.run_spend_usd:.4f}",
            f"${stage.evidence_cost_usd:.4f}",
        )
        for stage in usage.stages
    ]
    header = ("stage", "calls", "prompt", "output", "cached", "this run", "recorded")
    widths = [max(len(row[i]) for row in (header, *rows)) for i in range(len(header))]

    def line(row: tuple[str, ...]) -> str:
        cells = [row[0].ljust(widths[0])] + [row[i].rjust(widths[i]) for i in range(1, len(row))]
        return "  " + "  ".join(cells).rstrip()

    lines = ["Model usage by stage:", line(header), line(tuple("-" * w for w in widths))]
    lines.extend(line(row) for row in rows)
    lines.append(
        f"  this run spent ${usage.run_spend_usd:.4f} "
        f"on {usage.provider_calls} live call(s); "
        f"the evidence cost ${usage.evidence_cost_usd:.4f} to record "
        f"({usage.replayed_calls} call(s) replayed at no cost to this run)"
    )
    return "\n".join(lines)
