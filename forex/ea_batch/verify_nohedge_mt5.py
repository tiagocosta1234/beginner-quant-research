"""Test of the 2026-10-10 NO-HEDGE rule of AccountGuard (MT5 broker prohibits opposite positions on the same asset) in the MT5 Strategy Tester on MT5 broker's real ticks (portable MT5 broker tester terminal, never a live terminal).
   python -m forex.ea_batch.verify_nohedge_mt5
GuardSelfTest.mq5 = the real guard code + a driver that opens 1 lot of XAUUSD+ every 45 minutes (random side, closed after 40 minutes) and, with InpOppositeDriver, opens a position of the OPPOSITE side 300 seconds after the first one.
Run A (rule ON): every opposite position must be closed by the guard within 3 s (NOHEDGE events about as many as OPP_OPEN events) and no one-minute snapshot may show both sides open. Run B (rule OFF, control): the same driver must produce snapshots with both sides open (so the test can detect hedges at all)."""
from __future__ import annotations

import glob
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from forex.ea_batch import mt5data_run as ER

TR, TERM = ER.TR, ER.TERM_DIR
COLS = ["time", "event", "equity", "balance", "dayref", "positions", "detail"]
SRC = Path(r"D:\finance\beginner-quant-research\mt5\expert_advisors")


def read_log(name: str) -> pd.DataFrame:
    files = glob.glob(str(TERM / "Tester" / "Agent-*" / "MQL5" / "Files" / name))
    if not files:
        return pd.DataFrame(columns=COLS)
    f = max(files, key=lambda p: Path(p).stat().st_mtime); d = pd.read_csv(f, header=None, names=COLS, on_bad_lines="skip")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce"); return d.dropna(subset=["time"])


def compile_sources() -> None:
    ex = TERM / "MQL5" / "Experts" / "the trader"; ex.mkdir(parents=True, exist_ok=True)
    for f in ("AccountGuard.mqh", "GuardSelfTest.mq5"):
        shutil.copy2(SRC / f, ex / f)
    log = Path(r"D:\finance\tmp") / "nohedge_compile.log"; log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(TERM / "MetaEditor64.exe"), "/portable", f"/compile:{ex / 'GuardSelfTest.mq5'}", f"/log:{log}"], timeout=120)
    res = [l for l in log.read_bytes().decode("utf-16", errors="ignore").splitlines() if l.startswith("Result")]
    print("compile in the tester terminal:", res[-1] if res else "no result line", flush=True)
    if not res or " 0 errors" not in res[-1]:
        raise SystemExit("compile failed")


def run(tag: str, nohedge: bool, name: str) -> pd.DataFrame:
    inputs = {"InpGuardOn": "true", "InpDriverLots": "1.0", "InpEveryMin": "45", "InpHoldMin": "40", "InpStubborn": "false", "InpDirMode": "0", "InpInitial": "100000", "InpDailyStopPct": "4.0", "InpFloorStopPct": "9.0",
              "InpTargetPct": "0.0", "InpShiftSec": "0", "InpNoHedge": "true" if nohedge else "false", "InpOppositeDriver": "true", "InpLogName": name}
    r = TR.run_test(tag, r"the trader\GuardSelfTest.ex5", "XAUUSD+", "M1", "2026.03.02", "2026.03.27", inputs, timeout=7200)
    l = read_log(name); print(f"{tag}: net {r['net']:,.0f}, log rows {len(l)}, note {r['note']!r}, seconds {r['seconds']}, events {l.event.value_counts().to_dict() if len(l) else {}}", flush=True)
    return l


def mixed(l: pd.DataFrame) -> int:
    s = l[l.event == "SNAP"].detail.str.extract(r"b=(\d+) s=(\d+)").astype(float); return int(((s[0] > 0) & (s[1] > 0)).sum())


def main() -> int:
    compile_sources(); ok = True
    a = run("nohedge_A", True, "nohedge_A.csv"); b = run("nohedge_B", False, "nohedge_B.csv")
    oa, na, ma = int((a.event == "OPP_OPEN").sum()), int(a.detail.str.extract(r"closed=(\d+)")[0].astype(float).sum()) if len(a) else 0, mixed(a)
    ob, nb, mb = int((b.event == "OPP_OPEN").sum()), int((b.event == "NOHEDGE").sum()), mixed(b)
    c1 = oa >= 10 and na >= 0.9 * oa and ma == 0
    print(f"A (rule ON): opposite positions opened {oa}, closed by the guard {na}, one-minute snapshots with BOTH sides open {ma} -> {'PASS' if c1 else 'FAIL'}", flush=True); ok &= c1
    c2 = ob >= 10 and nb == 0 and mb > 0
    print(f"B (rule OFF, control): opposite positions opened {ob}, NOHEDGE events {nb}, snapshots with both sides open {mb} -> {'PASS (the test can see hedges)' if c2 else 'FAIL'}", flush=True); ok &= c2
    print("ALL CHECKS PASS" if ok else "SOME CHECK FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
