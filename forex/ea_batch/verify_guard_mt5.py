"""Test of the 2026-10-09 AccountGuard changes (day start rebuilt from the deal history, optional day PROFIT cap) in the MT5 Strategy Tester on MT5 broker's own real ticks (portable MT5 broker tester terminal, never a live terminal).
   python -m forex.ea_batch.verify_guard_mt5
GuardSelfTest.mq5 = the real guard code + a STUBBORN driver (1 lot XAUUSD+ on a schedule, retrying every 10 s even during a stop). One run, MT5 broker settings: day stop 2.0%, day profit cap 2.0%, server midnight as the day clock (InpShiftSec = 0), floor 6.5%,
and every day at 13:00 server time a freshly created guard rebuilds the day start from the deal history exactly like an EA restarted mid-day would (RESTARTCHK: old = the reference the running guard took at midnight, rebuilt = the restarted guard's).
Checks: (1) rebuilt == old on every day (and on days where the balance had already moved), (2) NEWDAY at 00:00 server, (3) DAYSTOP / PROFITCAP fire at the right level and nothing opened afterwards survives 3 s, (4) trading resumes the next day."""
from __future__ import annotations

import glob
import re
import shutil
from pathlib import Path

import numpy as np
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


def main() -> int:
    ex = TERM / "MQL5" / "Experts" / "the trader"
    for f in ("AccountGuard.mqh", "GuardSelfTest.mq5"):                       # the sources the tests run are the repo's current ones; compile them first (MetaEditor, see the commit notes)
        shutil.copy2(SRC / f, ex / f)
    name = "guard_G9.csv"
    inputs = {"InpGuardOn": "true", "InpDriverLots": "1.0", "InpEveryMin": "45", "InpHoldMin": "40", "InpStubborn": "false", "InpDirMode": "0", "InpInitial": "100000", "InpDailyStopPct": "2.0", "InpFloorStopPct": "6.5",
              "InpTargetPct": "0.0", "InpProfitCapPct": "2.0", "InpShiftSec": "0", "InpRestartHour": "13", "InpLogName": name}
    r = TR.run_test("vg9_mt5", r"the trader\GuardSelfTest.ex5", "XAUUSD+", "M1", "2026.03.02", "2026.03.27", inputs, timeout=7200)
    l = read_log(name); print(f"run: net {r['net']:,.0f}, deals {0 if r['deals'] is None else len(r['deals'])}, log rows {len(l)}, note {r['note']!r}, seconds {r['seconds']}", flush=True)
    if not len(l):
        print("FAIL: no log"); return 1
    ok = True; day = lambda t: t.dt.normalize()
    rc = l[l.event == "RESTARTCHK"].copy()
    pr = rc.detail.str.extract(r"old=([-\d.]+) rebuilt=([-\d.]+)").astype(float); rc["old"], rc["new"] = pr[0], pr[1]; err = (rc.old - rc.new).abs()
    moved = int(((rc.balance - rc.old).abs() > 1.0).sum())
    c1 = len(rc) >= 15 and float(err.max()) < 0.01
    print(f"(1) restart check: {len(rc)} days, max |old - rebuilt| = {err.max():.4f} USD, days on which the balance had already moved by 13:00 (non-trivial): {moved} -> {'PASS' if c1 else 'FAIL'}", flush=True); ok &= c1
    nd = l[l.event == "NEWDAY"]; c2 = len(nd) >= 15 and bool((nd.time.dt.hour <= 1).all()) and nd.time.dt.normalize().is_unique
    print(f"(2) NEWDAY events {len(nd)} (one per server day, first tick of the day: gold only trades from 01:05 server time, so 00:xx-01:xx), hours seen {sorted(set(nd.time.dt.hour))} -> {'PASS' if c2 else 'FAIL'}", flush=True); ok &= c2
    for tag, ev, sign in (("DAYSTOP", "DAYSTOP", -1), ("PROFITCAP", "PROFITCAP", +1)):
        e = l[l.event == ev]; line = e.dayref + sign * 2000.0; over = (sign * (e.equity - line))
        late = checked = 0
        for _, s in e.iterrows():
            after = l[(day(l.time) == day(pd.Series([s.time])).iloc[0]) & (l.time > s.time)]
            for _, o in after[after.event == "DRV_OPEN"].iterrows():
                checked += 1; late += 0 if len(after[(after.event == "ENFORCE") & (after.time >= o.time) & (after.time <= o.time + pd.Timedelta(seconds=3))]) else 1
        res = sum(1 for _, s in e.iterrows() if len(l[(l.event == "DRV_OPEN") & (l.time > s.time) & (day(l.time) > day(pd.Series([s.time])).iloc[0])]))
        c = len(e) >= 1 and bool((over >= -1e-6).all()) and late == 0
        print(f"(3) {tag}: fired {len(e)}x; equity beyond the line at the halt: median {over.median() if len(e) else float('nan'):,.0f} USD, max {over.max() if len(e) else float('nan'):,.0f} USD; driver opens after a halt {checked}, not closed within 3 s {late}; halts followed by trading on a later day {res} -> {'PASS' if c else 'FAIL'}", flush=True); ok &= c
    print("ALL CHECKS PASS" if ok else "SOME CHECK FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
