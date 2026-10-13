import itertools, numpy as np, pandas as pd
from forex.ea_research import clean_guard_sim as C
from forex.ea_batch.mt5_mc_config import CH, FU
from forex.ea_batch import mt5data_guard_carry as GC
from forex.ea_batch.mt5data_sizing_long import trades_mt5broker
bars = C.load_bars(); dd = lambda s: (pd.Timestamp(s) - C.EPOCH).days
A, CAPD, TARGET, LOCK, FEE, GOAL = C.A, C.CAPD, C.TARGET, C.LOCK, 451.0, 15000.0
H = int(np.busday_count("2026-10-09", "2026-12-23")); print("last day withdrawals can be requested = 22 Dec; business days 9 Oct .. 22 Dec:", H, flush=True)
def series(src, lots, P, L, lo, hi):
    trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
    tr = C.prep(trs)
    if src == "mt5broker":
        keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
    return C.simulate(bars, tr, lo, hi, P, L)
def passidx(rc, H):
    Vc, Bc, Hc = rc["V"], rc["B"], rc["Hi"]; n = len(Vc); res = {}
    for i0 in range(n - H + 1):
        bal, cnt = A, 0.0; res[i0] = None
        for j in range(H):
            k = i0 + j
            if Bc[k] <= -0.025 * A or bal + Bc[k] <= 0.92 * A: break
            if cnt + min(Hc[k], CAPD) >= LOCK: res[i0] = k; break
def series(src, lots, P, L, lo, hi):
    trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
    tr = C.prep(trs)
    if src == "mt5broker":
        keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
    return C.simulate(bars, tr, lo, hi, P, L)
for pn, (src, lo, hi) in {"LAST 12M": ("mt5", dd("2025-10-01"), dd("2026-09-30")), "2022-26": ("mt5broker", dd("2022-01-01"), dd("2026-09-30"))}.items():
    r = series(src, {k: v * 1.2 for k, v in CH.items()}, None, CAPD, lo, hi); V, B, Hi = r["V"], r["B"], r["Hi"]; n = len(V); N = prem = aware_pass = 0
    for i0 in range(n - 53 + 1):
        N += 1; cnt = 0.0; seen = False
        for j in range(53):
            k = i0 + j
            if B[k] <= -0.025 * A or A + cnt + B[k] <= 0.92 * A: break
            aware = cnt + min(Hi[k], CAPD) >= LOCK; unaware = cnt + Hi[k] >= LOCK
            if unaware and not aware and not (cnt + min(V[k], CAPD) >= TARGET): prem += 1; break         # live guard (equity >= 108.3%) would flatten and stop; MT5 broker then removes the excess above the 2,000 cap and the test is NOT passed
            if aware: aware_pass += 1; break
            x = min(V[k], CAPD) if V[k] > 0 else V[k]; cnt += x
            if cnt >= TARGET: aware_pass += 1; break
    print(f"{pn} x1.2 (53-day horizon, {N} starts): premature lock (guard flattens and stops at equity 108.3% while the counted profit would still be below 8%) in {100*prem/N:4.1f}% of starts; pass {100*aware_pass/N:4.1f}%")
