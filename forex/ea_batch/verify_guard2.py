"""Second round of AccountGuard tests, with the kill switch (after the first round showed that a trader that re-opens every 10 s bleeds the account through the spread even though every re-open is closed within 3 s).

K1  day stop 4% with the kill switch after 3 forced closes (the same stubborn driver, Mar 2025)   -> the account must stay near the stop level instead of bleeding away
K3  emergency stop at 1.5% with the kill switch (driver sells in a rally, Jan 2025)                -> equity stays near the floor
L1  pass lock: target 0.5% + 0.3% buffer, min trading days 1, driver buys only (Oct 2024)            -> LOCK fires with the equity above target + buffer; later opens are closed and the kill switch ends the run
(L0, from round one: the lock did NOT fire on days 1-3 although the equity was above the target, because the minimum of 4 trading days was not met.)
STOP THE EA BATCH FIRST.   python -m forex.ea_batch.verify_guard2
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.ea_batch.verify_guard import scenario, pday


def summarize(tag, l):
    s = l[l.event == "SNAP"]
    k = l[l.event == "KILL"]
    print(f"{tag}: events {l.event.value_counts().to_dict()}", flush=True)
    print(f"{tag}: equity first {s.equity.iloc[0]:,.0f}, lowest {min(s.equity.min(), l.equity.min()):,.0f}, last row {l.equity.iloc[-1]:,.0f} at {l.time.iloc[-1]}; kill rows {len(k)}", flush=True)


def main():
    base = {"InpDriverLots": "1.0", "InpEveryMin": "45", "InpHoldMin": "40", "InpStubborn": "true", "InpGuardOn": "true"}
    r, l = scenario("K1", "2025.03.03", "2025.03.31", {**base, "InpDirMode": "0", "InpDailyStopPct": "4.0", "InpFloorStopPct": "90.0", "InpTargetPct": "0.0", "InpKillAfter": "3"})
    print(f"K1: net {r['net']:,.0f}, deals {0 if r['deals'] is None else len(r['deals'])}", flush=True); summarize("K1", l)
    st = l[l.event == "DAYSTOP"]
    for _, s in st.iterrows():
        after = l[l.time > s.time]
        print(f"K1 day stop at {s.time}: equity {s.equity:,.0f} (reference {s.dayref:,.0f}, i.e. {(s.dayref - s.equity) / 1000:.2f}% down); lowest equity afterwards {after.equity.min():,.0f}; forced closes before the kill {int((after.event == 'ENFORCE').sum())}", flush=True)
    r, l = scenario("K3", "2025.01.02", "2025.01.31", {**base, "InpDirMode": "2", "InpDailyStopPct": "90.0", "InpFloorStopPct": "1.5", "InpTargetPct": "0.0", "InpKillAfter": "3"})
    print(f"K3: net {r['net']:,.0f}", flush=True); summarize("K3", l)
    em = l[l.event == "EMERGENCY"]
    if len(em):
        print(f"K3 emergency at {em.time.iloc[0]}: equity {em.equity.iloc[0]:,.0f} (floor 98,500); lowest equity afterwards {l[l.time > em.time.iloc[0]].equity.min():,.0f}", flush=True)
    r, l = scenario("L1", "2024.10.01", "2024.10.31", {**base, "InpDirMode": "1", "InpDailyStopPct": "50.0", "InpFloorStopPct": "90.0", "InpTargetPct": "0.5", "InpLockBufferPct": "0.3", "InpMinDays": "1", "InpPhaseStart": "2024.10.01 00:00", "InpKillAfter": "3"})
    print(f"L1: net {r['net']:,.0f}", flush=True); summarize("L1", l)
    lk = l[l.event == "LOCK"]
    if len(lk):
        t0 = lk.time.iloc[0]
        print(f"L1 lock at {t0}: equity {lk.equity.iloc[0]:,.0f} (target + buffer = 100,800); balance {lk.balance.iloc[0]:,.0f}; positions after lock in the next rows: {l[l.time > t0].positions.head(5).tolist()}; lowest equity afterwards {l[l.time > t0].equity.min():,.0f}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
