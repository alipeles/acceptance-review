"""Write a .env file from the process environment, API keys only.

Cloud sessions receive provider keys as environment variables; the tool reads
them from .env. This copies every variable whose name ends in _API_KEY into
.env in the current directory, and nothing else. It never prints a value.
"""

import os
import sys
from pathlib import Path

target = Path(".env")
if target.exists():
    print(".env already exists; leaving it alone")
    sys.exit(0)

keys = sorted(k for k in os.environ if k.endswith("_API_KEY"))
if not keys:
    print("no *_API_KEY variables in the environment; nothing written")
    sys.exit(1)

target.write_text("".join(f"{k}={os.environ[k]}\n" for k in keys))
print(f"wrote .env with {len(keys)} key(s): {', '.join(keys)}")
