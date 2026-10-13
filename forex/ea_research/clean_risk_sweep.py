import numpy as np, pandas as pd
from forex.ea_research import clean_guard_sim as C
from forex.ea_batch.mt5_mc_config import CH
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch.mt5data_sizing_long import trades_mt5broker
bars = C.load_bars(); dd = lambda s: (pd.Timestamp(s) - C.EPOCH).days
A, CAPD, TARGET, LOCK = C.A, C.CAPD, C.TARGET, C.LOCK
def outcomes(V, B, Hi, H=37, lock=True):
    res = {"pass": [], "breach": 0, "run": 0}; n = 0
    for i0 in range(len(V)):
        if i0 + H > len(V): continue
        n += 1; bal, cnt, r = A, 0.0, "run"
        for j in range(H):
            k = i0 + j
            if B[k] <= -0.025 * A or bal + B[k] <= 0.92 * A: r = "breach"; break
            if lock and cnt + min(Hi[k], CAPD) >= LOCK: r = "pass"; res["pass"].append(j + 1); break
            x = min(V[k], CAPD) if V[k] > 0 else V[k]; bal += x; cnt += x
            if cnt >= TARGET: r = "pass"; res["pass"].append(j + 1); break
        if r == "breach": res["breach"] += 1
        elif r == "run": res["run"] += 1
    return res, n
pools = {"LAST 12M (MT5 broker trades)": ("mt5", dd("2025-10-01"), dd("2026-09-30")), "2022-26 (MT5 broker trades scaled)": ("mt5broker", dd("2022-01-01"), dd("2026-09-30"))}
for pn, (src, lo, hi) in pools.items():
    print(f"\n##### {pn}", flush=True)
    for m in (1.0, 1.2, 1.5, 1.8, 2.1, 2.5, 3.0, 3.5, 4.0):
        lots = {k: v * m for k, v in CH.items()}
        trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
        tr = C.prep(trs)
        if src == "mt5broker":
            keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
        for nm, L in (("loss cap 2,000", CAPD), ("no guard", None)):
            r = C.simulate(bars, tr, lo, hi, None, L); o, n = outcomes(r["V"], r["B"], r["Hi"]); p = np.array(o["pass"])
            print(f"  x{m:<3} SDB {0.12*m:.2f} + XAU5 {0.04*m:.3f} | {nm:15s}| pass {100*len(p)/n:5.1f}% breach {100*o['breach']/n:5.1f}% still-open {100*o['run']/n:5.1f}% | days to pass: mean {p.mean() if len(p) else float('nan'):4.1f} median {np.median(p) if len(p) else float('nan'):4.0f} p25 {np.percentile(p,25) if len(p) else float('nan'):4.0f} p75 {np.percentile(p,75) if len(p) else float('nan'):4.0f} [starts {n}]", flush=True)
