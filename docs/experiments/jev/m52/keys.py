"""Read a provider key from the worktree's env file, without printing it.

The harness reads keys from the process environment; the experiment also
accepts them from the repo-root env file so a key added there needs no shell
restart. The environment wins when both are set.
"""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILE = _ROOT / ".env"


def key(name: str) -> str:
    """Return the value of ``name``, or raise if it is not set anywhere."""
    if os.environ.get(name):
        return os.environ[name]
    if _ENV_FILE.is_file():
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            line = line.removeprefix("export ")
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip("'\"")
    raise KeyError(f"{name} is not set in the environment or the repo env file")


if __name__ == "__main__":
    import sys

    for n in sys.argv[1:]:
        try:
            print(f"{n}: present ({len(key(n))} chars)")
        except KeyError:
            print(f"{n}: missing")
