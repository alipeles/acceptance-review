"""Why is the shared prefix not being cached?

Each verdict call constrains `defect_id` to the ids THAT call supplied, so every
call carries a different response schema. If the structured-output schema
participates in the cached prefix, that alone would defeat caching no matter how
much of the message text is shared.

Three conditions, same two message-prefixes throughout:
  A. as we send it today — per-call constrained schema
  B. identical schema on both calls
  C. no response_format at all
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
a, b = records[0], records[-1]
model = a["request"]["model"]
shared = os.path.commonprefix(
    [a["request"]["messages"][-1]["content"], b["request"]["messages"][-1]["content"]]
)
print(f"shared prefix: {len(shared):,} chars (~{len(shared) // 4:,} tokens), model {model}\n")


def issue(label, record, response_format):
    kwargs = dict(
        model=model,
        messages=record["request"]["messages"],
        temperature=0.0,
        seed=record["request"].get("seed"),
    )
    if response_format is not None:
        kwargs["response_format"] = response_format
    usage = litellm.completion(**kwargs).usage
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details else None
    print(f"  {label:<34} prompt={usage.prompt_tokens:>6,}  cached={cached}")


def schema_of(record):
    return {"type": "json_schema", "json_schema": record["request"]["response_schema"]}


print("A. per-call constrained schema (what we send today)")
issue("call 1", a, schema_of(a))
issue("call 2 (different schema)", b, schema_of(b))

print("\nB. identical schema on both calls")
issue("call 1", a, schema_of(a))
issue("call 2 (same schema as call 1)", b, schema_of(a))

print("\nC. no response_format at all")
issue("call 1", a, None)
issue("call 2", b, None)
