"""Re-take #191's pre-change instability baseline, now that the harness reads
the defect-verdict axis it was silently dropping.

Runs REPLAY-first by default. The original baseline recorded every transcript
for this case at these seeds, and the fix changed only how the harness *reads*
the responses — not one request. So a correct reconstruction of the case should
replay end to end and cost nothing, and a key miss is a signal that the
reconstruction is wrong (or the cache lost the run), not a licence to spend.
Pass --record to allow live calls.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/alipeles1/GoogleDrive/code/AI_acceptance_tool")
SCRATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from acceptance.benchmark.case import (  # noqa: E402
    BenchmarkCase,
    BenchmarkCaseInputs,
    BenchmarkCaseSource,
    GroundTruthLabels,
)
from acceptance.benchmark.instability import (  # noqa: E402
    DEFAULT_PERTURBATION,
    ObservingClient,
    measure_instability,
)
from acceptance.config import Mode, RunConfig  # noqa: E402
from acceptance.llm import ModelClient  # noqa: E402

CASE_ID = "167-gate2-run4"
MODEL = "openai/gpt-5.4-mini"
EXPECTED_DIGEST = "d9095f91e5f987c8"

parser = argparse.ArgumentParser()
parser.add_argument("--record", action="store_true", help="allow live calls on a key miss")
parser.add_argument("--out", default=str(SCRATCH / "baseline-instability.json"))
parser.add_argument(
    "--repo",
    default=None,
    help=(
        "a clone of this repository checked out at the case's head revision. "
        "Created if absent. Never the working repository: the perturbation "
        "copies whatever it is given and commits into the copy."
    ),
)
args = parser.parse_args()

mode = Mode.RECORD if args.record else Mode.REPLAY

regression = json.loads(
    (ROOT / "tests/fixtures/rating-regression" / CASE_ID / "case.json").read_text()
)
labels = GroundTruthLabels.from_dict(
    json.loads((ROOT / "tests/fixtures/rating-regression" / CASE_ID / "labels.json").read_text())
)
task_text = (ROOT / "tests/fixtures/rating-stability" / CASE_ID / "current-task.md").read_text()

repo = Path(args.repo) if args.repo else SCRATCH / "case-repo"
if not repo.is_dir():
    subprocess.run(["git", "clone", "-q", str(ROOT), str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "checkout", "-q", regression["head_revision"]], check=True
    )

case = BenchmarkCase(
    case_id=CASE_ID,
    source=BenchmarkCaseSource(kind="real_pr", identifier=CASE_ID),
    inputs=BenchmarkCaseInputs(
        repo=str(repo),
        task_text=task_text,
        base_revision=regression["base_revision"],
        head_revision=regression["head_revision"],
    ),
    ground_truth=labels,
)

config = RunConfig(model=MODEL, mode=mode)
store = config.build_client().store


def client_factory(run_config):
    return ObservingClient(
        model=run_config.model,
        mode=mode,
        store=store,
        temperature=run_config.temperature,
        seed=run_config.seed,
        embedding_model=run_config.embedding_model,
    )


report = measure_instability(
    case,
    models=[MODEL],
    runs_per_model=3,
    perturbation=DEFAULT_PERTURBATION,
    comparison_client=ModelClient(model=MODEL, mode=mode, store=store),
    client_factory=client_factory,
)

assert report.provenance.task_digest == EXPECTED_DIGEST, (
    f"task digest {report.provenance.task_digest} != the original baseline's {EXPECTED_DIGEST}; "
    "this is not the same case"
)

Path(args.out).write_text(json.dumps(report.to_dict(), indent=2) + "\n")
print("wrote", args.out)

for model in report.per_model:
    print(f"{model.model}: defect_verdict_distribution = {len(model.defect_verdict_distribution)}")
    print(f"  content differences: {model.content_difference_count}")
    print(f"  shape differences:   {model.shape_difference_count}")
if report.perturbation:
    p = report.perturbation
    print(f"perturbation {p.name}: {p.changed_judgements}/{p.watched_judgements} moved")
