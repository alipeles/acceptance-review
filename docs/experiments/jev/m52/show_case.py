"""Print one tuning case's fields, for designing prompts. Never a held-out case.

Run:  .venv/bin/python docs/experiments/jev/m52/show_case.py [index]
"""

from __future__ import annotations

import sys

from split import cases, load_split


def main() -> int:
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    tuning = set(load_split()["tuning"])
    case = [c for c in cases() if c.case_id in tuning][index]
    for name, value in case.model_dump().items():
        print(f"--- {name}")
        print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
