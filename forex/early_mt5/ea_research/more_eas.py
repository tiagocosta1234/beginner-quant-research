"""Families TS (trend on 18 markets), PI (index pairs), LL (lead-lag), PREREG_MORE_EAS.md.   env ME=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
TSM = ["XAUUSD", "XAGUSD", "WTI", "BRENT", "SP", "NSDQ", "DOW", "DAX", "NIKKEI", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "BTCUSD", "ETHUSD"]
DEV = ("2022-01-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31"); HOLD = ("2026-01-01", "2026-09-30"); DEV_TS = ("2023-01-01", "2024-12-31")
_C = {}


def load(m):
    if m in _C: return _C[m]
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bl", "bc", "ao"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)].reset_index(drop=True)
    srv = pd.to_datetime(d.t, unit="s"); d["sdate"] = srv.dt.normalize(); d["shm"] = srv.dt.hour * 100 + srv.dt.minute
    loc = srv.dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("America/New_York")
    d["date"] = loc.dt.tz_localize(None).dt.normalize(); d["hm"] = loc.dt.hour * 100 + loc.dt.minute
    _C[m] = d.dropna(subset=["date"]); return _C[m]


def at(d, key, val, col, by): return d[d[key] == val].drop_duplicates(by).set_index(by)[col]


# ---------------- TS
def ts():
    px, hs = {}, {}
    for m in TSM:
        d = load(m); px[m] = at(d, "hm", 1559, "bo", "date"); hs[m] = (at(d, "hm", 1559, "ao", "date") - px[m]) / px[m] / 2
    cal = px["SP"].index
    P = pd.DataFrame({m: px[m].reindex(cal.union(px[m].index)).ffill().reindex(cal) for m in TSM})
    H = pd.DataFrame({m: hs[m].reindex(cal.union(hs[m].index)).ffill().reindex(cal) for m in TSM})
    R = P.pct_change(); mom = P / P.shift(252) - 1; sd = R.rolling(60).std(ddof=1) * np.sqrt(252)
    month = pd.Series(cal.to_period("M"), index=cal); first = month != month.shift(1)
    W = pd.DataFrame(0.0, index=cal, columns=TSM); w = pd.Series(0.0, index=TSM); cost = pd.Series(0.0, index=cal)
    for i, D in enumerate(cal):
        if first.iloc[i] and i >= 252:
            ok = mom.iloc[i].notna() & sd.iloc[i].notna() & (sd.iloc[i] > 0)
            new = (np.sign(mom.iloc[i]) * np.minimum(0.10 / sd.iloc[i], 3.0) / len(TSM)).where(ok, 0.0)
            cost.iloc[i] = float(((new - w).abs() * H.iloc[i].fillna(0.0)).sum()); w = new
        W.iloc[i] = w.values
    port = (W.shift(1) * R).sum(axis=1) - cost                           # positions set at the close earn the next day's return
    return (port * 100).loc[cal[252]:]                                   # % of NAV


# ---------------- PI and the shared pair machinery
def pair_trades(xb, xa, yb, ya):
    idx = xb.index.intersection(yb.index).intersection(xa.index).intersection(ya.index).sort_values()
    xb, xa, yb, ya = xb[idx], xa[idx], yb[idx], ya[idx]
    lr = np.log(xb / yb); z = (lr - lr.rolling(60).mean()) / lr.rolling(60).std(ddof=1); out, i = {}, 60
    while i < len(idx):
        if abs(z.iloc[i]) >= 2.0:
            side = -1 if z.iloc[i] >= 2.0 else 1                          # +1 = long X short Y
            e = i; j = i + 1
            while j < len(idx) - 1 and abs(z.iloc[j]) > 0.5 and j - e < 20: j += 1
            if side == 1: ret = (xb.iloc[j] / xa.iloc[e] - 1) - (ya.iloc[j] / yb.iloc[e] - 1)
            else: ret = (yb.iloc[j] / ya.iloc[e] - 1) - (xa.iloc[j] / xb.iloc[e] - 1)
            out[idx[e]] = out.get(idx[e], 0.0) + ret * 1e4; i = j + 1
        else: i += 1
    return pd.Series(out)


def pi():
    P = {m: (at(load(m), "hm", 1559, "bo", "date"), at(load(m), "hm", 1559, "ao", "date")) for m in ("NSDQ", "SP", "DOW")}; parts = []
    for a, b in (("NSDQ", "SP"), ("SP", "DOW"), ("NSDQ", "DOW")): parts.append(pair_trades(P[a][0], P[a][1], P[b][0], P[b][1]))
    return pd.concat(parts).sort_index()


# ---------------- LL
def ret_window(d, t0, t1):
    a, b = at(d, "shm", t0, "bo", "sdate"), at(d, "shm", t1, "bo", "sdate"); return (b / a - 1).dropna()


def ll():
    dax, nik = load("DAX"), load("NIKKEI"); s1 = np.sign(ret_window(dax, 1000, 1830)); s2 = np.sign(ret_window(nik, 305, 755)); obs = []
    for m in ("SP", "NSDQ", "DOW"):
        d = load(m); ea, eb = at(d, "shm", 1830, "ao", "sdate"), at(d, "shm", 1830, "bo", "sdate"); xb, xa = at(d, "hm", 1559, "bo", "date"), at(d, "hm", 1559, "ao", "date")
        ndate = d[d.shm == 1830].drop_duplicates("sdate").set_index("sdate").date; r = {}
        for D, s in s1.items():
            if s == 0 or D not in ea.index: continue
            nd = ndate[D]
            if nd not in xb.index: continue
            r[D] = (xb[nd] / ea[D] - 1) * 1e4 if s > 0 else (eb[D] / xa[nd] - 1) * 1e4
        obs.append(pd.Series(r))
    ll1 = pd.concat(obs, axis=1, sort=True).dropna().mean(axis=1)
    d = load("DAX"); ea, eb = at(d, "shm", 1000, "ao", "sdate"), at(d, "shm", 1000, "bo", "sdate"); xb, xa = at(d, "shm", 1825, "bo", "sdate"), at(d, "shm", 1825, "ao", "sdate"); r = {}
    for D, s in s2.items():
        if s == 0 or D not in ea.index or D not in xb.index: continue
        r[D] = (xb[D] / ea[D] - 1) * 1e4 if s > 0 else (eb[D] / xa[D] - 1) * 1e4
    return ll1, pd.Series(r)


def win(s, w): return s[(s.index >= w[0]) & (s.index <= w[1])]
def one(s): return dict(n=len(s), mean=s.mean() if len(s) else np.nan, t=s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan)


if __name__ == "__main__":
    T, I, (L1, L2) = ts(), pi(), ll()
    if os.environ.get("ME") == "dry":                                    # counts only, no return statistic printed
        print("TS days", len(T), "DEV", len(win(T, DEV_TS)), "VAL", len(win(T, VAL)), "HOLD", len(win(T, HOLD)), "first", T.index.min().date())
        for k, s in (("PI", I), ("LL1", L1), ("LL2", L2)): print(k, "obs", len(s), "DEV", len(win(s, DEV)), "VAL", len(win(s, VAL)), "HOLD", len(win(s, HOLD)))
    if os.environ.get("ME") == "run":
        rows = []
        dts, vts = win(T, DEV_TS), win(T, VAL); sr = dts.mean() / dts.std(ddof=1) * np.sqrt(252)
        yrs = [win(T, (f"{y}-01-01", f"{y}-12-31")).sum() for y in (2023, 2024)]
        acc = bool(sr >= 0.5 and all(y > 0 for y in yrs) and vts.mean() > 0)
        row = dict(trial="TS", dev_n=len(dts), dev_stat=f"SR {sr:.2f}; 2023 {yrs[0]:+.1f}% 2024 {yrs[1]:+.1f}%", val_n=len(vts), val_stat=f"{vts.sum():+.1f}% (SR {vts.mean() / vts.std(ddof=1) * np.sqrt(252):.2f})", accepted=acc)
        if acc: h = win(T, HOLD); row.update(hold=f"{h.sum():+.1f}%", PASS=bool(h.mean() > 0))
        rows.append(row)
        FL = {"PI": (8.0, 1.65, 25), "LL1": (2.0, 2.0, 0), "LL2": (2.0, 2.0, 0)}
        for k, s in (("PI", I), ("LL1", L1), ("LL2", L2)):
            fl, bar, mn = FL[k]; d, v = one(win(s, DEV)), one(win(s, VAL)); acc = bool(d["n"] >= mn and d["mean"] >= fl and d["t"] >= bar and v["mean"] > 0)
            row = dict(trial=k, dev_n=d["n"], dev_stat=f"{d['mean']:+.2f} bp, t {d['t']:.2f}", val_n=v["n"], val_stat=f"{v['mean']:+.2f} bp, t {v['t']:.2f}", accepted=acc)
            if acc: h = one(win(s, HOLD)); row.update(hold=f"{h['mean']:+.2f} bp (n {h['n']})", PASS=bool(h["mean"] > 0))
            rows.append(row)
        txt = pd.DataFrame(rows).to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "MORE_EAS_RESULT.txt"), "w").write(txt)
