"""Unattended orchestrator (the trader: "run everything, dont cut anything", resume tomorrow with the keyword LOCKIN).
Runs, one after another, every resumable EA job on the shared MT5 terminal, retrying a step until it reports nothing left, and writes timestamps to D:\finance\scratch\overnight_status.log:
  1. fx_confirm        out-of-time check of the top 3 FX EAs (2022-2025)
  2. multi_symbol      multi-symbol edge screen (136 EAs x basket symbols, 704 runs)
  3. run_batch         the rest of the single-symbol 2026 real-tick screen (about 615 EAs)
Detached: started with Start-Process so it outlives the chat session.  python -m forex.ea_batch.overnight
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG = Path(r"D:\finance\scratch\overnight_status.log")
ROOT = Path(r"D:\finance\beginner-quant-research")
EA_ROOT = "D:/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/ea_batch"
STEPS = [("fx_confirm", ["-m", "forex.ea_batch.fx_confirm"]), ("multi_symbol", ["-m", "forex.ea_batch.multi_symbol"]), ("run_batch", ["-m", "forex.ea_batch.run_batch", "--ea-root", EA_ROOT])]


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def main():
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8", TEMP=r"D:\finance\tmp", TMP=r"D:\finance\tmp")
    log("orchestrator started")
    for name, args in STEPS:
        for attempt in range(1, 6):
            out = Path(rf"D:\finance\scratch\overnight_{name}_{attempt}.log")
            log(f"{name}: attempt {attempt} start")
            with open(out, "w", encoding="utf-8") as fh:
                rc = subprocess.run([sys.executable, "-u", *args], cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT).returncode
            log(f"{name}: attempt {attempt} exit code {rc}")
            if rc == 0:
                break
            time.sleep(60)
        log(f"{name}: finished")
    log("ALL STEPS FINISHED")
    Path(r"D:\finance\scratch\overnight_done.txt").write_text(f"done {datetime.now()}\n")


if __name__ == "__main__":
    main()
