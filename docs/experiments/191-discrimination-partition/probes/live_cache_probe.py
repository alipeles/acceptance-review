"""Ad hoc, live: does the provider actually cache the shared verdict prefix?

Takes two REAL post-fix verdict requests out of the transcript cache — different
calls that share ~90% of their text — and re-issues them back to back, reading
`prompt_tokens_details.cached_tokens`, which `_extract_usage` does not record.

Two different prompts, deliberately: re-sending one prompt twice would test
exact-duplicate caching, which is not the property in question. Prefix caching
is what makes the repeated diff cheap.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import litellm  # noqa: E402

records = []
for path in (ROOT / ".acceptance/cache/transcripts").iterdir():
    try:
        record = json.loads(path.read_text())
    except Exception:
        continue
    request = record.get("request", {})
    if request.get("response_schema", {}).get("name") != "_DefectVerdicts":
        continue
    if not request["messages"][-1]["content"].startswith("## Changed production code"):
        continue
    records.append(record)

records.sort(key=lambda r: r["request"]["messages"][-1]["content"])
print(f"post-fix verdict requests available: {len(records)}")
if len(records) < 3:
    sys.exit("need at least three")

picked = [records[0], records[len(records) // 2], records[-1]]
prompts = [r["request"]["messages"][-1]["content"] for r in picked]
shared = os.path.commonprefix(prompts)
print(f"shared prefix across the three: {len(shared):,} chars (~{len(shared) // 4:,} tokens)")
print(f"mean prompt: {sum(len(p) for p in prompts) // len(prompts):,} chars\n")

model = picked[0]["request"]["model"]
for index, record in enumerate(picked, start=1):
    request = record["request"]
    response = litellm.completion(
        model=model,
        messages=request["messages"],
        temperature=request.get("temperature", 0.0),
        seed=request.get("seed"),
        response_format={
            "type": "json_schema",
            "json_schema": request["response_schema"],
        },
    )
    usage = response.usage
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details else None
    share = f"{cached / usage.prompt_tokens:.0%}" if cached else "—"
    print(
        f"call {index}: prompt={usage.prompt_tokens:>6,}  "
        f"cached={('%s' % cached) if cached is not None else 'not reported':>6}  "
        f"({share} of the prompt)"
    )
