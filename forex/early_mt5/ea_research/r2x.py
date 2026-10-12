"""R2X: the daily RSI(2) dip rule on DAX/NIKKEI/ASX and BTC/ETH (PREREG_R2X.md).   env R2X=dry|run"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from pathlib import Path
from mt5broker.ea_research import more_eas as ME, fincept_mt5_verify as V, dip_addon as DA, intraday_dip as ID

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
SPEC = {"DAX": ("Europe/Berlin", 1729), "NIKKEI": ("Asia/Tokyo", 1459), "ASX": ("Australia/Sydney", 1559), "BTCUSD": ("UTC", 2359), "ETHUSD": ("UTC", 2359)}
DEV, VAL, HOLD = ME.DEV, ME.VAL, ME.HOLD


def px(m):
    tz, hm = SPEC[m]; d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t"); d = d[(d.bo > 0) & (d.ao >= d.bo)]
    loc = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert(tz)
    d = d.assign(date=loc.dt.tz_localize(None).dt.normalize(), hm=loc.dt.hour * 100 + loc.dt.minute).dropna(subset=["date"])
    s = d[d.hm == hm].drop_duplicates("date").set_index("date"); return s.bo, s.ao


def trades(m):
    b, a = px(m); r2 = V.rsi(b); s200, s5 = b.rolling(200).mean(), b.rolling(5).mean(); out, i = [], 200
    while i < len(b) - 1:
        if r2.iat[i] < 10 and b.iat[i] > s200.iat[i]:
            e = i; j = i + 1
            while j < len(b) - 1 and not (b.iat[j] > s5.iat[j] or r2.iat[j] > 70 or j - e >= 5): j += 1
            out.append(dict(mkt=m, entry=b.index[e], exit=b.index[j], ret=b.iat[j] / a.iat[e] - 1)); i = j + 1
        else: i += 1
    return out


def summ(df, w, years):
    d = ID.win(df, w)
    if d.empty: return dict(trades=0, days=0, per_year=0.0, mean=np.nan, pf=np.nan, t=np.nan)
    g = ID.by_day(d); t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    return dict(trades=len(d), days=len(g), per_year=len(d) / years, mean=1e4 * g.mean(), pf=ID.pf(g), t=t)


if __name__ == "__main__":
    T = {m: pd.DataFrame(trades(m)) for m in SPEC}; G = {"R2X1_indices": ("DAX", "NIKKEI", "ASX"), "R2X2_crypto": ("BTCUSD", "ETHUSD")}
    if os.environ.get("R2X") == "dry":
        for g, ms in G.items(): df = pd.concat([T[m] for m in ms]); print(g, "trades", len(df), "DEV", len(ID.win(df, DEV)), "VAL", len(ID.win(df, VAL)), "HOLD", len(ID.win(df, HOLD)))
    if os.environ.get("R2X") == "run":
        us = pd.DataFrame(sum((V.ev1((m,))[0] for m in ("SP", "NSDQ", "DOW")), []), columns=["mkt", "entry", "exit", "ret"])
        os.environ["DA_Z"] = "1.5"; Tk, _ = DA.trades(); kd = np.array(sorted(set(pd.to_datetime(Tk.date))), dtype="datetime64[D]")
        lines = []
        for g, ms in G.items():
            df = pd.concat([T[m] for m in ms], ignore_index=True); d, v = summ(df, DEV, 3.0), summ(df, VAL, 1.0); acc = bool(d["days"] >= 30 and d["mean"] >= 30 and d["pf"] >= 1.3 and d["t"] >= 1.65 and v["mean"] > 0)
            lines.append(f"{g}\n  DEV 2022-24: {ID.f(d)}\n  VAL 2025   : {ID.f(v)}\n  indicative Sharpe (25k/trade): DEV {ID.sharpe(df, DEV):.2f} | VAL {ID.sharpe(df, VAL):.2f}\n  accepted: {acc}")
            if acc: h = summ(df, HOLD, 0.75); lines.append(f"  HOLD 2026  : {ID.f(h)} | pass: {bool(h['mean'] > 0)}")
            ev = pd.to_datetime(df.entry).values.astype("datetime64[D]"); ud = np.array(sorted(set(pd.to_datetime(us.entry))), dtype="datetime64[D]")
            ov = lambda arr: 100 * np.mean([np.any(np.abs((arr - e).astype(int)) <= 1) for e in ev]) if len(ev) else 0
            lines.append(f"  entry days within 1 day of a US RSI(2) day: {ov(ud):.0f}% | of a ManualDip signal day: {ov(kd):.0f}%\n  by market 2022-26 (trades, mean bp): " + str({m: (len(x), round(1e4 * x.ret.mean())) for m, x in ID.win(df, ('2022-01-01', '2026-09-30')).groupby('mkt')}) + "\n")
        allr = pd.concat([T[m] for m in SPEC] + [us], ignore_index=True)
        lines.append(f"Pooled with the US block (breadth): DEV Sharpe {ID.sharpe(allr, DEV):.2f} | VAL {ID.sharpe(allr, VAL):.2f}; US block alone DEV {ID.sharpe(us, DEV):.2f} | VAL {ID.sharpe(us, VAL):.2f}")
        txt = "\n".join(lines); print(txt); open(os.path.join(os.path.dirname(__file__), "R2X_RESULT.txt"), "w").write(txt)
