"""Compute an audit's rates from its labels and its attempts.

Separate from `run_audit.py` on purpose: the numbers must be recomputable from
the two committed files without re-running anything, and every earlier audit's
rates were worked out by hand and cannot be rechecked.

    .venv/bin/python dogfood-logs/45-injection-audits/score_audit.py \
        --labels dogfood-logs/45-injection-audits/labels/v9.json \
        --attempts dogfood-logs/45-injection-audits/injection-audit-v9.attempts.json

Two questions are answered, from the same labels:

- #334 (several candidate edits per defect): of the edits that passed the
  gates, how many put the named defect into the code, how many changed no
  behaviour at all, and what did a defect cost.
- #335 (verification split into two questions): how often does each question
  refuse a bad edit, and how often does it refuse a good one. The judged label
  is the ground truth; the verifier's own answer is read from the attempts and
  never from the labels.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

#: A label of `injects` means the edit made its named defect true. Everything
#: else is a bad edit for the verifier's purposes — including `unclear`, which
#: is counted separately as well, since a judge that could not tell is not
#: evidence that the verifier was wrong.
GOOD = "injects"

#: The outcomes where the tests were run against the edit and read. Only these
#: count toward the validity rate; a refused edit never became an observation.
COUNTED = ("killed", "survived")


def _pct(part: int, whole: int) -> str:
    return f"{part}/{whole} ({100 * part / whole:.0f}%)" if whole else f"{part}/0 (n/a)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--attempts", required=True, type=Path)
    args = parser.parse_args(argv)

    labels_doc = json.loads(args.labels.read_text(encoding="utf-8"))
    attempts_doc = json.loads(args.attempts.read_text(encoding="utf-8"))
    labels = {entry["defect_id"]: entry for entry in labels_doc["labels"]}
    attempts = {entry["defect_id"]: entry for entry in attempts_doc["attempts"]}

    missing = sorted(set(attempts) - set(labels))
    unknown = sorted(set(labels) - set(attempts))

    print(f"audit {attempts_doc['audit']} at {attempts_doc['revision']}")
    print(f"edits built by {attempts_doc['descriptor_model']}, k={attempts_doc['max_candidates']}")
    if missing:
        print(f"WARNING: {len(missing)} attempts carry no label, e.g. {missing[:3]}")
    if unknown:
        print(f"WARNING: {len(unknown)} labels match no attempt, e.g. {unknown[:3]}")

    outcomes = Counter(entry["outcome"] for entry in attempts.values())
    print("\n## Outcomes")
    for outcome, count in sorted(outcomes.items()):
        print(f"- {outcome}: {count}")

    # --- #334: the edits that passed the gates -----------------------------
    counted = [d for d, a in attempts.items() if a["outcome"] in COUNTED]
    judged = [d for d in counted if d in labels and "edit" in labels[d]]
    categories = Counter(labels[d]["edit"] for d in judged)
    injects = categories[GOOD]

    print("\n## #334 — validity of the edits that passed the gates")
    print(f"- edits counted (killed or survived): {len(counted)}, judged: {len(judged)}")
    for category, count in sorted(categories.items(), key=lambda item: -item[1]):
        print(f"- {category}: {_pct(count, len(judged))}")
    print(f"- put the named defect into the code: {_pct(injects, len(judged))}")

    # The share #334's Acceptance asks for by name. `changes_behaviour` is a
    # field this audit adds: the five categories cannot express it, because
    # "changed something else" and "changed nothing observable" are both
    # `unrelated`.
    with_field = [d for d in judged if "changes_behaviour" in labels[d]]
    unchanged = [d for d in with_field if labels[d]["changes_behaviour"] is False]
    print(f"- change no behaviour at all: {_pct(len(unchanged), len(with_field))}")
    if len(with_field) < len(judged):
        print(f"  ({len(judged) - len(with_field)} judged edits carry no behaviour-change label)")

    kills = [d for d in counted if attempts[d]["outcome"] == "killed"]
    real_kills = [d for d in kills if labels.get(d, {}).get("edit") == GOOD]
    print(f"- real kills: {_pct(len(real_kills), len(kills))}")

    # --- k and what a defect cost ------------------------------------------
    asked = [attempts[d]["candidates_asked"] for d in attempts if attempts[d]["candidates_asked"]]
    used = [attempts[d]["candidate_used"] for d in attempts if attempts[d].get("candidate_used")]
    spend = attempts_doc["spend"]
    edit_spend = spend.get("mutation descriptor", {})
    print("\n## #334 — what it cost")
    print(f"- defects asked about: {len(asked)}; candidate edits bought: {sum(asked)}")
    if used:
        print(f"- candidate used: {Counter(used).most_common()}")
    if asked:
        print(f"- candidates per defect asked about: {sum(asked) / len(asked):.2f}")
    if edit_spend:
        per_defect = edit_spend["cost_usd"] / len(asked) if asked else 0.0
        print(f"- edit building: ${edit_spend['cost_usd']:.4f}, {edit_spend['seconds']:.0f}s live")
        print(f"- cost per defect asked about: ${per_defect:.4f}")
    # Attempts files written before #366 carry neither field; both default to
    # "none", which is what those runs used.
    reasoning = attempts_doc.get("stage_reasoning") or {}
    print(f"- reasoning effort: {reasoning or 'none'}")
    for stage, row in sorted(spend.items()):
        if row.get("reasoning_tokens"):
            print(f"- {stage}: {row['reasoning_tokens']:,} reasoning tokens")
    print(f"- wall clock for the whole run: {attempts_doc['wall_clock_seconds']:.0f}s")

    # --- #335: each verification question, against the judged labels --------
    verified = [d for d in judged if attempts[d].get("verification_reason")]
    if not verified:
        print("\n## #335 — verification did not run in this audit")
        return 0

    good = [d for d in verified if labels[d]["edit"] == GOOD]
    bad = [d for d in verified if labels[d]["edit"] != GOOD]
    refused_bad = [d for d in bad if not attempts[d]["verified"]]
    refused_good = [d for d in good if not attempts[d]["verified"]]

    print("\n## #335 — the two questions against the judged labels")
    print(f"- bad edits refused: {_pct(len(refused_bad), len(bad))} (bar: at least 80%)")
    print(f"- good edits refused: {_pct(len(refused_good), len(good))} (bar: under 10%)")
    by_step = Counter(attempts[d]["refused_by"] for d in verified if not attempts[d]["verified"])
    for step, count in sorted(by_step.items(), key=lambda item: -item[1]):
        on_bad = sum(1 for d in refused_bad if attempts[d]["refused_by"] == step)
        on_good = sum(1 for d in refused_good if attempts[d]["refused_by"] == step)
        print(f"- refused by {step}: {count} ({on_bad} bad, {on_good} good)")

    clears = (
        len(bad)
        and len(good)
        and len(refused_bad) / len(bad) >= 0.80
        and len(refused_good) / len(good) < 0.10
    )
    print(f"\n**The bar is {'met' if clears else 'NOT met'} on this audit.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
