"""Score Jev's minimal reachability question against the cases whose reach is known.

Known reach: every killed case ran the edited line; of the 16 survivors Jev
called "fails" (``tuning-gap-categories.json``), 11 never run it and 5 run it
without changing anything asserted, from the coding agent's explanations.
The other survivors have no reach label and are only summarised.

Compared with the earlier reach question (the "reaches" half of the two-pass
request in ``run_jev_framing.py``) on the same cases.

Run:  .venv/bin/python docs/experiments/jev/m52/run_reach.py
Writes ``tuning-reach.json``.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import reach_prompt
import recorder
from run_jev_framing import TWO_QUESTIONS, answers
from run_jev_framing import body as framed_body
from run_prompts import _auc
from split import cases, load_split

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-reach.json"

NEVER_RUN = [
    "PySnooper/1/m1/tests/test_chinese.py::test_chinese",
    "thefuck/24/m0/tests/test_types.py::TestCorrectedCommand::test_equality",
    "thefuck/24/m0/tests/test_types.py::TestCorrectedCommand::test_hashable",
    "thefuck/24/m1/tests/test_types.py::TestCorrectedCommand::test_equality",
    "thefuck/30/m2/tests/rules/test_fix_file.py::test_not_file",
    "tqdm/2/m0/tqdm/tests/tests_tqdm.py::test_format_meter",
    "tqdm/2/m1/tqdm/tests/tests_tqdm.py::test_format_meter",
    "youtube-dl/14/m0/test/test_youtube_chapters.py::TestYoutubeChapters::test_youtube_chapters",
    "youtube-dl/14/m3/test/test_youtube_chapters.py::TestYoutubeChapters::test_youtube_chapters",
    "youtube-dl/25/m3/test/test_utils.py::TestUtil::test_js_to_json_realworld",
    "youtube-dl/39/m0/test/test_utils.py::TestUtil::test_limit_length",
]
RUN_NO_CHANGE = [
    "PySnooper/1/m0/tests/test_chinese.py::test_chinese",
    "thefuck/30/m0/tests/rules/test_fix_file.py::test_not_file",
    "youtube-dl/19/m1/test/test_YoutubeDL.py::TestYoutubeDL::test_prepare_filename",
    "youtube-dl/21/m3/test/test_utils.py::TestUtil::test_urljoin",
    "youtube-dl/41/m1/test/test_utils.py::TestUtil::test_unified_dates",
]


def group(case) -> str:
    if case.killed:
        return "killed"
    if case.case_id in NEVER_RUN:
        return "never-run"
    if case.case_id in RUN_NO_CHANGE:
        return "run-no-change"
    return "unlabelled-survivor"


def summary(p: dict[str, float], groups: dict[str, str]) -> dict:
    out: dict = {}
    for g in ("killed", "run-no-change", "never-run", "unlabelled-survivor"):
        v = sorted(p[k] for k in p if groups[k] == g)
        out[g] = {
            "n": len(v),
            "mean": round(sum(v) / len(v), 3),
            "at_or_above_0.5": sum(x >= 0.5 for x in v),
        }
    labelled = [(p[k], groups[k] != "never-run") for k in p if groups[k] != "unlabelled-survivor"]
    out["labelled"] = {
        "n": len(labelled),
        "auc": round(_auc(labelled), 3),
        "accuracy_at_0.5": round(sum((x >= 0.5) == y for x, y in labelled) / len(labelled), 3),
        "never_run_below_0.5": sum(x < 0.5 for x, y in labelled if not y),
        "reached_at_or_above_0.5": sum(x >= 0.5 for x, y in labelled if y),
    }
    never = [p[k] for k in p if groups[k] == "never-run"]
    reached = [p[k] for k in p if groups[k] in ("killed", "run-no-change")]
    out["never_run_below_lowest_reached"] = sum(x < min(reached) for x in never)
    return out


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
    assert all(k in tuning for k in NEVER_RUN + RUN_NO_CHANGE)
    groups = {c.case_id: group(c) for c in usable}

    with ThreadPoolExecutor(max_workers=8) as pool:
        new = dict(
            zip(
                groups,
                pool.map(lambda c: recorder.jev(reach_prompt.body(c)), usable),
                strict=True,
            )
        )
    p_new = {k: answers(r)["reaches"] for k, r in new.items()}
    p_old = {
        c.case_id: answers(recorder.jev(framed_body(c, TWO_QUESTIONS), replay_only=True))["reaches"]
        for c in usable
    }
    tokens = sum(r["response"]["usage"]["input_tokens"] for r in new.values()) / len(new)
    report = {
        "cases": len(usable),
        "minimal": summary(p_new, groups),
        "earlier": summary(p_old, groups),
        "minimal_mean_input_tokens": round(tokens),
        "never_run": {k: {"minimal": p_new[k], "earlier": p_old[k]} for k in NEVER_RUN},
        "run_no_change": {k: {"minimal": p_new[k], "earlier": p_old[k]} for k in RUN_NO_CHANGE},
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
