"""Two Jev prompt changes aimed at its false "fails" on surviving mutants.

Both use the "context + description" content (change request, file, original
hunk, test source, defect description) and change only how the job is framed:

- ``framed``: one yes/no question, with a situation and criteria that explain
  mutation testing: every mutant meets every test, so many tests never run the
  edited line; a test catches a mutant only if it runs the edited line AND the
  edit changes something it asserts on.
- ``two-pass``: the same framing, as two yes/no questions in one request:
  ``reaches`` (does the test run the edited line?) and ``fails_if_reached``
  (supposing it does, would it fail?). Combined in code: the probability of a
  kill is p(reaches) x p(fails_if_reached), and the gated decision is "fails"
  only when both answers lean yes.

"Runs the edited line", not "invokes the modified code": 7 of the 16 false
positives call the edited function but take a different branch.

Recorded through ``recorder.jev`` (new request bodies, so new keys; the
earlier variants' recordings are untouched).

Run:  .venv/bin/python docs/experiments/jev/m52/run_jev_framing.py
Writes ``tuning-jev-framing.json``.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import recorder
from classify_gap import no_tools
from run_prompts import score
from split import cases, load_split
from thresholds import calibration

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-jev-framing.json"
BASE = "context+description"
JEV_PER_TOKEN = 0.042 / 1_000_000

SITUATION = (
    "We are running mutation testing to find out which tests catch which defects. A mutant "
    "is the project's code with one small mechanical edit applied. Every mutant is run "
    "against every test, so most tests were not written with this mutant in mind, and many "
    "never execute the edited line at all. A test catches a mutant only when both are true: "
    "(1) with its own inputs, the test actually executes the edited line; and (2) the edit "
    "changes something the test asserts on, so an assertion fails or an error is raised. "
    "The change request, the original code, the test, and the edit are shown."
)

ONE_QUESTION = {
    "fails": {
        "type": "noul",
        "instructions": (
            "Would this test fail with this mutant in place? Judge both parts: does the test, "
            "with its own inputs, actually execute the edited line; and if it does, does the "
            "edit change something the test asserts on?"
        ),
        "criteria": {
            "true": (
                "The test executes the edited line, and the edit changes a value or behaviour "
                "the test checks, so an assertion fails or an error is raised."
            ),
            "false": (
                "The test never executes the edited line (it calls other code, or its inputs "
                "always take a branch that skips the line), or it executes it but nothing it "
                "asserts on changes."
            ),
        },
    }
}

TWO_QUESTIONS = {
    "reaches": {
        "type": "noul",
        "instructions": "With its own inputs, does this test execute the edited line?",
        "criteria": {
            "true": "At least one call the test makes runs the edited line.",
            "false": (
                "The test calls other code, or its inputs always take a branch that skips the "
                "edited line, or the module holding it is never used by the test."
            ),
        },
    },
    "fails_if_reached": {
        "type": "noul",
        "instructions": (
            "Suppose this test does execute the edited line. Would the edit then change "
            "something the test asserts on, so that an assertion fails or an error is raised?"
        ),
        "criteria": {
            "true": "The edit changes a value or behaviour the test checks.",
            "false": (
                "The test's assertions come out the same with the edit, for example because "
                "the changed value is not what the test checks, or the result is equivalent."
            ),
        },
    },
}


def body(case, questions) -> dict:
    state = {"situation": SITUATION}
    state.update(prompts.parts(case, BASE))
    return {"model": "jev-latest", "state": state, "questions": questions}


def answers(record) -> dict[str, float]:
    return {k: float(v["noul"]) for k, v in record["response"]["answers"].items()}


def clears_survivors(p, label) -> dict:
    """The most survivors Jev can clear with no killed case cleared."""
    first_kill = min(p[k] for k, y in label.items() if y)
    cleared = [k for k, y in label.items() if p[k] < first_kill]
    return {
        "lowest_kill_p": round(first_kill, 3),
        "survivors_cleared": len(cleared),
        "survivors_total": sum(not y for y in label.values()),
    }


def with_opus(p, label, opus, opus_cost, jev_cost, lo) -> dict:
    right, cost, escalated = 0, 0.0, 0
    for k, y in label.items():
        cost += jev_cost[k]
        if p[k] <= lo:
            says = False
        else:
            says, escalated = opus[k], escalated + 1
            cost += opus_cost[k]
        right += says == y
    n = len(label)
    return {
        "lo": lo,
        "accuracy": round(right / n, 3),
        "escalated_share": round(escalated / n, 3),
        "cost_per_case": round(cost / n, 4),
    }


def main() -> int:
    tuning = set(load_split()["tuning"])
    usable = []
    for c in cases():
        if c.case_id in tuning:
            try:
                prompts.mutated_hunk(c)
                usable.append(c)
            except prompts.CannotBuild:
                pass
    label = {c.case_id: c.killed for c in usable}
    gap = json.loads((HERE / "tuning-gap-categories.json").read_text(encoding="utf-8"))
    false_pos = {r["case_id"] for r in gap["rows"] if not r["killed"]}

    def run(c):
        one = recorder.jev(body(c, ONE_QUESTION))
        two = recorder.jev(body(c, TWO_QUESTIONS))
        base = recorder.jev(prompts.jev_body(c, BASE), replay_only=True)
        return c.case_id, one, two, base

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, usable))

    opus, opus_cost = {}, {}
    for c in usable:
        o = no_tools(c)
        opus[c.case_id], opus_cost[c.case_id] = o["verdict"], o["cost_usd"]

    probs: dict[str, dict[str, float]] = {"before": {}, "framed": {}, "two-pass": {}}
    costs: dict[str, dict[str, float]] = {k: {} for k in probs}
    reach, fail_if = {}, {}
    for cid, one, two, base in results:
        probs["before"][cid] = recorder.jev_p_yes(base)
        probs["framed"][cid] = answers(one)["fails"]
        a = answers(two)
        reach[cid], fail_if[cid] = a["reaches"], a["fails_if_reached"]
        probs["two-pass"][cid] = a["reaches"] * a["fails_if_reached"]
        for name, rec in (("before", base), ("framed", one), ("two-pass", two)):
            costs[name][cid] = rec["response"]["usage"]["input_tokens"] * JEV_PER_TOKEN

    report: dict = {"cases": len(label), "variants": {}}
    for name, p in probs.items():
        pairs = [(p[k], label[k]) for k in label]
        s = score(pairs)
        s["ece"] = calibration(p, label)["ece"]
        s["false_fails"] = sum(p[k] >= 0.5 and not label[k] for k in label)
        s["missed_kills"] = sum(p[k] < 0.5 and label[k] for k in label)
        s["of_16_false_positives_now_below_0.5"] = sum(p[k] < 0.5 for k in false_pos)
        s["clears_survivors"] = clears_survivors(p, label)
        lo = s["clears_survivors"]["lowest_kill_p"] - 0.01
        s["survivors_cleared_then_opus"] = with_opus(p, label, opus, opus_cost, costs[name], lo)
        s["jev_cost_per_case"] = round(sum(costs[name].values()) / len(label), 7)
        report["variants"][name] = s
    gated = {k: reach[k] >= 0.5 and fail_if[k] >= 0.5 for k in label}
    report["two_pass_gated_at_0.5"] = {
        "accuracy": round(sum(gated[k] == label[k] for k in label) / len(label), 3),
        "false_fails": sum(gated[k] and not label[k] for k in label),
        "missed_kills": sum((not gated[k]) and label[k] for k in label),
    }
    report["reaches_question_alone"] = {
        "auc_for_kill": score([(reach[k], label[k]) for k in label])["auc"],
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
