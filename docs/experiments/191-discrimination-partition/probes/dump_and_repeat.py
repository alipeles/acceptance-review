"""Dump one real verdict request, then ask it repeatedly at fixed seed.

Answers the question our own system structurally cannot: an identical request
replays from the transcript cache and never reaches a model, so "same prompt,
different answer" is invisible from inside a run. Here the same prompt is issued
three times live.
"""

import json
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

# The one with the fewest defects, so the dumped file is readable.
records.sort(key=lambda r: len(json.loads(r["response"])["verdicts"]))
record = records[len(records) // 3]
request = record["request"]

system = request["messages"][0]["content"]
user = request["messages"][-1]["content"]

dump = ROOT / ".acceptance" / "verdict-prompt-example.md"
dump.write_text(
    "# One verdict request, exactly as sent\n\n"
    f"model: `{request['model']}` · temperature: {request.get('temperature')} · "
    f"seed: {request.get('seed')} · partition: {request.get('partition')}\n\n"
    f"Prompt size: {len(user):,} chars.\n\n"
    "## SYSTEM\n\n```\n" + system + "\n```\n\n"
    "## USER\n\n```\n" + user + "\n```\n\n"
    "## The response it got\n\n```json\n"
    + json.dumps(json.loads(record["response"]), indent=2)
    + "\n```\n"
)
print(f"wrote {dump}  ({len(user):,} chars of user prompt)")

defect_lines = [line for line in user.splitlines() if line.startswith("- defect id=")]
test_lines = [line for line in user.splitlines() if line.startswith("- ") and "::" in line]
print(f"this batch: {len(defect_lines)} defect(s), {len(test_lines)} mapped test(s)")

if "--live" not in sys.argv:
    sys.exit(0)

print("\nsame prompt, three times, temperature 0, fixed seed:")
seen = []
for attempt in range(3):
    response = litellm.completion(
        model=request["model"],
        messages=request["messages"],
        temperature=request.get("temperature", 0.0),
        seed=request.get("seed"),
        response_format={"type": "json_schema", "json_schema": request["response_schema"]},
    )
    body = json.loads(response.choices[0].message.content)
    verdicts = {v["defect_id"]: v["would_be_caught"] for v in body["verdicts"]}
    seen.append(verdicts)
    print(f"  attempt {attempt + 1}: {verdicts}")

print()
print("identical across all three:", all(v == seen[0] for v in seen))
print(
    "recorded run's verdicts:   ",
    {v["defect_id"]: v["would_be_caught"] for v in json.loads(record["response"])["verdicts"]},
)
