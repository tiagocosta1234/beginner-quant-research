"""Family X: combine every tested daily stream with the fixed rule of PREREG_COMBINE_ALL.md.   python -m mt5broker.ea_research.combine_all"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from mt5broker.ea_research import clean_boot_lib as L
from mt5broker.ea_batch.mt5_mc_config import CH
from mt5broker.ea_research import overnight_grid as NG, crypto_weekend as CW, turn_of_month as TM, cot as COT, event_macro as EV

CAL = pd.bdate_range("2022-01-03", "2026-09-30")
DEV, VAL, HOLD = ("2022-01-01", "2024-12-31"), ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-09-30")


def on_cal(s: pd.Series) -> pd.Series:
    s = s.groupby(s.index.normalize()).sum(); s.index = s.index.map(lambda d: d if d.dayofweek < 5 else d + pd.Timedelta(days=7 - d.dayofweek))
    return s.groupby(level=0).sum().reindex(CAL).fillna(0.0)


def pair_legs() -> dict:
    out = {}; lo, hi = L.day("2022-01-01"), L.day("2026-09-30")
    for leg in ("sdb", "xau5"):
        tr = L.ea_trades("mt5broker", leg, CH[leg] * 1.2, lo); r = L.C.simulate(L.bars(), tr, lo, hi, None, None)
        out[f"PAIR_{leg}"] = on_cal(pd.Series(r["V"], index=pd.to_datetime(r["days"] * 86400, unit="s")))
    return out


def streams() -> pd.DataFrame:
    S = pair_legs()
    F = pd.read_parquet("D:/finance/tmp/factory_daily.parquet"); F.index = pd.to_datetime(F.index)
    for c in F.columns: S[f"F_{c}"] = on_cal(F[c])
    G = NG.grid("2026-09-30")
    for c in G.columns: S[f"N_{c}"] = on_cal(G[c] * 10.0)                                   # bp per 100K -> USD
    W = CW.run_all("2026-09-30")["W1"].set_index("date").net; S["W1_crypto_weekend"] = on_cal(W * 10.0)
    E, _ = TM.events("2026-09-30")
    for k, s in E.items():
        s.index = [pd.Timestamp(m) + pd.offsets.BDay(3) for m in s.index]; S[f"TOM_{k}"] = on_cal(s * 10.0)
    C = COT.weeks("2026-09-30")
    for k, g in C.groupby("trial"):
        w = g.groupby("week").net.mean(); w.index = w.index + pd.Timedelta(days=7); S[f"COT_{k}"] = on_cal(w * 10.0)
    v1 = EV.v1_events(pd.read_csv(EV.CAL)).set_index("date").net; S["V1_preFOMC"] = on_cal(v1 * 10.0)
    return pd.DataFrame(S)


def sl(x, p): return x[(x.index >= p[0]) & (x.index <= p[1])]


def stats(x):
    eq = x.cumsum(); return dict(mean=float(x.mean()), sh=float(x.mean() / x.std(ddof=1)), dd=float((eq.cummax() - eq).max()))


def p_pass(x, H, paths=20000, seed=3):
    rng = np.random.default_rng(seed); v = x.to_numpy(); n = len(v); idx = np.empty((paths, H), int); idx[:, 0] = rng.integers(0, n, paths)
    jump = rng.random((paths, H)) < 0.2; new = rng.integers(0, n, (paths, H))
    for j in range(1, H): idx[:, j] = np.where(jump[:, j], new[:, j], (idx[:, j - 1] + 1) % n)
    cnt = np.full(paths, 99.68); st = np.zeros(paths, np.int8)
    for j in range(H):
        d = np.maximum(v[idx[:, j]], -2000.0); act = st == 0
        br = act & (100000 + cnt + d <= 92000); st[br] = 2; act = st == 0
        cnt = np.where(act, cnt + np.minimum(d, 2000.0), cnt); st[act & (cnt >= 8000)] = 1
    return float((st == 1).mean()), float((st == 2).mean())


def evaluate(name, P):
    for nm, per in (("DEV 2022-24", DEV), ("VAL 2025", VAL), ("2026", HOLD)):
        x = sl(P, per); s = stats(x); pp = [p_pass(x, h) for h in (15, 36, 52)]
        print(f"  {name:10s} {nm:11s}: mean {s['mean']:+7.1f} USD/day | daily Sharpe {s['sh']:+.3f} (~{s['sh']*np.sqrt(252):+.1f}/yr) | max DD {s['dd']:,.0f} | P(pass) 15/36/52 bd: {[round(100*a, 1) for a, b in pp]}% (breach {[round(100*b, 1) for a, b in pp]}%)")


def main():
    S = streams(); d = sl(S, DEV); n = len(d); t = d.mean() / (d.std(ddof=1) / np.sqrt(n))
    sel = [c for c in S.columns if t[c] >= 2.0 and d[c].mean() > 0]
    print(f"streams {S.shape[1]} | days {len(S)} | selected on DEV (t >= 2, mean > 0): {len(sel)}")
    for c in sorted(sel, key=lambda c: -t[c]): print(f"   {c:40s} DEV t {t[c]:+.2f}  mean {d[c].mean():+.1f} USD/day")
    print("   best 8 of the rest by DEV t:", {c: round(float(t[c]), 2) for c in t.drop(sel).sort_values(ascending=False).head(8).index})
    def build(cols):
        X = S[cols] * (300.0 / sl(S[cols], DEV).std(ddof=1)); X = X.clip(lower=-500.0); P = X.sum(axis=1); return P * (800.0 / sl(P, DEV).std(ddof=1))
    if sel:
        P = build(sel); print("\nPORTFOLIO (selected streams, inverse-vol, -500 daily floor each):"); evaluate("portfolio", P)
        if len(sel) > 1: C = sl(S[sel], DEV).corr().to_numpy(); print(f"   median DEV correlation between selected streams {np.median(C[np.triu_indices(len(sel), 1)]):+.2f}")
    pair = [c for c in S.columns if c.startswith("PAIR_")]; Q = build(pair); print("\nYARDSTICK (gold pair legs only, same scaling):"); evaluate("pair", Q)
    with open(L.C.__file__.replace("clean_guard_sim.py", "LEDGER.csv"), "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},combine_all,X,DEV,{n},{len(sel)},,,,,,selected {';'.join(sel)[:400]}\n")


if __name__ == "__main__":
    main()
