import sys
sys.argv = ["x", "--source", "mt5broker"]
import numpy as np, pandas as pd
from mt5broker.ea_research import clean_guard_sim as C
from mt5broker.ea_research import clean_guard_tick as TK
from mt5broker.ea_batch.mt5_mc_config import CH
from mt5broker.ea_batch import mt5data_guard_carry as GC
from mt5broker.ea_batch import mt5data_guard_speed as GS
from mt5broker.ea_batch.mt5data_sizing_long import trades_mt5broker
A, CAPD, TARGET, H1 = C.A, C.CAPD, C.TARGET, 15
bars = C.load_bars(); dd = lambda s: (pd.Timestamp(s) - C.EPOCH).days
def outcome(V, B, hmax=H1):
    p = b = N = 0; n = len(V)
    for i0 in range(n - hmax + 1):
        N += 1; cnt = 0.0
        for j in range(hmax):
            k = i0 + j
            if B[k] <= -0.025 * A or A + cnt + B[k] <= 0.92 * A: b += 1; break
            cnt += min(V[k], CAPD) if V[k] > 0 else V[k]
            if cnt >= TARGET: p += 1; break
    return 100 * p / N, 100 * b / N
def prep_mt5(m):
    lots = {k: v * m for k, v in CH.items()}
    return C.prep([GS.with_side(GC.trades("77900", lots["sdb"])).drop(columns=["side", "in_ms", "out_ms"]), GS.with_side(GC.trades("mkt_xau5min", lots["xau5"])).drop(columns=["side", "in_ms", "out_ms"])])
def prep_5y(m, lo):
    lots = {k: v * m for k, v in CH.items()}; tr = C.prep([trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])]); keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f; return tr
import MetaTrader5 as mt5
if not mt5.initialize(path=GS.TERM, portable=True, timeout=120000): raise SystemExit(f"cannot attach: {mt5.last_error()}")
try:
    lo12, hi12, lo5, hi5 = dd("2025-10-01"), dd("2026-09-30"), dd("2022-01-01"), dd("2026-09-30")
    print("size | SDB + 5-min lots | SDB risk per trade | LAST 12M tick model: pass / breach in 15 days | LAST 12M minute model | 2022-26 minute model", flush=True)
    for m in (1.2, 1.8, 2.5, 3.0, 3.5, 4.0, 5.0):
        tr = prep_mt5(m); rt = TK.simulate_tick(bars, tr, lo12, hi12, CAPD, mt5); rm = C.simulate(bars, tr, lo12, hi12, None, CAPD); r5 = C.simulate(bars, prep_5y(m, lo5), lo5, hi5, None, CAPD)
        a, b, c = outcome(rt["V"], rt["B"]), outcome(rm["V"], rm["B"]), outcome(r5["V"], r5["B"]); sd = 0.12 * m
        print(f"x{m:<4} | {0.12*m:.2f} + {0.04*m:.3f} | {0.95*m:.2f}% | tick {a[0]:4.1f}% / {a[1]:4.1f}% | minute {b[0]:4.1f}% / {b[1]:4.1f}% | 2022-26 minute {c[0]:4.1f}% / {c[1]:4.1f}% | tick days replayed {rt['tickdays']}", flush=True)
finally:
    mt5.shutdown()
