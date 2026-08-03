"""Request partitioning (DR-164).

The mechanism is generic, so these are its properties independent of any stage:
batches cover the input exactly once, composition is a pure function of the
input, and the descriptor folded into the request key carries the run control
without carrying the batch's position.
"""

import pytest

from acceptance.partition import Batch, partition


def _ids(batches: list[Batch]) -> list[list[str]]:
    return [list(batch.items) for batch in batches]


def test_batches_cover_every_item_exactly_once():
    items = [f"t{n:02d}" for n in range(10)]

    batches = partition(items, 4, key=str)

    assert _ids(batches) == [
        ["t00", "t01", "t02", "t03"],
        ["t04", "t05", "t06", "t07"],
        ["t08", "t09"],
    ]
    assert [item for batch in batches for item in batch.items] == items


def test_batch_composition_is_independent_of_input_order():
    """Batches must be a pure function of the input: if the order tests arrive
    in could change the batches, request keys churn between runs and replay
    misses even though nothing about the review changed."""
    items = ["c", "a", "e", "b", "d"]

    forward = partition(items, 2, key=str)
    shuffled = partition(list(reversed(items)), 2, key=str)

    assert _ids(forward) == [["a", "b"], ["c", "d"], ["e"]]
    assert _ids(shuffled) == _ids(forward)


def test_every_batch_reports_the_configured_size_not_its_own_length():
    """The last batch is short, but the control in force is still the
    configured size — provenance would otherwise report a size no call ran
    under whenever the input divided unevenly."""
    batches = partition(["a", "b", "c"], 2, key=str)

    assert [len(batch.items) for batch in batches] == [2, 1]
    assert [batch.size for batch in batches] == [2, 2]
    assert [batch.index for batch in batches] == [0, 1]
    assert {batch.count for batch in batches} == {2}


def test_request_partition_carries_size_only():
    """`size` is in the request hash because it is a run control. `index` and
    `count` are deliberately out: the messages already differ per batch, and
    hashing `count` would invalidate an unchanged early batch's transcript every
    time an item was appended."""
    batches = partition(["a", "b", "c"], 2, key=str)

    assert batches[0].request_partition() == {"size": 2}
    assert batches[1].request_partition() == {"size": 2}


def test_changing_the_size_changes_the_descriptor_even_when_batches_match():
    """Two sizes can yield identical batches when the input is smaller than
    both. The descriptor must still differ, or changing the control would leave
    recorded transcripts replaying as if nothing had changed."""
    small = partition(["a"], 4, key=str)
    large = partition(["a"], 8, key=str)

    assert _ids(small) == _ids(large)
    assert small[0].request_partition() != large[0].request_partition()


def test_no_items_yields_no_batches():
    assert partition([], 4, key=str) == []


def test_a_size_below_one_is_rejected():
    with pytest.raises(ValueError, match="at least 1"):
        partition(["a"], 0, key=str)


def test_the_mechanism_works_on_a_payload_that_has_nothing_to_do_with_mapping():
    """Reusability is the obligation, so exercise it on a shape the mapping
    stage would never produce. A partitioner that had grown mapping-specific
    assumptions — a `test_id` attribute, an obligation list — could not run this
    at all, and the next stage to need batching would have to reimplement it."""
    changed_files = [
        {"path": "src/b.py", "hunks": 3},
        {"path": "src/a.py", "hunks": 1},
        {"path": "src/c.py", "hunks": 7},
    ]

    batches = partition(changed_files, 2, key=lambda f: f["path"])

    assert [[f["path"] for f in b.items] for b in batches] == [
        ["src/a.py", "src/b.py"],
        ["src/c.py"],
    ]
    assert batches[0].request_partition() == {"size": 2}


def test_the_mechanism_does_not_depend_on_the_stage_that_uses_it():
    """The one caller today is mapping (DR-164 decision 2). The module must not
    import it back: a partitioner that reaches into `evidence/` is reusable only
    in name, and the coupling would not show up in any behavioural test."""
    import ast
    import pathlib

    import acceptance.partition as module

    tree = ast.parse(pathlib.Path(module.__file__).read_text())
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert not [name for name in imported if name.startswith("acceptance.")]


def test_a_batch_is_immutable():
    batch = partition(["a", "b"], 2, key=str)[0]

    with pytest.raises(Exception):
        batch.size = 99
