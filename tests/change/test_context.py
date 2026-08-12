"""M2.2 acceptance: for a changed function, its definition and at least its
in-repo callers are retrieved; retrieval respects the configured budget cap."""

from pathlib import Path

from acceptance.change.context import RetrievalBudget, retrieve_context
from acceptance.review_state import ChangeSet, DiffHunk, FileChange


def _hunk(new_start: int, new_lines: int) -> DiffHunk:
    return DiffHunk(
        header=f"@@ -{new_start},{new_lines} +{new_start},{new_lines} @@",
        old_start=new_start,
        old_lines=new_lines,
        new_start=new_start,
        new_lines=new_lines,
        content="",
    )


def _change_set(*files: FileChange) -> ChangeSet:
    return ChangeSet(base_revision="base", head_revision="head", files=list(files))


def _source_change(
    path: str, new_start: int, new_lines: int, status: str = "modified"
) -> FileChange:
    return FileChange(
        path=path,
        status=status,
        category="source",
        hunks=[_hunk(new_start, new_lines)],
    )


def _write(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(content)


MOD = """\
def helper():
    return 1


def target():
    return helper() + 1
"""

CALLER = """\
from mod import target


def use_it():
    return target() + target()
"""


def test_changed_function_definition_and_callers_are_retrieved(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", MOD)
    _write(repo, "caller.py", CALLER)
    # The hunk lands on `target` (lines 5-6).
    change_set = _change_set(_source_change("mod.py", new_start=5, new_lines=2))

    result = retrieve_context(repo, change_set)

    assert len(result.contexts) == 1
    context = result.contexts[0]
    assert context.definition.qualname == "target"
    assert context.definition.kind == "function"
    assert context.definition.file == "mod.py"
    assert "def target():" in context.definition.source

    # At least the in-repo callers are retrieved (two calls in caller.py).
    caller_files = {c.file for c in context.call_sites}
    assert "caller.py" in caller_files
    assert len(context.call_sites) == 2
    assert all(c.in_definition == "use_it" for c in context.call_sites)


def test_innermost_enclosing_definition_is_a_method(tmp_path):
    repo = tmp_path
    _write(
        repo,
        "svc.py",
        "class Service:\n"
        "    def start(self):\n"
        "        return self.run()\n"
        "\n"
        "    def run(self):\n"
        "        return 42\n",
    )
    _write(
        repo, "client.py", "from svc import Service\n\n\ndef go():\n    return Service().run()\n"
    )
    # Change lands on Service.run (lines 5-6).
    change_set = _change_set(_source_change("svc.py", new_start=5, new_lines=2))

    result = retrieve_context(repo, change_set)

    context = result.contexts[0]
    assert context.definition.qualname == "Service.run"
    assert context.definition.kind == "method"
    # `Service().run()` is a name-based caller match.
    assert any(c.file == "client.py" and c.in_definition == "go" for c in context.call_sites)


def test_call_site_budget_cap_is_respected_and_flagged(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", MOD)
    _write(repo, "caller.py", CALLER)  # two target() calls
    change_set = _change_set(_source_change("mod.py", new_start=5, new_lines=2))

    result = retrieve_context(repo, change_set, RetrievalBudget(max_call_sites_per_definition=1))

    context = result.contexts[0]
    assert len(context.call_sites) == 1  # capped
    assert context.call_sites_truncated is True


def test_files_scanned_budget_cap_is_respected_and_flagged(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", MOD)
    _write(repo, "caller.py", CALLER)
    _write(repo, "zzz_other.py", "x = 1\n")  # 3 py files total
    change_set = _change_set(_source_change("mod.py", new_start=5, new_lines=2))

    result = retrieve_context(repo, change_set, RetrievalBudget(max_files_scanned=1))

    assert result.files_scanned == 1
    assert result.files_scanned_truncated is True


def test_vendored_directories_are_not_scanned_for_callers(tmp_path):
    repo = tmp_path
    _write(repo, "mod.py", MOD)
    # A caller that lives under .venv must not be scanned (not an in-repo caller).
    (repo / ".venv").mkdir()
    (repo / ".venv" / "vendored.py").write_text("from mod import target\ntarget()\n")
    change_set = _change_set(_source_change("mod.py", new_start=5, new_lines=2))

    result = retrieve_context(repo, change_set)

    context = result.contexts[0]
    assert all(".venv" not in c.file for c in context.call_sites)


def test_deleted_files_are_skipped(tmp_path):
    repo = tmp_path
    _write(repo, "caller.py", CALLER)
    change_set = _change_set(_source_change("mod.py", new_start=5, new_lines=2, status="deleted"))

    result = retrieve_context(repo, change_set)

    assert result.contexts == []


def test_non_source_files_are_skipped(tmp_path):
    repo = tmp_path
    _write(repo, "requirements.txt", "requests==2.0\n")
    change_set = _change_set(
        FileChange(
            path="requirements.txt",
            status="modified",
            category="config",
            hunks=[_hunk(1, 1)],
        )
    )

    result = retrieve_context(repo, change_set)
    assert result.contexts == []


def test_result_round_trips_through_persistence(tmp_path):
    from acceptance.change.context import RetrievalResult

    repo = tmp_path
    _write(repo, "mod.py", MOD)
    _write(repo, "caller.py", CALLER)
    change_set = _change_set(_source_change("mod.py", new_start=5, new_lines=2))

    result = retrieve_context(repo, change_set)
    assert RetrievalResult.from_dict(result.to_dict()) == result
