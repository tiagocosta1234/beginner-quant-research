"""Family ID: the RSI(2) dip rule at H1 and H4 on six indices (PREREG_INTRADAY_DIP.md).   env ID=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data_mt5"; IDX = ("SP", "NSDQ", "DOW", "DAX", "NIKKEI", "ASX")
DEV = ("2022-01-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31"); HOLD = ("2026-01-01", "2026-09-30")
CFG = {"ID1": (3600, 30), "ID2": (14400, 120)}


def bars(m, sec, minmin):
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "bc", "ao"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]; d["b"] = d.t // sec
    g = d.groupby("b").agg(t0=("t", "first"), ob=("bo", "first"), oa=("ao", "first"), cb=("bc", "last"), n=("t", "size")); g = g[g.n >= minmin].reset_index(drop=True); g["t0"] = g.t0.astype(np.int64); return g


def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean(); return 100 - 100 / (1 + up / dn)


def trades(m, sec, minmin):
    g = bars(m, sec, minmin); c = g.cb; r = rsi2(c); s200, s5 = c.rolling(200).mean(), c.rolling(5).mean(); t0 = g.t0.values; out = []; i = 200; n = len(g)
    while i < n - 2:
        if r.iat[i] < 10 and c.iat[i] > s200.iat[i] and t0[i + 1] - t0[i] <= 2 * sec:
            j = i + 1
            while j < n - 2 and not (c.iat[j] > s5.iat[j] or r.iat[j] > 70 or j - i >= 5): j += 1
            if t0[j + 1] - t0[j] <= 2 * sec or True:
                ret = g.ob.iat[j + 1] / g.oa.iat[i + 1] - 1
                out.append(dict(mkt=m, entry=pd.Timestamp(t0[i + 1], unit="s"), exit=pd.Timestamp(t0[j + 1], unit="s"), ret=ret, bars=j + 1 - i))
            i = j + 1
        else: i += 1
    return out


def run(tid):
    sec, mm = CFG[tid]; rows = []
    for m in IDX: rows += trades(m, sec, mm)
    return pd.DataFrame(rows)


def win(df, w): return df[(df.entry >= w[0]) & (df.entry <= pd.Timestamp(w[1]) + pd.Timedelta(days=1))]


def by_day(df): return df.groupby(df.entry.dt.normalize()).ret.mean()


def pf(x): wn, ls = x[x > 0].sum(), -x[x < 0].sum(); return wn / ls if ls else np.inf


def summary(df, w, years):
    d = win(df, w)
    if d.empty: return dict(trades=0, days=0, per_year=0.0, mean=np.nan, pf=np.nan, t=np.nan)
    g = by_day(d); t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    return dict(trades=len(d), days=len(g), per_year=len(d) / years, mean=1e4 * g.mean(), pf=pf(g), t=t)


def sharpe(df, w, notional=25000.0):
    d = win(df, w); days = pd.bdate_range(w[0], w[1]); pnl = (d.assign(x=d.exit.dt.normalize()).groupby("x").ret.sum() * notional).reindex(days, fill_value=0.0); return pnl.mean() / pnl.std(ddof=1) * np.sqrt(252) if pnl.std() > 0 else np.nan


def f(s): return f"trades {s['trades']:5d} ({s['per_year']:5.0f}/yr) | days {s['days']:4d} | mean {s['mean']:+7.1f} bp | PF(day) {s['pf']:.2f} | t {s['t']:.2f}"


if __name__ == "__main__":
    R = {tid: run(tid) for tid in CFG}
    if os.environ.get("ID") == "dry":                                    # counts only, no return statistic printed
        for tid, df in R.items(): print(tid, "trades", len(df), "DEV", len(win(df, DEV)), "VAL", len(win(df, VAL)), "HOLD", len(win(df, HOLD)), "markets", df.mkt.value_counts().to_dict())
    if os.environ.get("ID") == "run":
        lines = []
        for tid, df in R.items():
            d, v = summary(df, DEV, 3.0), summary(df, VAL, 1.0); acc = bool(d["days"] >= 150 and d["mean"] >= 15 and d["pf"] >= 1.3 and d["t"] >= 2.0 and v["mean"] > 0 and v["pf"] >= 1.0)
            lines.append(f"{tid} ({'H1' if tid == 'ID1' else 'H4'})\n  DEV  2022-24: {f(d)}\n  VAL  2025   : {f(v)}\n  indicative Sharpe (25k per trade): DEV {sharpe(df, DEV):.2f} | VAL {sharpe(df, VAL):.2f}\n  accepted: {acc}")
            if acc: h = summary(df, HOLD, 0.75); lines.append(f"  HOLD 2026   : {f(h)} | pass: {bool(h['mean'] > 0)} | Sharpe {sharpe(df, HOLD):.2f}")
            lines.append("  by market (DEV+VAL, trades / mean bp): " + str({m: (len(g), round(1e4 * g.ret.mean(), 1)) for m, g in win(df, ("2022-01-01", "2025-12-31")).groupby("mkt")}) + "\n")
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "INTRADAY_DIP_RESULT.txt"), "w").write(txt)
