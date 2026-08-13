"""Ad hoc: is the repeated diff actually landing in the provider's prompt cache?

Takes REAL recorded verdict prompts out of the transcript cache — not synthetic
ones, so the prefix length and content are exactly what a run sends — and
re-issues them through litellm, printing the raw usage including
`prompt_tokens_details`, which `_extract_usage` drops.

Two things it answers:
  1. how much of each verdict request is the invariant code block (the ceiling
     on what caching can save);
  2. whether the provider actually reports cached tokens on the second call.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

# load_dotenv walks up from the CALLING FILE, not cwd — a scratchpad script sees
# no project .env unless the path is given explicitly.
load_dotenv(ROOT / ".env")

CACHE = ROOT / ".acceptance/cache/transcripts"

verdicts = []
for path in CACHE.iterdir():
    try:
        record = json.loads(path.read_text())
    except Exception:
        continue
    request = record.get("request", {})
    if request.get("response_schema", {}).get("name") != "_DefectVerdicts":
        continue
    verdicts.append((path, record))

print(f"recorded _DefectVerdicts transcripts: {len(verdicts)}")
if not verdicts:
    sys.exit("no verdict transcripts yet — let the harness finish first")

# Group by seed so we compare calls from ONE run, which is where the prefix is
# shared. Different seeds are different runs and would not share a cache anyway.
by_seed = defaultdict(list)
for path, record in verdicts:
    by_seed[record["request"].get("seed")].append(record)

wanted = None
for arg in sys.argv[1:]:
    if arg.startswith("--seed="):
        wanted = int(arg.split("=", 1)[1])
if wanted is not None:
    seed, group = wanted, by_seed[wanted]
else:
    seed, group = max(by_seed.items(), key=lambda kv: len(kv[1]))
print(f"largest single-run group: seed={seed}, {len(group)} verdict calls")

prompts = [record["request"]["messages"][-1]["content"] for record in group]
shared = os.path.commonprefix(prompts)

total_prompt_tokens = sum(r.get("usage", {}).get("prompt_tokens", 0) for r in group)
total_cost = sum(r.get("usage", {}).get("cost_usd", 0.0) for r in group)

# Characters are a proxy; 1 token ~ 4 chars for English/code is close enough to
# size the opportunity, and the live call below gives the real number.
mean_len = sum(len(p) for p in prompts) / len(prompts)
print()
print(f"shared prefix:            {len(shared):>8,} chars")
print(f"mean verdict prompt:      {mean_len:>8,.0f} chars")
print(f"shared fraction:          {len(shared) / mean_len:>8.1%}")
print(f"prompt tokens, this run:  {total_prompt_tokens:>8,}")
print(f"cost, verdict stage:      ${total_cost:>8.4f}")
print(f"if the prefix were free:  ${total_cost * (1 - len(shared) / mean_len):>8.4f} (rough)")

if "--live" not in sys.argv:
    print("\n(pass --live to re-issue two of these and read cached_tokens)")
    sys.exit(0)

import litellm  # noqa: E402

model = group[0]["request"]["model"]
print(f"\nre-issuing two real verdict prompts against {model} ...")
for index, record in enumerate(group[:2]):
    request = record["request"]
    response = litellm.completion(
        model=model,
        messages=request["messages"],
        temperature=request.get("temperature", 0.0),
        seed=request.get("seed"),
    )
    usage = response.usage
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details else None
    print(
        f"  call {index + 1}: prompt={usage.prompt_tokens:,} "
        f"cached={cached if cached is not None else 'not reported'}"
    )
