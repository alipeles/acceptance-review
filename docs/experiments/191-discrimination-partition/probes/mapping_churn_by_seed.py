"""How much does the mapped test set churn between two runs that differ ONLY
by seed?

Seeds 1001 and 1002 are used by no perturbation run, so they separate cleanly —
unlike seed 1000, which the perturbed run shares. Same repo, same commit, same
task, same code. Any difference in which tests are mapped to which criterion is
mapping instability and nothing else.
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / ".acceptance/cache/transcripts"
MARKER = "test_unrelated_addition_for_perturbation_measurement"

mapped = defaultdict(lambda: defaultdict(set))  # seed -> obligation -> tests
offered = defaultdict(set)  # seed -> tests the mapper was shown

for path in CACHE.iterdir():
    try:
        record = json.loads(path.read_text())
    except Exception:
        continue
    request = record.get("request", {})
    if request.get("response_schema", {}).get("name") != "_Mappings":
        continue
    seed = request.get("seed")
    if seed not in (1001, 1002):
        continue
    if MARKER in request["messages"][-1]["content"]:
        continue
    for mapping in json.loads(record["response"]).get("mappings", []):
        offered[seed].add(mapping["test_id"])
        for obligation_id in mapping.get("obligation_ids", []):
            mapped[seed][obligation_id].add(mapping["test_id"])

a, b = mapped[1001], mapped[1002]
print(f"tests judged: seed 1001 -> {len(offered[1001])}, seed 1002 -> {len(offered[1002])}")
print(f"criteria with at least one mapped test: {len(a)} vs {len(b)}\n")

ids = sorted(set(a) | set(b))
identical = 0
rows = []
for obligation_id in ids:
    before, after = a.get(obligation_id, set()), b.get(obligation_id, set())
    if before == after:
        identical += 1
        continue
    rows.append((obligation_id, before, after))

print(f"criteria whose mapped set is IDENTICAL across the two runs: {identical} of {len(ids)}")
print(f"criteria whose mapped set CHANGED:                          {len(rows)} of {len(ids)}\n")

total_added = total_removed = 0
for obligation_id, before, after in rows:
    added, removed = after - before, before - after
    total_added += len(added)
    total_removed += len(removed)

print(f"test-links added across the run:   {total_added}")
print(f"test-links removed across the run: {total_removed}\n")

print("the ten largest swings:")
for obligation_id, before, after in sorted(rows, key=lambda r: -(len(r[1] ^ r[2])))[:10]:
    added, removed = after - before, before - after
    print(f"  {obligation_id}: {len(before)} -> {len(after)}  (+{len(added)} -{len(removed)})")
