"""Family AL: five hypotheses on data we never used (Fear & Greed, funding, stablecoins, real yields), PREREG_ALT_DATA.md.   env AL=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path
from forex.ea_research import more_eas as ME

DATA = Path(__file__).resolve().parents[1] / "data_mt5"; ALT = Path("D:/finance/data_macro/alt")
DEV, VAL, HOLD = ME.DEV, ME.VAL, ME.HOLD
_U = {}


def load_utc(m):
    if m in _U: return _U[m]
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]
    utc = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").dt.tz_localize(None)
    d = d.assign(utc=utc).dropna(subset=["utc"]).sort_values("utc").reset_index(drop=True); _U[m] = d; return d


def fill(m, ts, col):
    """first bar at or after ts, within 10 minutes; NaN otherwise"""
    d = load_utc(m); i = d.utc.searchsorted(ts, side="left")
    if i >= len(d) or (d.utc.iat[i] - ts) > pd.Timedelta(minutes=10): return np.nan
    return d[col].iat[i]


def run_crypto(signals, hold_days):
    """signals: Series date -> +1/-1 (UTC midnight of the entry day). One position per asset at a time; BTC and ETH averaged per entry date."""
    per = {}
    for m in ("BTCUSD", "ETHUSD"):
        busy = pd.Timestamp("1900-01-01"); r = {}; sg = signals[m] if isinstance(signals, dict) else signals
        for D, s in sg.sort_index().items():
            if D < busy: continue
            X = D + pd.Timedelta(days=hold_days)
            if s > 0: e, x = fill(m, D, "ao"), fill(m, X, "bo"); ret = x / e - 1
            else: e, x = fill(m, D, "bo"), fill(m, X, "ao"); ret = e / x - 1
            if np.isfinite(ret): r[D] = ret * 1e4; busy = X
        per[m] = pd.Series(r)
    return pd.concat(per, axis=1, sort=True).mean(axis=1).dropna()


def al1():
    f = pd.read_csv(ALT / "fng.csv", parse_dates=["date"]).set_index("date").fng; f = f[f.index >= "2021-12-01"]
    return run_crypto(pd.Series(1, index=f.index[f <= 25]), 7)


def al2():
    f = pd.read_csv(ALT / "fng.csv", parse_dates=["date"]).set_index("date").fng; f = f[f.index >= "2021-12-01"]
    return run_crypto(pd.Series(-1, index=f.index[f >= 75]), 7)


def al3():
    sig = {}
    for sym, m in (("BTCUSDT", "BTCUSD"), ("ETHUSDT", "ETHUSD")):
        d = pd.read_csv(ALT / f"funding_{sym}.csv", parse_dates=["time"]); d["time"] = d.time.dt.round("min"); d = d.set_index("time").rate
        tr = d.rolling(3).sum(); mid = tr[(tr.index.hour == 0) & (tr.index.minute == 0)].dropna(); r = {}
        for t, v in mid.items():
            if t < pd.Timestamp("2021-12-01"): continue
            if v >= 0.0009: r[t] = -1
            elif v <= -0.0003: r[t] = 1
        sig[m] = pd.Series(r, dtype=float)                                   # each asset trades its OWN funding signal
    return run_crypto(sig, 3)


def al4():
    s = pd.read_csv(ALT / "stablecoins.csv", parse_dates=["date"]).set_index("date").stable_usd; sig = {}
    for D in pd.date_range("2021-12-06", "2026-09-30", freq="W-MON"):
        a, b = D - pd.Timedelta(days=29), D - pd.Timedelta(days=1)
        if a in s.index and b in s.index and s[b] / s[a] - 1 >= 0.02: sig[D] = 1
    return run_crypto(pd.Series(sig), 7)


def al5():
    d = ME.load("XAUUSD"); b, a = ME.at(d, "hm", 1559, "bo", "date"), ME.at(d, "hm", 1559, "ao", "date"); idx = b.index.intersection(a.index).sort_values(); b, a = b[idx], a[idx]
    y = pd.read_csv("D:/finance/data_macro/DFII10.csv", parse_dates=["observation_date"]).dropna().set_index("observation_date").iloc[:, 0].astype(float)
    r, i = {}, 0
    while i < len(idx) - 6:
        D = idx[i]; prior = y[y.index < D]
        if len(prior) > 6:
            ch = (prior.iat[-1] - prior.iat[-6]) * 100                      # bp
            s = 1 if ch <= -10 else (-1 if ch >= 10 else 0)
            if s:
                j = i + 5
                r[D] = ((b.iloc[j] / a.iloc[i] - 1) if s > 0 else (b.iloc[i] / a.iloc[j] - 1)) * 1e4; i = j + 1; continue
        i += 1
    return pd.Series(r)


def win(s, w): return s[(s.index >= w[0]) & (s.index <= w[1])]
def one(s): return dict(n=len(s), mean=s.mean() if len(s) else np.nan, t=s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan)


if __name__ == "__main__":
    S = {"AL1_fear_buy": al1(), "AL2_greed_sell": al2(), "AL3_funding": al3(), "AL4_stablecoins": al4(), "AL5_real_yield_gold": al5()}
    if os.environ.get("AL") == "dry":                                   # counts only, no return statistic is printed
        for k, s in S.items(): print(k, "obs", len(s), "DEV", len(win(s, DEV)), "VAL", len(win(s, VAL)), "HOLD", len(win(s, HOLD)))
    if os.environ.get("AL") == "run":
        rows = []
        for k, s in S.items():
            fl = 15.0 if k.startswith("AL5") else 40.0; d, v = one(win(s, DEV)), one(win(s, VAL)); acc = bool(d["n"] >= 30 and d["mean"] >= fl and d["t"] >= 1.65 and v["mean"] > 0)
            row = dict(trial=k, dev_n=d["n"], dev_bp=round(d["mean"], 1), dev_t=round(d["t"], 2), val_n=v["n"], val_bp=round(v["mean"], 1), val_t=round(v["t"], 2), accepted=acc)
            if acc: h = one(win(s, HOLD)); row.update(hold_n=h["n"], hold_bp=round(h["mean"], 1), PASS=bool(h["mean"] > 0))
            rows.append(row)
        txt = pd.DataFrame(rows).to_string(index=False); print(txt); open(os.path.join(os.path.dirname(__file__), "ALT_DATA_RESULT.txt"), "w").write(txt)
