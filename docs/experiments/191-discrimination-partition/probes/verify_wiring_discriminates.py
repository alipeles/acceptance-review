"""Make the enumeration prompt sensitive to test files, run the test, restore.

The claim under test is that adding a test cannot move an obligation's
enumerated defects. The way that claim fails is for something test-shaped to
reach the enumeration request, so this injects exactly that — the render stops
filtering the diff down to source files — and asserts the test goes red.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
src = ROOT / "src/acceptance/evidence/discrimination.py"

good = src.read_text()
filter_line = '        if file_change.category != "source":\n            continue\n'
assert good.count(filter_line) == 1

try:
    src.write_text(good.replace(filter_line, "        pass\n"))
    result = subprocess.run(
        [".venv/bin/pytest", "tests/test_discrimination_wiring.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(result.stdout[-900:])
    print("EXIT", result.returncode, "(non-zero = the test discriminates)")
finally:
    src.write_text(good)
    print("restored:", src.read_text() == good)
