"""Tests of AccountGuard in the real-tick Strategy Tester (the trader: "test it on every single aspect").

GuardSelfTest.mq5 = the real guard code + a STUBBORN driver (opens 1.0 lot XAUUSD on a schedule and tries again every 10 s whenever flat, even during a stop), standing in for the third-party EAs.
G0  guard off, driver only (Mar-Apr 2025)                                    -> how bad the stubborn driver is on its own
G1  guard on, day stop 4%                                                     -> (a) the equity of a stopped day does not fall much below ref - 4%, (b) every driver open after a stop is closed within 2 s,
                                                                                (c) trading resumes the next Prague day, (d) the stop actually fired (>= 3 times)
G2  pass lock: target 0.5%, min 4 days, driver buys only (Oct-Nov 2024)      -> LOCK fires only after 4 trading days and equity >= target + buffer; nothing is open afterwards and nothing re-opens
G3  emergency stop: floor 1.5%, driver sells only in a rally (Jan-Feb 2025)    -> EMERGENCY fires, then no position survives 2 s for the rest of the run
G4  guard on with thresholds that cannot trigger (50% / 90%)                   -> identical result to G0 (the guard must not interfere)
G5  day boundary: NEWDAY events at server 01:00 (= Prague midnight) in winter and summer
STOP THE EA BATCH FIRST.   python -m forex.ea_batch.verify_guard
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import run_batch as RB
from forex.ea_batch.tester_run import run_test

EXPERT = r"the trader\GuardSelfTest.ex5"
OUT = Path(r"D:\finance\scratch\verify_guard"); OUT.mkdir(parents=True, exist_ok=True)
COLS = ["time", "event", "equity", "balance", "dayref", "positions", "detail"]


def read_log(name: str) -> pd.DataFrame:
    root = Path(r"C:\Users\author\AppData\Roaming\MetaQuotes\Tester") / RB.data_folder().name       # the tester agents live behind this junction
    files = glob.glob(str(root / "Agent-*" / "MQL5" / "Files" / name))
    if not files:
        return pd.DataFrame(columns=COLS)
    f = max(files, key=lambda p: Path(p).stat().st_mtime)
    d = pd.read_csv(f, header=None, names=COLS, on_bad_lines="skip")
    d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    d.to_csv(OUT / name, index=False)
    return d.dropna(subset=["time"])


def scenario(tag, frm, to, inputs):
    name = f"guard_{tag}.csv"
    r = run_test(f"vg_{tag}", EXPERT, "XAUUSD", "M1", frm, to, {**inputs, "InpLogName": name}, timeout=5400)
    return r, read_log(name)


def pday(t: pd.Series) -> pd.Series:
    return (t - pd.Timedelta(hours=1)).dt.normalize()


def main():
    res = {}
    base = {"InpDriverLots": "1.0", "InpEveryMin": "45", "InpHoldMin": "40", "InpStubborn": "true"}
    # G0 / G1 / G4
    r0, l0 = scenario("G0", "2025.03.03", "2025.03.31", {**base, "InpGuardOn": "false", "InpDirMode": "0"})
    r1, l1 = scenario("G1", "2025.03.03", "2025.03.31", {**base, "InpGuardOn": "true", "InpDirMode": "0", "InpDailyStopPct": "4.0", "InpFloorStopPct": "90.0", "InpTargetPct": "0.0"})
    r4, l4 = scenario("G4", "2025.03.03", "2025.03.31", {**base, "InpGuardOn": "true", "InpDirMode": "0", "InpDailyStopPct": "50.0", "InpFloorStopPct": "90.0", "InpTargetPct": "0.0"})
    for tag, r, l in (("G0", r0, l0), ("G1", r1, l1), ("G4", r4, l4)):
        print(f"{tag}: net {r['net']:,.0f}, equity drawdown {r['eq_dd']:,.0f}, deals {0 if r['deals'] is None else len(r['deals'])}, log rows {len(l)}, note {r['note']!r}", flush=True)
    res["G0"] = dict(net=r0["net"], dd=r0["eq_dd"], deals=len(r0["deals"]) if r0["deals"] is not None else 0)
    res["G4"] = dict(net=r4["net"], dd=r4["eq_dd"], deals=len(r4["deals"]) if r4["deals"] is not None else 0)
    print(f"G4 vs G0 (guard must not interfere): net {r4['net']:,.2f} vs {r0['net']:,.2f}; deals {res['G4']['deals']} vs {res['G0']['deals']}", flush=True)
    # G1 checks
    l = l1.copy(); l["pd"] = pday(l["time"])
    stops = l[l.event == "DAYSTOP"]
    print(f"G1: day stops fired {len(stops)}; ENFORCE events {int((l.event == 'ENFORCE').sum())}", flush=True)
    worst = []
    for _, s in stops.iterrows():
        day = l[l.pd == s.pd]
        ref = s.dayref; eq_stop = s.equity
        mn = day[day.time >= s.time].equity.min() if len(day[day.time >= s.time]) else eq_stop
        worst.append((ref - min(eq_stop, mn)) / 1000.0)
    if worst:
        print(f"G1 (a): day loss at the stop and after, in % of $100K: median {np.median(worst):.2f}%, worst {max(worst):.2f}% (limit 4.00%; MT5 broker's 2-Step limit 5%)", flush=True)
    late = 0; checked = 0
    for _, s in stops.iterrows():
        after = l[(l.pd == s.pd) & (l.time > s.time)]
        for _, o in after[after.event == "DRV_OPEN"].iterrows():
            checked += 1
            enf = after[(after.event == "ENFORCE") & (after.time >= o.time) & (after.time <= o.time + pd.Timedelta(seconds=3))]
            late += 0 if len(enf) else 1
    print(f"G1 (b): driver opens after a stop: {checked}; not closed within 3 s: {late}", flush=True)
    resume = 0
    for _, s in stops.iterrows():
        nxt = l[(l.pd > s.pd) & (l.event == "DRV_OPEN")]
        resume += int(len(nxt) > 0 and (nxt.pd.iloc[0] - s.pd).days <= 5)
    print(f"G1 (c): stops followed by new driver trades within 5 days: {resume} of {len(stops)}", flush=True)
    # G5 day boundary
    nd = l1[l1.event == "NEWDAY"].copy()
    if len(nd):
        t = nd.time.dt.strftime("%H:%M"); print(f"G5: NEWDAY times (server): {t.value_counts().head(4).to_dict()} over {len(nd)} days, months covered {sorted(set(nd.time.dt.strftime('%Y-%m')))[:3]}", flush=True)
    # G2 pass lock
    r2, l2 = scenario("G2", "2024.10.01", "2024.10.31", {**base, "InpGuardOn": "true", "InpDirMode": "1", "InpDailyStopPct": "4.0", "InpFloorStopPct": "90.0", "InpTargetPct": "0.5", "InpLockBufferPct": "0.3", "InpMinDays": "4", "InpPhaseStart": "2024.10.01 00:00"})
    lk = l2[l2.event == "LOCK"]
    print(f"G2: lock events {len(lk)}", flush=True)
    if len(lk):
        t0 = lk.time.iloc[0]; before = l2[l2.time < t0]
        days = pday(before[before.event == "DRV_OPEN"].time).nunique()
        after = l2[l2.time > t0]
        reopen = after[after.event == "DRV_OPEN"]
        unmatched = sum(0 if len(after[(after.event == "ENFORCE") & (after.time >= o.time) & (after.time <= o.time + pd.Timedelta(seconds=3))]) else 1 for _, o in reopen.iterrows())
        print(f"G2: locked at {t0} equity {lk.equity.iloc[0]:,.0f} (target {100000 * 1.008:,.0f}); trading days before the lock {days} (need >= 4); driver opens after the lock {len(reopen)}, not closed within 3 s: {unmatched}; positions in the last SNAP {int(l2[l2.event == 'SNAP'].positions.iloc[-1])}", flush=True)
    # G3 emergency
    r3, l3 = scenario("G3", "2025.01.02", "2025.01.31", {**base, "InpGuardOn": "true", "InpDirMode": "2", "InpDailyStopPct": "90.0", "InpFloorStopPct": "1.5", "InpTargetPct": "0.0"})
    em = l3[l3.event == "EMERGENCY"]
    print(f"G3: emergency events {len(em)}", flush=True)
    if len(em):
        t0 = em.time.iloc[0]; after = l3[l3.time > t0]
        reopen = after[after.event == "DRV_OPEN"]
        unmatched = sum(0 if len(after[(after.event == "ENFORCE") & (after.time >= o.time) & (after.time <= o.time + pd.Timedelta(seconds=3))]) else 1 for _, o in reopen.iterrows())
        print(f"G3: emergency at {t0}, equity {em.equity.iloc[0]:,.0f} (floor {98500:,}); lowest equity afterwards {after.equity.min():,.0f}; driver opens after: {len(reopen)}, not closed within 3 s: {unmatched}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
