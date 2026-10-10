"""VERIFICATION 1 of the claim 'the two daily caps raise P(pass by 30 Nov) from 12.8% to 22.4%': which cap causes it? (minute-level MT5 broker series, 37 business days)   python -m mt5broker.ea_research.verify_guard_gain
Variants per size: no cap, LOSS cap only (-2,000), PROFIT cap only (+2,000), both. Also prints the sum of the daily closed P&L and the share of the counted profit lost to the 2%-a-day limit, so the mechanism is visible."""
import sys
sys.argv = ["x", "--source", "mt5broker"]
import numpy as np
import pandas as pd

from mt5broker.ea_batch import mt5_combo_v2 as V2
from mt5broker.ea_batch.mt5_mc_config import CH
from mt5broker.ea_batch import mt5data_guard_carry as GC
from mt5broker.ea_batch.mt5data_sizing_long import trades_mt5broker
from mt5broker.ea_research.deadline_lock import run

CAPD = 2_000.0


def main():
    U, E1, R1, st, days = V2.build_ns({"77900": 1.0, "mkt_xau5min": 0.0}, True); _, E2, R2, _, _ = V2.build_ns({"77900": 0.0, "mkt_xau5min": 1.0}, True); S = {}
    for m in (1.0, 1.4):
        lots = {k: v * m for k, v in CH.items()}; trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])]
        for nm, P, L in (("no cap", None, None), ("loss cap only", None, CAPD), ("profit cap only", CAPD, None), ("both caps", CAPD, CAPD)):
            S[f"{nm} {m}"] = GC.series(U, E1, R1, E2, R2, st, lots, trs, P, L, 0.0)
    d = pd.DatetimeIndex(S["no cap 1.0"]["days"]); idx = [i for i in range(len(d)) if d[i] >= pd.Timestamp("2022-01-01")]
    print("ALL 2022-26 starts, by 30 Nov (37 bd):", flush=True)
    for m in (1.0, 1.4):
        for nm in ("no cap", "loss cap only", "profit cap only", "both caps"):
            r = S[f"{nm} {m}"]; V = r["V"][np.asarray(d >= pd.Timestamp("2022-01-01"))]; a, n = run(S, idx, f"{nm} {m}", 37, False)
            lost = 1 - np.minimum(V, CAPD).clip(min=None).sum() / V.sum() if V.sum() else float("nan")
            print(f"  x{m} {nm:16s} pass {100*a['pass']/n:5.1f}% breach {100*a['breach']/n:4.1f}% | sum of daily P&L {V.sum():9,.0f} | counted (2% a day) {np.minimum(V, CAPD).sum():9,.0f} -> {100*(1 - np.minimum(V, CAPD).sum()/V.sum()):4.1f}% lost to the daily limit | days above +2,000: {int((V > CAPD).sum())}", flush=True)


if __name__ == "__main__":
    main()
