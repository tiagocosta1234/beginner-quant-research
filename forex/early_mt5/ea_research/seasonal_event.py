"""Family SE: overnight, turn-of-month and pre-FOMC index anomalies (PREREG_SEASONAL_EVENT.md).   env SE=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from scipy import stats
from mt5broker.ea_research import dip_addon as DA

US = ("SP", "NSDQ", "DOW"); DEV = ("2022-01-01", "2024-12-31"); VAL = ("2025-01-01", "2025-12-31"); HOLD = ("2026-01-01", "2026-09-30")
FLOOR = {"SE1": 2.0, "SE2": 10.0, "SE3": 10.0}; BAR = {"SE1": 2.0, "SE2": 1.65, "SE3": 1.65}


def px(m):
    d = DA.load(m)
    def at(hm, col): return d[d.hm == hm].drop_duplicates("date").set_index("date")[col]
    return dict(a1559=at(1559, "ao"), b1559=at(1559, "bo"), b0930=at(930, "bo"), a1400=at(1400, "ao"), b1400=at(1400, "bo"))


def avg(frames): return pd.concat(frames, axis=1).dropna().mean(axis=1)


def series():
    P = {m: px(m) for m in US}; out = {}
    # SE1: entry D 15:59 ask -> next trading day 09:30 bid; indexed by entry date
    s = []
    for m in US:
        e, x = P[m]["a1559"], P[m]["b0930"]; days = e.index.intersection(x.index).sort_values(); r = {}
        for D in e.index:
            nxt = x.index[x.index.searchsorted(D, side="right"):]
            if len(nxt) and (nxt[0] - D).days <= 4: r[D] = (x[nxt[0]] / e[D] - 1) * 1e4
        s.append(pd.Series(r))
    out["SE1"] = avg(s)
    # SE2: 4th-from-last trading day (15:59 ask) -> 3rd trading day of next month (15:59 bid)
    cal = P["SP"]["a1559"].index; ym = pd.Series(cal.to_period("M"), index=cal); s = []
    for m in US:
        e, x = P[m]["a1559"], P[m]["b1559"]; r = {}
        months = ym.unique()
        for k in range(len(months) - 1):
            cur, nxt = cal[ym.values == months[k]], cal[ym.values == months[k + 1]]
            if len(cur) < 4 or len(nxt) < 3: continue
            D, N = cur[-4], nxt[2]
            if D in e.index and N in x.index: r[D] = (x[N] / e[D] - 1) * 1e4
        s.append(pd.Series(r))
    out["SE2"] = avg(s)
    # SE3: prior trading day 14:00 ask -> FOMC day 14:00 bid
    fo = pd.to_datetime(pd.read_csv("D:/finance/data_macro/event_calendar.csv").query("kind == 'FOMC'").date); s = []
    for m in US:
        e, x = P[m]["a1400"], P[m]["b1400"]; r = {}
        for F in fo:
            if F not in x.index: continue
            prev = e.index[e.index < F]
            if len(prev) and (F - prev[-1]).days <= 4: r[prev[-1]] = (x[F] / e[prev[-1]] - 1) * 1e4
        s.append(pd.Series(r))
    out["SE3"] = avg(s)
    return out


def win(s, w): return s[(s.index >= w[0]) & (s.index <= w[1])]


def one(s):
    return dict(n=len(s), mean=s.mean(), t=s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan)


if __name__ == "__main__":
    S = series()
    if os.environ.get("SE") == "dry":                                   # counts only, no return statistic is printed
        for k, s in S.items(): print(k, "obs", len(s), "DEV", len(win(s, DEV)), "VAL", len(win(s, VAL)), "HOLD", len(win(s, HOLD)), "first", s.index.min().date(), "last", s.index.max().date())
    if os.environ.get("SE") == "run":
        rows = []
        for k, s in S.items():
            d, v = one(win(s, DEV)), one(win(s, VAL)); acc = bool(d["mean"] >= FLOOR[k] and d["t"] >= BAR[k] and v["mean"] > 0)
            row = dict(trial=k, dev_n=d["n"], dev_bp=round(d["mean"], 2), dev_t=round(d["t"], 2), val_n=v["n"], val_bp=round(v["mean"], 2), val_t=round(v["t"], 2), accepted=acc)
            if acc: h = one(win(s, HOLD)); row.update(hold_n=h["n"], hold_bp=round(h["mean"], 2), PASS=bool(h["mean"] > 0))
            rows.append(row)
        txt = pd.DataFrame(rows).to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "SEASONAL_EVENT_RESULT.txt"), "w").write(txt)
