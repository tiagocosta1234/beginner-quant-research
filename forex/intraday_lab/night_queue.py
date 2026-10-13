"""Overnight queue of pre-registered lab iterations, one after another; log D:\\finance\\scratch\\lab_night.log.   python -m forex.intraday_lab.night_queue"""
import datetime as dt
import os
import subprocess
import sys

LOG = r"D:\finance\scratch\lab_night.log"
JOBS = ["forex.intraday_lab.iter20_sdb_filters"]


def log(s):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {s}\n")


for j in JOBS:
    log(f"START {j}")
    r = subprocess.run([sys.executable, "-m", j], capture_output=True, text=True, cwd=r"D:\finance\beginner-quant-research", env={**os.environ, "PYTHONPATH": r"D:\finance\beginner-quant-research"})
    log(f"END {j} exit {r.returncode}\n{r.stdout[-6000:]}\n{r.stderr[-2000:]}")
log("QUEUE DONE")
