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
    r = C.simulate(bars, tr, lo, hi, P, L); return {k: r[k].tolist() for k in ("V", "B")}
H1 = 15           # business days left this month: Mon 12 Oct .. Fri 30 Oct (today's session is almost over)
def run(r, d):
    V, B = r["V"], r["B"]; n = len(V); p = b = N = 0
    for i0 in range(n - H1 + 1):
        N += 1; cnt = 0.0
        for j in range(H1):
            k = i0 + j
            if B[k] <= -0.025 * A or A + cnt + B[k] <= 0.92 * A: b += 1; break
            v = V[k] + d; cnt += min(v, CAPD) if v > 0 else v
            if cnt >= TARGET: p += 1; break
    return 100 * p / N, 100 * b / N
for pn, (src, lo, hi) in {"LAST 12M": ("mt5", dd("2025-10-01"), dd("2026-09-30")), "2022-26": ("mt5broker", dd("2022-01-01"), dd("2026-09-30"))}.items():
    for m in (1.2, 1.8):
        r = series(src, {k: v * m for k, v in CH.items()}, None, CAPD, lo, hi); mean = np.mean(r["V"])
        print(f"{pn} x{m} (pair mean {mean:5.0f} USD/day): P(pass in 15 business days) / breach vs extra smooth alpha per day:  " + "  ".join(f"+{d}: {run(r, d)[0]:4.1f}%/{run(r, d)[1]:3.1f}%" for d in (0, 100, 200, 300, 400, 500, 700)), flush=True)
