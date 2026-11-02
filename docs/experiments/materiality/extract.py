"""Pull a labeling sample out of a stored review JSON.

Usage: python3 extract.py <repo> <review.json> <out.json>
Emits one item per obligation named in the verdict rationale (not implemented or
non-discriminating test evidence) and one per unrequested-change finding, each
with everything a reader needs to judge it without opening the repo.
"""
import ast, json, re, subprocess, sys
from pathlib import Path

repo, review_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
r = json.load(open(review_path))
head = r["reviewed_revision"]

def git_show(path):
    try:
        return subprocess.run(["git", "-C", str(repo), "show", f"{head}:{path}"],
                              capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None

_src_cache = {}
def test_source(test_id):
    path, _, name = test_id.partition("::")
    name = name.split("[")[0]
    if path not in _src_cache:
        _src_cache[path] = git_show(path)
    src = _src_cache[path]
    if not src:
        return None
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(src, node)
    return None

hunks = {}
for f in r["change_set"]["files"]:
    for h in f["hunks"]:
        hunks[f"{f['path']}#{h['header']}"] = {"path": f["path"], "header": h["header"], "content": h["content"]}

task_text = r["task_source"]["text"]
reqs = {q["id"]: q for q in r["requirement_map"]["requirements"]}
defects_by_ob = {d["obligation_id"]: d["defects"] for d in r["defect_sets"]}
mut_by_defect = {}
for m in r["mutation_attempts"]:
    mut_by_defect.setdefault(m["defect_id"], []).append(m)
recs_by_ob = {}
for rec in r["recommendations"]:
    recs_by_ob.setdefault(rec["obligation_id"], []).append(rec)

rationale = r["completion"]["rationale"]
named = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", rationale))

items = []
for n, ob in enumerate(r["obligation_map"], 1):
    if ob["id"] not in named:
        continue
    try:
        ob_json = json.loads(ob["description"]) if ob["description"].startswith("{") else None
    except Exception:
        ob_json = None
    tests = []
    for t in ob.get("test_evidence", []):
        tid = t if isinstance(t, str) else t.get("test_id") or t.get("ref") or json.dumps(t)
        tests.append({"id": tid, "source": test_source(tid)})
    code = []
    for ref in ob.get("coverage_refs", []):
        key = ref if isinstance(ref, str) else ref.get("ref", "")
        if key in hunks:
            code.append(hunks[key])
        else:
            code.append({"path": key, "header": "", "content": None})
    defects = []
    for d in defects_by_ob.get(ob["id"], []):
        muts = mut_by_defect.get(d["id"], [])
        defects.append({
            "id": d["id"], "type": d["type"], "description": d["description"],
            "expected_behavior": d.get("expected_behavior"), "defective_behavior": d.get("defective_behavior"),
            "code_refs": d.get("code_refs", []),
            "mutation": [{"outcome": m["outcome"], "reason": m.get("reason"), "killing_tests": m.get("killing_tests", []),
                          "tests_run": m.get("tests_run", [])} for m in muts],
        })
    items.append({
        "kind": "obligation", "ordinal": n, "id": ob["id"],
        "description": ob["description"], "observable_behavior": ob.get("observable_behavior"),
        "type": ob["type"], "importance": ob["importance"], "explicit": ob["explicit"],
        "required_evidence": ob.get("required_evidence"),
        "source_spans": [s.get("text") for s in ob.get("source_spans", [])],
        "coverage_status": ob["coverage_status"], "evidence_class": ob["evidence_class"],
        "covered_defects": ob.get("covered_defects"), "enumerated_defects": ob.get("enumerated_defects"),
        "code": code, "tests": tests, "defects": defects,
        "recommendations": [{k: v for k, v in rec.items() if k != "obligation_id"} for rec in recs_by_ob.get(ob["id"], [])],
    })

for n, f in enumerate([f for f in r["findings"] if f["type"] == "unrequested_change"], 1):
    code = []
    for l in f.get("links", []):
        key = l.get("ref", "")
        code.append(hunks.get(key, {"path": key, "header": "", "content": None}))
    items.append({"kind": "unrequested_change", "ordinal": n, "id": f"unrequested-{n}",
                  "description": f["description"], "severity": f["severity"],
                  "related_obligation": f.get("related_obligation"), "code": code})

sample = {"repo": repo.name, "reviewed_revision": head, "verdict": r["completion"]["verdict"],
          "rationale": rationale, "task_text": task_text,
          "requirements": [{"id": q["id"], "section": q["section"], "text": q["span"]["text"]} for q in r["requirement_map"]["requirements"]],
          "obligation_count": len(r["obligation_map"]), "items": items}
out.write_text(json.dumps(sample, indent=1))
print(f"{len(items)} items -> {out}")
