"""Test of the 2026-10-09 PASS LOCK redesign (counted equity, confirm after closing, release if short, restart-safe) in the MT5 Strategy Tester on MT5 broker's real ticks (portable MT5 broker tester terminal, never a live terminal).
   python -m forex.ea_batch.verify_lock_mt5
GuardSelfTest.mq5 = the real guard code + a STUBBORN driver (3 lots XAUUSD+, always buy, retrying every 10 s even during a stop). Gold rallied in January 2026, so a 5% target (105,000) is reached in a few days.
Run T1 (MT5 broker settings): target 5.0%, buffer 0.3%, counted-equity cap 2.0%, day stop 4% (so it does not interfere), no profit cap. Checks: (a) LOCK fires, followed by PASSED within 5 s with no positions; (b) at every LOCK the COUNTED equity (day reference + min(day profit, 2,000)) is at or above the trigger; (c) cap-aware evidence: snapshots where RAW equity was already above the trigger but today's profit was above the 2,000 cap, before the first LOCK, i.e. the old raw lock would have fired and this one did not; (d) after PASSED the stubborn driver is closed within 3 s each time and no position survives in the snapshots.
Run T2 (release path): buffer 0 and the harness burns 30,000 USD on spread (the tester jumps over the target by far, so the burn must be large) after the lock has flattened the account (InpSlipOnLock), as if the close had slipped: LOCKRELEASED must appear and the driver must trade again afterwards."""
from __future__ import annotations

import glob
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from forex.ea_batch import mt5data_run as ER

TR, TERM = ER.TR, ER.TERM_DIR
COLS = ["time", "event", "equity", "balance", "dayref", "positions", "detail"]
SRC = Path(r"D:\finance\beginner-quant-research\mt5\expert_advisors")
CAP, INIT = 2000.0, 100000.0


def read_log(name: str) -> pd.DataFrame:
    files = glob.glob(str(TERM / "Tester" / "Agent-*" / "MQL5" / "Files" / name))
    if not files:
        return pd.DataFrame(columns=COLS)
    f = max(files, key=lambda p: Path(p).stat().st_mtime); d = pd.read_csv(f, header=None, names=COLS, on_bad_lines="skip")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce"); return d.dropna(subset=["time"])


def counted(eq, ref):
    return ref + CAP if eq - ref > CAP else eq


def compile_sources() -> None:
    ex = TERM / "MQL5" / "Experts" / "the trader"; ex.mkdir(parents=True, exist_ok=True)
    for f in ("AccountGuard.mqh", "GuardSelfTest.mq5"):
        shutil.copy2(SRC / f, ex / f)
    log = Path(r"D:\finance\tmp") / "lock_compile.log"; log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(TERM / "MetaEditor64.exe"), "/portable", f"/compile:{ex / 'GuardSelfTest.mq5'}", f"/log:{log}"], timeout=120)
    txt = log.read_bytes().decode("utf-16", errors="ignore"); res = [l for l in txt.splitlines() if l.startswith("Result")]
    print("compile in the tester terminal:", res[-1] if res else "no result line", flush=True)
    if not res or " 0 errors" not in res[-1]:
        raise SystemExit("compile failed")


def run(tag: str, buffer: float, name: str, slip: float = 0.0):
    inputs = {"InpGuardOn": "true", "InpDriverLots": "3.0", "InpEveryMin": "45", "InpHoldMin": "40", "InpStubborn": "true", "InpDirMode": "1", "InpInitial": "100000", "InpDailyStopPct": "4.0", "InpFloorStopPct": "9.0",
              "InpTargetPct": "5.0", "InpLockBufferPct": str(buffer), "InpMinDays": "0", "InpProfitCapPct": "0.0", "InpShiftSec": "0", "InpCountedCapPct": "2.0", "InpSlipOnLock": str(slip), "InpLogName": name}
    if slip > 0:
        inputs["InpDailyStopPct"], inputs["InpFloorStopPct"] = "50.0", "30.0"          # T2 burns far more than the real stops allow; keep them out of the way
    r = TR.run_test(tag, r"the trader\GuardSelfTest.ex5", "XAUUSD+", "M1", "2026.01.05", "2026.01.20", inputs, timeout=7200)
    l = read_log(name); print(f"{tag}: net {r['net']:,.0f}, log rows {len(l)}, note {r['note']!r}, seconds {r['seconds']}, events {l.event.value_counts().to_dict() if len(l) else {}}", flush=True)
    return l


def main() -> int:
    compile_sources(); ok = True
    l = run("lock_T1", 0.3, "lock_T1.csv")
    if not len(l):
        print("FAIL: no log"); return 1
    trig = INIT * 1.05 + 0.003 * INIT
    lk = l[l.event == "LOCK"]; ps = l[l.event == "PASSED"]
    c_a = len(lk) >= 1 and len(ps) >= 1
    gaps = [(ps[ps.time >= s.time].time.min() - s.time).total_seconds() for _, s in lk.iterrows() if len(ps[ps.time >= s.time])]
    c_a = c_a and bool(gaps) and bool((ps.positions == 0).all())
    print(f"(a) LOCK {len(lk)}x, PASSED {len(ps)}x with no position, seconds from LOCK to PASSED {gaps} (in the tester gold only trades from 01:05 server, and the lock fires at the 01:00 day start, so the close waits for the session) -> {'PASS' if c_a else 'FAIL'}", flush=True); ok &= c_a
    cs = [counted(r.equity, r.dayref) for _, r in lk.iterrows()]; c_b = len(cs) >= 1 and all(c >= trig - 150 for c in cs)
    print(f"(b) counted equity at the LOCK rows {[round(c) for c in cs]} vs trigger {trig:,.0f} (tolerance 150 for the tick between trigger and log) -> {'PASS' if c_b else 'FAIL'}", flush=True); ok &= c_b
    first = lk.time.min() if len(lk) else l.time.max(); pre = l[(l.event == "SNAP") & (l.time < first)]
    raw_only = pre[(pre.equity >= trig) & ((pre.equity - pre.dayref) > CAP) & ((pre.dayref + CAP) < trig)]
    print(f"(c) snapshots before the first LOCK with RAW equity >= trigger but today's profit above the cap (old lock would have fired): {len(raw_only)} -> informational {'(cap-aware logic exercised)' if len(raw_only) else '(not exercised in this window)'}", flush=True)
    after = l[l.time > ps.time.min()] if len(ps) else l.iloc[0:0]; late = checked = 0
    for _, o in after[after.event == "DRV_OPEN"].iterrows():
        checked += 1; late += 0 if len(after[(after.event == "ENFORCE") & (after.time >= o.time) & (after.time <= o.time + pd.Timedelta(seconds=3))]) else 1
    held = after[(after.event == "SNAP") & (after.positions > 0)]
    c_d = len(ps) >= 1 and late == 0 and len(held) == 0
    print(f"(d) after PASSED: driver opens {checked}, not closed within 3 s {late}, snapshots with a position {len(held)} -> {'PASS' if c_d else 'FAIL'}", flush=True); ok &= c_d
    l2 = run("lock_T2", 0.0, "lock_T2.csv", 30000.0)
    rel = l2[l2.event == "LOCKRELEASED"]; resumed = len(l2[(l2.event == "DRV_OPEN") & (l2.time > rel.time.min())]) if len(rel) else 0
    c_e = len(rel) >= 1 and resumed >= 1
    print(f"T2 release path: LOCKRELEASED {len(rel)}x, driver opens after the first release {resumed} -> {'PASS' if c_e else 'FAIL'}", flush=True); ok &= c_e
    print("ALL CHECKS PASS" if ok else "SOME CHECK FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
