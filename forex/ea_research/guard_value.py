"""What is each lever worth for 'pass by 30 November' (37 business days) and over a long life? Same machinery as deadline_lock.py.   python -m forex.ea_research.guard_value
Rows: (a) NO guard at all (the EAs as published), (b) both daily caps (what runs today), (c) caps + pass lock, then the same at 1.4x. MT5-based 2022-26 series, minute-level halts, every start day; 'life' = 300 business days."""
import sys
sys.argv = ["x", "--source", "mt5broker"]
import numpy as np
import pandas as pd

from forex.ea_batch import mt5_combo_v2 as V2
from forex.ea_batch.mt5_mc_config import CH
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch.mt5data_sizing_long import trades_mt5broker
from forex.ea_research.deadline_lock import run

CAPD = 2_000.0


def main():
    U, E1, R1, st, days = V2.build_ns({"77900": 1.0, "mkt_xau5min": 0.0}, True); _, E2, R2, _, _ = V2.build_ns({"77900": 0.0, "mkt_xau5min": 1.0}, True); S = {}
    for m in (1.0, 1.4):
        lots = {k: v * m for k, v in CH.items()}; trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])]
        S[f"nocap {m}"] = GC.series(U, E1, R1, E2, R2, st, lots, trs, None, None, 0.0); S[f"caps {m}"] = GC.series(U, E1, R1, E2, R2, st, lots, trs, CAPD, CAPD, 0.0)
    d = pd.DatetimeIndex(S["caps 1.0"]["days"])
    for title, lo, hi in (("ALL 2022-26 starts", "2022-01-01", "2027-01-01"), ("last 12 months of starts", "2025-10-01", "2027-01-01")):
        idx = [i for i in range(len(d)) if pd.Timestamp(lo) <= d[i] < pd.Timestamp(hi)]; print(f"\n##### {title}", flush=True)
        for m in (1.0, 1.4):
            for label, key, lock in ((f"x{m} NO guard", f"nocap {m}", False), (f"x{m} both caps (today)", f"caps {m}", False), (f"x{m} caps + pass lock", f"caps {m}", True)):
                a, n = run(S, idx, key, 37, lock); b, n2 = run(S, idx, key, 300, lock)
                print(f"  {label:26s} by 30 Nov (37 bd): pass {100*a['pass']/n:5.1f}% breach {100*a['breach']/n:5.1f}% | over a long life (300 bd): pass {100*b['pass']/n2:5.1f}% breach {100*b['breach']/n2:5.1f}%  [starts {n} / {n2}]", flush=True)


if __name__ == "__main__":
    main()
