"""Run every live bot test file and report one line each. Exit code 1 if any file fails.

Run from the futures/ folder:  python live_bot/tests/run_all.py
Most test files are plain scripts with their own main(); test_pnl_tracker.py uses pytest."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # the futures/ folder, so `live_bot` is importable
PYTEST_FILES = {"test_pnl_tracker.py"}


def main() -> int:
    env = dict(os.environ, PYTHONPATH=str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    failed = []
    for path in sorted(HERE.glob("test_*.py")):
        if path.name in PYTEST_FILES:
            cmd = [sys.executable, "-m", "pytest", "-q", str(path)]
        else:
            cmd = [sys.executable, str(path)]
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        last = (proc.stdout.strip().splitlines() or [""])[-1]
        status = "ok  " if proc.returncode == 0 else "FAIL"
        print(f"{status} {path.name:48s} {last[:80]}")
        if proc.returncode != 0:
            failed.append(path.name)
            print(proc.stdout[-1500:], proc.stderr[-1500:], sep="\n")
    print(f"\n{len(failed)} failed" if failed else "\nall test files passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
