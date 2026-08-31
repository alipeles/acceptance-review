"""Pilot the response shapes for the (defect, test) pair question (#314).

#314's Gate 1 question is not *build a call graph?* — that is settled — but how a
batch of pairs ANSWERS. DR-312's resolved question 2 names two arms and forbids
settling it by argument, because DR-173 is the record of an armchair-plausible
mapping shape that improved its headline number by losing 91 of 153 correct
mappings.

    LISTING  each test names the defects it would catch; a defect the test does
             not name is taken to survive. The response stays small and it is the
             list shape the model handles today. Shedding is INVISIBLE: a
             judgement the model quietly skipped is indistinguishable from one it
             answered "survives", and that silently un-covers a defect.

    VERDICT  each test carries an explicit verdict for EVERY offered defect.
             Shedding becomes visible, because a missing (test, defect) entry is
             detectable. But it is the shape DR-173 measured losing 59% of
             correct mappings, and it grows the response, which never amortizes
             — the caching discount is input-only.

Those two are the original arms and DR-314 chose between them. The three below
were added afterwards, to attack the cost the chosen shape turned out to carry on
a real review: #314's Gate 2 run spent 546,143 output tokens ($2.46) on the pair
stage, of which roughly 44% was defect-id echoes, 32% was reasons and 23% was
JSON scaffolding.

    REASONED  the shape the shipped stage actually uses — `defect_id`, `fails`
              and a freeform `reason`. It is NOT the same as the verdict arm:
              `defects/pair_mapping.py::_Judged` carries a reason and the verdict
              arm never did, so the verdict arm is the wrong denominator for a
              measurement about reason tokens. This arm exists to be the right
              one, and it is a baseline, not a candidate.

    KILLS-ONLY  the shipped schema, with a reason asked for only where the test
              FAILS and left empty where it survives. The tagged arms below try
              to make a survives reason cheaper; this one asks whether it is
              wanted. It exists because the reason-free verdict arm turned out to
              have the best recall of any arm measured, which pointed at the
              survives reason as the thing to drop rather than to encode
              smaller — but the verdict arm drops the reason on killing pairs
              too, and `report.py` renders that one to the reader.

    UNION     the same idea taken to where strict mode allows it: a union of two
              per-disposition entries, so a surviving pair returns `defect_id`
              and `fails` with NO `reason` field, and a killing pair returns one.
              It exists because `kills-only` recovered only 46% of the reason's
              cost — an empty `reason` key still costs about 10 output tokens
              against 18.5 for a written one, and `StrictResponseModel` forbids
              the optional field that would remove it. `obligations.py` already
              returns a union of per-disposition shapes and
              `supplied_ids.py::_constrained_nested` walks union members so the
              id constraint survives, so the machinery is in the repo already.

    TAGGED    reasoned, plus a closed enum of REJECTION RELATIONS in a field of
              its own, with the reason left empty wherever a relation fits. The
              enum is derived from the 12,323
              survives reasons the Gate 2 run recorded
              (`docs/experiments/pair-prefilter/survives-reasons.tsv`): a crude
              regex pass puts 73.3% of them in five relations, and the residual
              is mostly the same relations phrased differently. Relations are
              relations only — no repo vocabulary — so the enum transfers.

    TAGGED-SINGLE  the same relations, carried in the EXISTING `reason` field
              instead of a field of their own. It exists because the `tagged`
              arm above barely saved anything, and the reason it did not is
              scaffolding rather than the idea: a second field costs a key, a
              value, and an empty `reason` on every entry, which is about what
              the sentence it replaced cost. This arm keeps the shipped schema
              byte for byte and changes only the instruction. The enum is then
              stated in prose rather than enforced, which is the weakness #163
              exists to name, so its tag share is checked locally on an exact
              match and never parsed charitably.

    TAGGED-ALIAS  tagged, plus per-batch aliases. The request presents each
              defect and test as `D1`..`Dn` / `T1`..`Tn` beside its full id, and
              the response schema admits only the aliases. This is the id-echo
              half of the cost. NOTE it changes the REQUEST as well as the
              schema, which the other arms do not, so its figure is attributable
              to the arm as a whole rather than to the response shape alone.

Every arm sends the SAME `_SHARED_PROMPT`. Only the per-arm instruction, the
response schema, and (for the alias arm alone) the id rendering differ.

## What it scores against

#315's human-reviewed defect labels on the archetype fixtures, whose `killed_by`
lists the tests that would fail if the delivered code contained that defect. That
is ground truth, which is stronger than the control #314's acceptance names (the
current mapping stage's shared-mapping count) — that control compares against
another model stage's opinion, and this compares against a human's.

**The labelled defects are fed in directly rather than enumerated.** #315 exists
to separate "the enumerator missed the defect" from "the judge missed the kill",
and this pilot is choosing a shape for the judge. Feeding it the labelled set
holds the enumerator constant at perfect, so every difference measured here
belongs to the judge.

## Reading the figures

    recall     of the labelled kills, the share the arm predicted. THE STOP
               CONDITION: an arm whose recall falls below the other's, or below
               the control, is rejected however good its other figures look.
    precision  of the arm's predicted kills, the share that were labelled.
    kills/defect  the guard metric — DR-173's analogue of mean ids per test. An
               arm that wins by answering "no" more often shows up here as a
               collapsed mean, and that is the failure DR-173 exists to catch.
               It matters MORE for the tagged arms than it did for the original
               two: a menu of survives-relations makes "survives" the
               syntactically cheap answer, so a tagged arm could buy its recall
               stability with silence and look fine on recall alone.
    unanswered the pairs the arm returned nothing about. Reported as a count and
               as whether the shape lets us DETECT it at all, which is the whole
               case for the verdict arm. The tagged arms keep an explicit verdict
               per offered defect, so they keep that property; the assertion that
               they do is `_unanswered`, which counts answered ids against the
               offered set for every verdict-shaped arm alike.
    output tokens  the point of the last two arms. Reported per arm and as a
               ratio to BOTH the verdict arm (asked for) and the reasoned arm
               (the shape actually shipped, and the only honest denominator for
               a saving that will be realised against production).
    tag usage  what share of survives verdicts answered with a tag alone. If this
               is low the compression thesis fails even where recall holds.

Run with the sandbox off only if the provider host is not reachable; the default
model host is allowed. Writes findings.json beside this file.

    .venv/bin/python docs/experiments/pair-response-shape/pilot.py
"""

from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Literal

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from acceptance.config import DEFAULT_SEED, RunConfig
from acceptance.llm import Mode, StrictResponseModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.supplied_ids import constrain
from acceptance.usage import summarize

ARCHETYPES = REPO / "tests" / "fixtures" / "archetypes"
OUT = Path(__file__).resolve().parent / "findings.json"

LISTING_STAGE = "pair mapping pilot (listing)"
VERDICT_STAGE = "pair mapping pilot (verdict)"
REASONED_STAGE = "pair mapping pilot (reasoned)"
KILLS_ONLY_STAGE = "pair mapping pilot (kills-only)"
UNION_STAGE = "pair mapping pilot (union)"
TAGGED_STAGE = "pair mapping pilot (tagged)"
TAGGED_SINGLE_STAGE = "pair mapping pilot (tagged-single)"
ALIAS_STAGE = "pair mapping pilot (tagged-alias)"

ARMS = (
    "listing",
    "verdict",
    "reasoned",
    "kills-only",
    "union",
    "tagged",
    "tagged-single",
    "tagged-alias",
)
TAGGED_ARMS = ("tagged", "tagged-single", "tagged-alias")

# Arms drawn nine times instead of three. The two candidates left standing —
# `kills-only` and `union` — separated by a single labelled edge on one draw,
# which three seeds cannot resolve. `verdict` is drawn nine times as well
# because the qualification bar IS its worst seed: a minimum over nine draws is
# systematically lower than a minimum over three, so comparing a nine-seed
# candidate against a three-seed bar would be biased in the candidate's favour.
# `reasoned` for the same reason from the other side — it is the shape any
# change would REPLACE, so recommending a replacement while it holds three draws
# and the candidate holds nine would be the same error pointing the other way.
# That error is not hypothetical: on three seeds `kills-only` averaged 0.9688 and
# looked like the best arm here; on nine it averages 0.9410 and is the worst of
# these four. Everything else stays at three; those arms are already decided.
DEEP_SEED_ARMS = ("verdict", "reasoned", "kills-only", "union")
# Arms whose entries carry a `reason` field at all, so that whether it was filled
# is a question with an answer. `listing` and `verdict` have no such field and are
# left out, which also keeps their recorded entries in `findings.json` unchanged.
REASON_ARMS = ("reasoned", "kills-only", "union", *TAGGED_ARMS)

# The pair stage's share of #314's Gate 2 run, from
# `dogfood-logs/314-gate2-run1/output.log` and that run's ledger entry. Used only
# to project a measured token ratio onto a real review; nothing here is fitted to
# it.
GATE2_PAIR_OUTPUT_TOKENS = 546_143
GATE2_PAIR_OUTPUT_USD = 2.46
GATE2_RUN_USD = 4.25
OUTPUT_USD_PER_MTOK = 4.50

_SHARED_PROMPT = """\
You are given some concrete DEFECTS — specific ways the delivered code could be
wrong — and some TESTS from the same codebase.

THE QUESTION, applied to one (defect, test) pair at a time:

    If the delivered code contained THIS DEFECT, would THIS TEST fail?

Answer it as a matter of fact about the test's assertions, not about what the
test is named or what it seems to be about. A test fails on a defect only when
the defect changes a value the test actually asserts on. A test that exercises
the defective code but asserts nothing affected by the defect does NOT fail, and
neither does a test that stubs out the defective behaviour.

Judge every pair independently. Do not assume that a test which catches one
defect catches its neighbours, and do not assume a defect no test seems aimed at
is therefore uncaught."""

_LISTING_INSTRUCTION = """\
For each test, return `catches`: the ids of the defects that test would fail on.
Return an entry for EVERY test, using an empty list where the test would fail on
none of them."""

_VERDICT_INSTRUCTION = """\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries."""

_REASONED_INSTRUCTION = """\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries.
Keep `reason` to one short sentence."""

_KILLS_ONLY_INSTRUCTION = """\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries.

Where `fails` is true, give one short sentence in `reason` naming what the test
asserts that the defect would change. Where `fails` is false, leave `reason`
EMPTY and write nothing in it."""

_UNION_INSTRUCTION = """\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries.

An entry whose `fails` is true also carries `reason`: one short sentence naming
what the test asserts that the defect would change. An entry whose `fails` is
false carries NO `reason` field at all — not an empty one."""


# Derived from the 12,323 survives reasons recorded by #314's Gate 2 run. Three
# relations carry almost all of them; STUBBED and WRONG-LAYER are rare in that
# corpus but are kept because the shared prompt names stubbing explicitly as a
# way a test fails to fail, and an arm with no tag for it would push those into
# freeform for a reason that is about the menu rather than the judgement.
RELATIONS = (
    "NOT-EXERCISED",
    "NOT-ASSERTED",
    "SCOPE-ONLY",
    "STUBBED",
    "WRONG-LAYER",
    "OTHER",
)

_RELATION_MENU = """\
    NOT-EXERCISED  the test never runs the code the defect breaks
    NOT-ASSERTED   it runs that code but asserts nothing the defect would change
    SCOPE-ONLY     it checks a neighbouring concern, not this one
    STUBBED        it replaces the defective behaviour with a stub, mock or fake
    WRONG-LAYER    it constrains a different layer, so the defect cannot reach it
    OTHER          none of the five fits"""

_TAGGED_INSTRUCTION = f"""\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries.

Each entry also carries a REJECTION RELATION in `relation`, chosen from:

{_RELATION_MENU}

`relation` says why a test does NOT fail, so it applies only where `fails` is
false; set it to OTHER whenever `fails` is true.

When `fails` is false and one of the five relations fits, give that relation and
leave `reason` EMPTY. Otherwise — `fails` true, or no relation fits — give one
short sentence in `reason`."""

_TAGGED_SINGLE_INSTRUCTION = f"""\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries.

`reason` carries one of these REJECTION RELATIONS, written on its own with
nothing else, wherever one of them fits:

{_RELATION_MENU}

A relation says why a test does NOT fail, so it applies only where `fails` is
false. Where `fails` is false and one of the five fits, put that relation in
`reason` and write nothing else in it. Where `fails` is true, or where none of
the five fits, put one short sentence in `reason` instead."""

_ALIAS_INSTRUCTION = f"""\
Each defect and each test is labelled with a SHORT ID (D1, D2, … and T1, T2, …)
beside its full id. Answer with the short ids only.

For each test, return one entry per OFFERED DEFECT — every defect short id, not
only the ones it catches — with `fails` true if the test would fail on that
defect and false if it would not. A test with five defects offered returns five
entries.

Each entry also carries a REJECTION RELATION in `relation`, chosen from:

{_RELATION_MENU}

`relation` says why a test does NOT fail, so it applies only where `fails` is
false; set it to OTHER whenever `fails` is true.

When `fails` is false and one of the five relations fits, give that relation and
leave `reason` EMPTY. Otherwise — `fails` true, or no relation fits — give one
short sentence in `reason`."""


class _Listed(StrictResponseModel):
    test_id: str
    catches: list[str]


class _Listing(StrictResponseModel):
    tests: list[_Listed]


class _Judged(StrictResponseModel):
    defect_id: str
    fails: bool


class _Verdicted(StrictResponseModel):
    test_id: str
    defects: list[_Judged]


class _Verdicts(StrictResponseModel):
    tests: list[_Verdicted]


class _Reasoned(StrictResponseModel):
    defect_id: str
    fails: bool
    reason: str


class _ReasonedTest(StrictResponseModel):
    test_id: str
    defects: list[_Reasoned]


class _Reasonings(StrictResponseModel):
    tests: list[_ReasonedTest]


class _Survives(StrictResponseModel):
    """A pair the test does not fail on. No `reason` field exists to pay for.

    `fails` is `Literal[False]` rather than `bool` so the two members of the
    union are told apart by a value the response must carry anyway, rather than
    by which optional keys happen to be present. Strict mode has no optional
    keys, which is the whole reason this arm exists.
    """

    defect_id: str
    fails: Literal[False]


class _Kills(StrictResponseModel):
    defect_id: str
    fails: Literal[True]
    reason: str


class _UnionTest(StrictResponseModel):
    # `_Kills` first: pydantic resolves the union left to right, and putting the
    # member with more required fields first means a response carrying a reason
    # is never accepted as the shape that has none.
    test_id: str
    defects: list[_Kills | _Survives]


class _Unions(StrictResponseModel):
    tests: list[_UnionTest]


class _Tagged(StrictResponseModel):
    defect_id: str
    fails: bool
    # A Literal rather than a per-call enum: the relation set is fixed in the
    # software and identical on every call, which is the property that makes it
    # transferable across reviews. `constrain` leaves it alone — it only rewrites
    # the id fields named in `allowed`.
    relation: Literal[RELATIONS]  # type: ignore[valid-type]
    reason: str


class _TaggedTest(StrictResponseModel):
    test_id: str
    defects: list[_Tagged]


class _Taggings(StrictResponseModel):
    tests: list[_TaggedTest]


def _test_ids(head: Path) -> dict[str, str]:
    """Every test in the case's head revision, as pytest node id -> source.

    Node ids are built the way `killed_by` writes them in the labels —
    `<file>::<name>` — so predictions and labels are comparable without
    normalising either side.
    """
    found: dict[str, str] = {}
    for path in sorted(head.rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            module = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        relative = path.relative_to(head).as_posix()
        for node in module.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test"
            ):
                segment = "\n".join(lines[node.lineno - 1 : (node.end_lineno or node.lineno)])
                found[f"{relative}::{node.name}"] = segment
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for item in node.body:
                    if isinstance(
                        item, ast.FunctionDef | ast.AsyncFunctionDef
                    ) and item.name.startswith("test"):
                        segment = "\n".join(
                            lines[item.lineno - 1 : (item.end_lineno or item.lineno)]
                        )
                        found[f"{relative}::{node.name}::{item.name}"] = segment
    return found


def _cases() -> list[dict]:
    """Every archetype carrying defect labels, with its tests and source."""
    loaded = []
    for directory in sorted(ARCHETYPES.iterdir()):
        labels = directory / "labels.json"
        head = directory / "head"
        if not labels.is_file() or not head.is_dir():
            continue
        defects = json.loads(labels.read_text(encoding="utf-8")).get("defects") or []
        tests = _test_ids(head)
        if not defects or not tests:
            continue
        source = {
            path.relative_to(head).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(head.rglob("*.py"))
            if not path.name.startswith("test_") and "__pycache__" not in path.parts
        }
        loaded.append(
            {"name": directory.name, "defects": defects, "tests": tests, "source": source}
        )
    return loaded


def _aliases(ids: list[str], prefix: str) -> dict[str, str]:
    """Full id -> per-batch alias, assigned over the ids sorted.

    Sorted rather than in discovery order so two runs over the same case assign
    the same aliases, which a byte-identical rerun needs.
    """
    return {full: f"{prefix}{index}" for index, full in enumerate(sorted(ids), start=1)}


def _blocks(
    case: dict,
    instruction: str,
    defect_alias: dict[str, str] | None = None,
    test_alias: dict[str, str] | None = None,
) -> list[Block]:
    """The request. With no aliases this is byte-identical to what the listing,
    verdict and reasoned arms have always sent, which is what keeps their
    recordings valid and their figures comparable."""
    source = "\n\n".join(f"### {path}\n{text}" for path, text in sorted(case["source"].items()))
    if defect_alias is None:
        defects = "\n".join(
            f"- id={defect['id']}: {defect['description']}" for defect in case["defects"]
        )
    else:
        defects = "\n".join(
            f"- id={defect_alias[defect['id']]} (full id {defect['id']}): {defect['description']}"
            for defect in case["defects"]
        )
    if test_alias is None:
        tests = "\n\n".join(f"### {node}\n{body}" for node, body in sorted(case["tests"].items()))
    else:
        tests = "\n\n".join(
            f"### {test_alias[node]} (full id {node})\n{body}"
            for node, body in sorted(case["tests"].items())
        )
    return [
        Block(BlockKind.INSTRUCTIONS, f"{_SHARED_PROMPT}\n\n{instruction}"),
        Block(BlockKind.SUBJECT, f"## Delivered source\n\n{source}"),
        Block(BlockKind.SUBJECT, f"## Defects\n\n{defects}"),
        Block(BlockKind.SUBJECT, f"## Tests\n\n{tests}"),
    ]


def _decode(
    raw,
    arm: str,
    defect_alias: dict[str, str] | None,
    test_alias: dict[str, str] | None,
) -> tuple[list[tuple[str, list]], int]:
    """The response as (test id, judgements), with aliases resolved to full ids.

    An alias the response invents decodes to nothing, and the entry is DROPPED
    and counted rather than guessed at. That is the #163 rule applied to the
    alias arm: an id we cannot honour means the judgement we asked for was not
    obtained, which is a different claim from the model having considered the
    pair and answered no. Dropping it silently would let the alias arm buy
    coverage it never earned.
    """
    if defect_alias is None:
        return [(entry.test_id, list(entry.defects)) for entry in raw.tests], 0

    to_defect = {alias: full for full, alias in defect_alias.items()}
    to_test = {alias: full for full, alias in (test_alias or {}).items()}
    decoded: list[tuple[str, list]] = []
    undecodable = 0
    for entry in raw.tests:
        node = to_test.get(entry.test_id)
        if node is None:
            undecodable += len(entry.defects)
            continue
        judgements = []
        for judged in entry.defects:
            full = to_defect.get(judged.defect_id)
            if full is None:
                undecodable += 1
                continue
            judgements.append(judged.model_copy(update={"defect_id": full}))
        decoded.append((node, judgements))
    return decoded, undecodable


def _unanswered(case: dict, predicted: dict[str, set[str]], arm: str, decoded) -> dict:
    """How many pairs the arm said nothing about, and whether we could tell.

    In every verdict-shaped arm — verdict, reasoned, tagged, tagged-alias — a
    shed pair is detectable: the test's entry is present and a defect id is
    missing from it. In the listing arm it is NOT — a defect the model skipped
    and a defect it decided survives look identical, which is exactly DR-164's
    silent-filter trap. The count below is therefore an UNDERCOUNT for the
    listing arm, and saying so is the point.
    """
    total = len(case["defects"]) * len(case["tests"])
    answered = 0
    if arm == "listing":
        answered = len(predicted) * len(case["defects"])
    else:
        offered = {defect["id"] for defect in case["defects"]}
        for _node, judgements in decoded:
            answered += len({judged.defect_id for judged in judgements} & offered)
    return {
        "pairs": total,
        "unanswered": max(0, total - answered),
        "detectable": arm != "listing",
    }


def _relation_of(judged) -> tuple[str, bool]:
    """The relation a survives verdict carried, and whether it also wrote prose.

    Two shapes reach here. The `tagged` and `tagged-alias` arms carry a separate
    `relation` field whose values the schema enforces. The `tagged-single` arm
    carries the relation inside `reason`, where nothing enforces it, so the
    relation is recognised only on an EXACT match against the menu — anything
    else is counted as freeform rather than charitably parsed. A loose match
    would let the arm claim a tag share it did not earn, which is the figure the
    whole compression thesis rests on.
    """
    if hasattr(judged, "relation"):
        return judged.relation, bool(judged.reason.strip())
    text = judged.reason.strip()
    if text in RELATIONS and text != "OTHER":
        return text, False
    return "OTHER", bool(text)


def _score(cases: list[dict], predictions: dict[str, dict[str, set[str]]]) -> dict:
    """Recall, precision and the guard metric, pooled over every case."""
    labelled_edges: set[tuple[str, str, str]] = set()
    predicted_edges: set[tuple[str, str, str]] = set()
    defects = 0
    for case in cases:
        predicted = predictions.get(case["name"]) or {}
        defects += len(case["defects"])
        for defect in case["defects"]:
            for node in defect.get("killed_by") or []:
                labelled_edges.add((case["name"], defect["id"], node))
        for node, caught in predicted.items():
            for defect_id in caught:
                predicted_edges.add((case["name"], defect_id, node))

    hit = labelled_edges & predicted_edges
    return {
        "labelled_kills": len(labelled_edges),
        "predicted_kills": len(predicted_edges),
        "matched": len(hit),
        "recall": (len(hit) / len(labelled_edges)) if labelled_edges else None,
        "precision": (len(hit) / len(predicted_edges)) if predicted_edges else None,
        "kills_per_defect": (len(predicted_edges) / defects) if defects else None,
    }


def _arm_setup(arm: str, case: dict):
    """Schema, stage, instruction, allowed ids and alias maps for one call."""
    defect_ids = [defect["id"] for defect in case["defects"]]
    test_ids = sorted(case["tests"])
    if arm == "listing":
        return (
            _Listing,
            LISTING_STAGE,
            _LISTING_INSTRUCTION,
            {
                "test_id": test_ids,
                "catches": defect_ids,
            },
            None,
            None,
        )
    if arm == "verdict":
        return (
            _Verdicts,
            VERDICT_STAGE,
            _VERDICT_INSTRUCTION,
            {
                "test_id": test_ids,
                "defect_id": defect_ids,
            },
            None,
            None,
        )
    if arm == "reasoned":
        return (
            _Reasonings,
            REASONED_STAGE,
            _REASONED_INSTRUCTION,
            {
                "test_id": test_ids,
                "defect_id": defect_ids,
            },
            None,
            None,
        )
    if arm == "kills-only":
        # The SHIPPED schema again, and again only the instruction differs. The
        # tagged arms tried to make a survives reason cheaper; this one asks
        # whether it is needed at all. The reason on a KILLING pair is what
        # `report.py` renders to the reader, so it stays; the reason on a
        # surviving pair is the 32% of output this arm declines to buy.
        return (
            _Reasonings,
            KILLS_ONLY_STAGE,
            _KILLS_ONLY_INSTRUCTION,
            {
                "test_id": test_ids,
                "defect_id": defect_ids,
            },
            None,
            None,
        )
    if arm == "union":
        # The field is ABSENT on a surviving pair rather than present and empty,
        # which is the half of the reason's cost `kills-only` could not reach:
        # `StrictResponseModel` forbids optional fields, so a per-entry
        # instruction can only empty one. A union of per-disposition shapes is
        # how the repo already gets around that — `requirement/obligations.py`
        # returns one, and `supplied_ids.py::_constrained_nested` walks union
        # members precisely so the id constraint survives the detour.
        return (
            _Unions,
            UNION_STAGE,
            _UNION_INSTRUCTION,
            {
                "test_id": test_ids,
                "defect_id": defect_ids,
            },
            None,
            None,
        )
    if arm == "tagged":
        return (
            _Taggings,
            TAGGED_STAGE,
            _TAGGED_INSTRUCTION,
            {
                "test_id": test_ids,
                "defect_id": defect_ids,
            },
            None,
            None,
        )
    if arm == "tagged-single":
        # The SHIPPED schema, unchanged — only the instruction differs. That is
        # the whole point of this arm: the two-field `tagged` arm pays for a
        # `relation` key, an enum value, a `reason` key and an empty string on
        # every entry, and those four together cost about what the sentence they
        # replace cost. Carrying the tag in the existing field removes that
        # scaffolding. The price is that the enum is stated in prose rather than
        # enforced by the schema, which is exactly the weakness #163 was filed
        # about, so a tag here is CHECKED locally rather than guaranteed.
        return (
            _Reasonings,
            TAGGED_SINGLE_STAGE,
            _TAGGED_SINGLE_INSTRUCTION,
            {
                "test_id": test_ids,
                "defect_id": defect_ids,
            },
            None,
            None,
        )
    defect_alias = _aliases(defect_ids, "D")
    test_alias = _aliases(test_ids, "T")
    # The schema admits the aliases and nothing else, so a full id is not merely
    # rejected downstream but unrepresentable in the response.
    allowed = {
        "test_id": sorted(test_alias.values(), key=lambda alias: int(alias[1:])),
        "defect_id": sorted(defect_alias.values(), key=lambda alias: int(alias[1:])),
    }
    return _Taggings, ALIAS_STAGE, _ALIAS_INSTRUCTION, allowed, defect_alias, test_alias


def _projection(reasoned_tokens: float, arm_tokens: float) -> dict:
    """A measured token ratio carried onto #314's Gate 2 pair stage.

    Against the REASONED arm, because that is the shape the stage ships. The
    figure is an estimate and inherits every limit of a 13-case fixture set —
    see the README's note on defect-id length, which makes the alias arm's saving
    here a floor rather than a reading.
    """
    ratio = arm_tokens / reasoned_tokens if reasoned_tokens else None
    if ratio is None:
        return {"ratio_to_reasoned": None}
    projected_tokens = GATE2_PAIR_OUTPUT_TOKENS * ratio
    saved_tokens = GATE2_PAIR_OUTPUT_TOKENS - projected_tokens
    return {
        "ratio_to_reasoned": ratio,
        "projected_output_tokens": projected_tokens,
        "saved_output_tokens": saved_tokens,
        "saved_usd": saved_tokens * OUTPUT_USD_PER_MTOK / 1_000_000,
        "projected_run_usd": GATE2_RUN_USD - saved_tokens * OUTPUT_USD_PER_MTOK / 1_000_000,
    }


def main() -> int:
    cases = _cases()
    if not cases:
        print("no archetype cases carry defect labels", file=sys.stderr)
        return 1

    pairs = sum(len(case["defects"]) * len(case["tests"]) for case in cases)
    print(f"{len(cases)} cases, {sum(len(c['defects']) for c in cases)} defects, {pairs} pairs")

    # Repeated draws, because one draw is what DR-173 warns against and #150 is
    # the open issue on provider variance. The seed is the only thing varied —
    # same prompts, same cases, same temperature — so a spread across these is
    # draw variance and nothing else. Three is enough to see whether a
    # difference between the arms is larger than the noise around it; it is not
    # enough to put a confidence interval on either arm, and the write-up says so.
    seeds = [DEFAULT_SEED, DEFAULT_SEED + 1, DEFAULT_SEED + 2]
    deep_seeds = [DEFAULT_SEED + offset for offset in range(9)]
    by_arm = {arm: (deep_seeds if arm in DEEP_SEED_ARMS else seeds) for arm in ARMS}

    # Carried forward rather than overwritten. `run_spend_usd` is what THIS run
    # was billed, so an arm whose calls all replay reports $0 — which would erase
    # the live figures DR-314 quotes. `evidence_cost_usd` is the stable one and
    # is what the write-up should use; the old field is preserved so the record
    # stays traceable.
    previous: dict = {}
    if OUT.is_file():
        previous = (json.loads(OUT.read_text(encoding="utf-8")) or {}).get("arms") or {}

    findings: dict = {
        "cases": [case["name"] for case in cases],
        "seeds": seeds,
        "seeds_by_arm": by_arm,
        "arms": {},
    }
    schedule = [(name, seed) for name in ARMS for seed in by_arm[name]]
    for arm, seed in schedule:
        config = RunConfig(mode=Mode.RECORD, seed=seed)
        client = config.build_client()
        predictions: dict[str, dict[str, set[str]]] = {}
        shedding = []
        undecodable = 0
        tags: Counter[str] = Counter()
        survives = {"tag_only": 0, "tag_and_reason": 0, "freeform": 0}
        # Where a `reason` field exists, whether it was actually filled. For the
        # kills-only arm this is the whole measurement: the instruction to leave
        # a surviving pair's reason empty is stated in prose and enforced by
        # nothing, so an arm that writes one anyway saves nothing. Counted rather
        # than assumed, which is the #163 lesson.
        written = {
            "kills_with_reason": 0,
            "kills_empty": 0,
            "kills_absent": 0,
            "survives_with_reason": 0,
            "survives_empty": 0,
            "survives_absent": 0,
        }
        for case in cases:
            model, stage, instruction, allowed, defect_alias, test_alias = _arm_setup(arm, case)
            batch = partition([case["name"]], 1, key=lambda name: name)[0]
            raw = client.complete(
                assemble(_blocks(case, instruction, defect_alias, test_alias)),
                constrain(model, allowed),
                batch.request_partition(),
                parse_as=model,
                stage=stage,
            )
            predicted: dict[str, set[str]] = {}
            if arm == "listing":
                decoded: list = []
                for entry in raw.tests:
                    predicted[entry.test_id] = set(entry.catches)
            else:
                decoded, missed = _decode(raw, arm, defect_alias, test_alias)
                undecodable += missed
                for node, judgements in decoded:
                    predicted[node] = {judged.defect_id for judged in judgements if judged.fails}
                    for judged in judgements:
                        if arm not in REASON_ARMS:
                            continue
                        if not hasattr(judged, "reason"):
                            filled = "absent"
                        else:
                            filled = "with_reason" if judged.reason.strip() else "empty"
                        written[f"{'kills' if judged.fails else 'survives'}_{filled}"] += 1
                    if arm not in TAGGED_ARMS:
                        continue
                    for judged in judgements:
                        if judged.fails:
                            continue
                        relation, freeform = _relation_of(judged)
                        tags[relation] += 1
                        if relation != "OTHER" and not freeform:
                            survives["tag_only"] += 1
                        elif relation != "OTHER":
                            survives["tag_and_reason"] += 1
                        else:
                            survives["freeform"] += 1
            predictions[case["name"]] = predicted
            shedding.append(_unanswered(case, predicted, arm, decoded))

        usage = summarize(client.observed_calls)
        label = f"{arm}/seed={seed}"
        carried = previous.get(label) or {}
        entry = {
            **_score(cases, predictions),
            "arm": arm,
            "seed": seed,
            "unanswered_pairs": sum(row["unanswered"] for row in shedding),
            "shedding_detectable": arm != "listing",
            "undecodable_ids": undecodable,
            "cost_usd": usage.run_spend_usd or carried.get("cost_usd", 0.0),
            "evidence_cost_usd": usage.evidence_cost_usd,
            "prompt_tokens": sum(stage.prompt_tokens for stage in usage.stages),
            "completion_tokens": sum(stage.completion_tokens for stage in usage.stages),
            "completion_tokens_per_case": sum(stage.completion_tokens for stage in usage.stages)
            / len(cases),
            "predictions": {
                name: {node: sorted(caught) for node, caught in sorted(predicted.items())}
                for name, predicted in sorted(predictions.items())
            },
        }
        if sum(written.values()):
            survives_total = (
                written["survives_with_reason"]
                + written["survives_empty"]
                + written["survives_absent"]
            )
            entry["reason_usage"] = {
                **written,
                # Empty and absent together: both mean the judge wrote no prose
                # about a surviving pair, which is the behaviour the instruction
                # asked for. Which of the two it was is the arm's schema, not the
                # judge's compliance, and the counts above keep them apart.
                "survives_without_prose": (
                    ((written["survives_empty"] + written["survives_absent"]) / survives_total)
                    if survives_total
                    else None
                ),
            }
        if arm in TAGGED_ARMS:
            answered_survives = sum(survives.values())
            entry["tag_usage"] = {
                **survives,
                "survives_verdicts": answered_survives,
                "tag_share": (
                    (survives["tag_only"] / answered_survives) if answered_survives else None
                ),
                "tag_frequency": dict(sorted(tags.items())),
            }
        findings["arms"][label] = entry

    per_arm = {arm: [row for row in findings["arms"].values() if row["arm"] == arm] for arm in ARMS}
    means = {
        arm: sum(row["completion_tokens"] for row in rows) / len(rows)
        for arm, rows in per_arm.items()
    }
    findings["output_token_ratios"] = {
        arm: {
            "mean_completion_tokens": means[arm],
            "ratio_to_verdict": means[arm] / means["verdict"] if means["verdict"] else None,
            **_projection(means["reasoned"], means[arm]),
        }
        for arm in ARMS
    }
    findings["gate2_reference"] = {
        "pair_stage_output_tokens": GATE2_PAIR_OUTPUT_TOKENS,
        "pair_stage_output_usd": GATE2_PAIR_OUTPUT_USD,
        "run_usd": GATE2_RUN_USD,
        "output_usd_per_mtok": OUTPUT_USD_PER_MTOK,
    }

    OUT.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for label, figures in findings["arms"].items():
        print(
            f"{label:28s} recall={figures['recall']:.4f} precision={figures['precision']:.4f} "
            f"kills/defect={figures['kills_per_defect']:.3f} "
            f"unanswered={figures['unanswered_pairs']} "
            f"undecodable={figures['undecodable_ids']} "
            f"detectable={figures['shedding_detectable']} "
            f"cost=${figures['evidence_cost_usd']:.4f} out={figures['completion_tokens']}"
        )

    # The spread across seeds is the thing to read, not any single row: an arm
    # whose recall moves more between seeds than the arms differ from each other
    # has not been separated by this experiment.
    print()
    for arm in ARMS:
        rows = per_arm[arm]
        recalls = [row["recall"] for row in rows]
        guards = [row["kills_per_defect"] for row in rows]
        ratios = findings["output_token_ratios"][arm]
        print(
            f"{arm:13s} n={len(rows)} recall min={min(recalls):.4f} max={max(recalls):.4f} "
            f"mean={sum(recalls) / len(recalls):.4f}  "
            f"kills/defect {min(guards):.3f}-{max(guards):.3f}  "
            f"out mean={means[arm]:.0f} "
            f"(x{ratios['ratio_to_verdict']:.2f} verdict, "
            f"x{ratios['ratio_to_reasoned']:.2f} reasoned)"
        )

    # A minimum over nine draws is systematically lower than a minimum over
    # three, so `recall min` above is NOT comparable between arms drawn a
    # different number of times. These two figures are: the mean, and the share
    # of draws at or below the bar. Read those when comparing `verdict`,
    # `kills-only` and `union`, which is why all three were drawn nine times.
    print()
    bar = min(row["recall"] for row in per_arm["verdict"])
    print(f"bar = verdict's worst of {len(per_arm['verdict'])} draws = {bar:.4f}")
    for arm in DEEP_SEED_ARMS:
        rows = per_arm[arm]
        recalls = sorted(row["recall"] for row in rows)
        below = [value for value in recalls if value < bar]
        spread = max(recalls) - min(recalls)
        print(
            f"{arm:13s} n={len(recalls)} mean={sum(recalls) / len(recalls):.4f} "
            f"median={recalls[len(recalls) // 2]:.4f} spread={spread:.4f} "
            f"draws below the bar={len(below)}/{len(recalls)}"
        )

    print()
    for arm in ARMS:
        rows = [row for row in per_arm[arm] if "reason_usage" in row]
        if not rows:
            continue
        empty = [row["reason_usage"]["survives_without_prose"] for row in rows]
        killed = [row["reason_usage"]["kills_with_reason"] for row in rows]
        absent = sum(row["reason_usage"]["survives_absent"] for row in rows)
        print(
            f"{arm:13s} survives without prose min={min(empty):.3f} max={max(empty):.3f}  "
            f"(field absent on {absent})  kills carrying a reason={killed}"
        )

    print()
    for arm in TAGGED_ARMS:
        shares = [row["tag_usage"]["tag_share"] for row in per_arm[arm]]
        pooled: Counter[str] = Counter()
        for row in per_arm[arm]:
            pooled.update(row["tag_usage"]["tag_frequency"])
        print(
            f"{arm:13s} tag share min={min(shares):.3f} max={max(shares):.3f}  "
            f"tags={dict(pooled.most_common())}"
        )

    print()
    for arm in ARMS:
        projected = findings["output_token_ratios"][arm]
        print(
            f"{arm:13s} projected on Gate 2: "
            f"{projected['projected_output_tokens']:.0f} output tokens, "
            f"saves ${projected['saved_usd']:.2f} of the pair stage's "
            f"${GATE2_PAIR_OUTPUT_USD:.2f}"
        )
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
