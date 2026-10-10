"""Trend-pullback rule H1 on five MT5, exactly as registered in PREREG_TREND_PULLBACK.md.
   python -m mt5broker.ea_research.trend_pullback --smoke      mechanics check on Dec 2021 gold (prints trades; not used for any decision)
   python -m mt5broker.ea_research.trend_pullback --trials      H1 on gold (DEV, VAL) and on NSDQ / SP / BTC / ETH (DEV, VAL, pooled 2022-25), appended to LEDGER.csv
   python -m mt5broker.ea_research.trend_pullback --holdout     the one-time 2026 look on gold (only if acceptance 1 and 2 held)
Server clock; M15 bars from M1; ATR of the previous 14 bars; costs: ask/bid from the bar spread + per-market slippage in basis points of the price; stop first inside a bar."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
SLIP_BP = {"XAUUSD": 0.4, "NSDQ": 0.12, "SP": 0.12, "BTCUSD": 2.0, "ETHUSD": 2.0}
PERIODS = {"SMOKE": ("2021-12-01", "2021-12-31"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
P = dict(trend_bars=16, ma_bars=96, pull_atr=0.5, stop_atr=2.0, trail_atr=3.0, max_bars=96, cool=4, atr_n=14)


def epoch(day: str) -> int:
    return int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp())


def bars(name: str):
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet").sort_values("t"); t = d.t.to_numpy("int64"); b15 = t // 900; b60 = t // 3600
    g = d.assign(b15=b15).groupby("b15"); m15 = pd.DataFrame({"o": g.bo.first(), "h": g.bh.max(), "l": g.bl.min(), "c": g.bc.last(), "sp": g.sp.mean()}); m15["t"] = m15.index.to_numpy() * 900
    h = d.assign(b60=b60).groupby("b60"); h1 = pd.DataFrame({"h": h.bh.max(), "l": h.bl.min(), "c": h.bc.last()}); h1["t"] = h1.index.to_numpy() * 3600; h1["atr"] = atr(h1)
    m15["atr"] = atr(m15); m15["h1atr"] = h1.atr.reindex((m15.t // 3600).values).to_numpy()
    return m15.reset_index(drop=True)


def atr(b: pd.DataFrame) -> pd.Series:
    pc = b.c.shift(1); tr = pd.concat([b.h - b.l, (b.h - pc).abs(), (b.l - pc).abs()], axis=1).max(axis=1); return tr.rolling(P["atr_n"]).mean().shift(1)         # ATR of the previous 14 bars


def simulate(m15: pd.DataFrame, name: str, a: str, b: str) -> pd.DataFrame:
    t0, t1 = epoch(a), epoch(b) + 86400; o, h, l, c, sp, ts, at, ha = (m15[k].to_numpy() for k in ("o", "h", "l", "c", "sp", "t", "atr", "h1atr")); n = len(m15); slip = SLIP_BP[name] * 1e-4
    ma = pd.Series(c).rolling(P["ma_bars"]).mean().to_numpy(); rows = []; pos = None; cool = -10; pend = 0
    for k in range(P["ma_bars"] + 20, n - 1):
        if ts[k] >= t1:
            break
        if pos is None and pend != 0 and ts[k] >= t0 and k - cool >= P["cool"]:
            s = pend; ent = (o[k] + sp[k] + o[k] * slip) if s > 0 else (o[k] - o[k] * slip); R = P["stop_atr"] * ha[k - 1]
            if np.isfinite(R) and R > 0:
                pos = dict(s=s, entry=ent, stop=ent - s * R, R=R, ext=ent, k0=k, t_in=int(ts[k]), ha=ha[k - 1])
        pend = 0
        if pos is not None:
            s = pos["s"]; ex = None
            if s > 0 and l[k] <= pos["stop"]: ex, why = min(pos["stop"], o[k]) - pos["stop"] * slip, "stop"
            elif s < 0 and h[k] + sp[k] >= pos["stop"]: ex, why = max(pos["stop"], o[k] + sp[k]) + pos["stop"] * slip, "stop"
            if ex is None:
                pos["ext"] = max(pos["ext"], c[k]) if s > 0 else min(pos["ext"], c[k]); tr = pos["ext"] - s * P["trail_atr"] * pos["ha"]; pos["stop"] = max(pos["stop"], tr) if s > 0 else min(pos["stop"], tr)
                if k - pos["k0"] + 1 >= P["max_bars"]:
                    ex, why = ((o[k + 1] - o[k + 1] * slip) if s > 0 else (o[k + 1] + sp[k + 1] + o[k + 1] * slip)), "time"
            if ex is not None:
                pnl = s * (ex - pos["entry"]); rows.append(dict(t_in=pos["t_in"], t_out=int(ts[k]), side=s, entry=pos["entry"], exit=ex, pnl=pnl, bp=pnl / pos["entry"] * 1e4, r=pnl / pos["R"], why=why, day=int(ts[k] // 86400))); pos = None; cool = k
        if pos is None and np.isfinite(at[k]) and np.isfinite(ma[k]) and k - cool >= P["cool"]:
            ret4 = c[k] - c[k - P["trend_bars"]]; s = 1 if (ret4 > 0 and c[k] > ma[k]) else (-1 if (ret4 < 0 and c[k] < ma[k]) else 0)
            if s != 0 and s * (c[k] - o[k]) <= -P["pull_atr"] * at[k]:
                pend = s
    T = pd.DataFrame(rows)
    return T[(T.t_in >= t0) & (T.t_in < t1)].reset_index(drop=True) if len(T) else T


def stats(T: pd.DataFrame, m15: pd.DataFrame, a: str, b: str) -> dict:
    d0, d1 = epoch(a) // 86400, epoch(b) // 86400; dd = m15.t.to_numpy() // 86400; days = np.unique(dd[(dd >= d0) & (dd <= d1)])
    if not len(T):
        return dict(days=len(days), trades=0, mean=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), r=float("nan"), net=0.0)
    s = pd.Series(0.0, index=days); g = T.groupby("day").bp.sum(); ix = g.index.intersection(s.index); s.loc[ix] += g.loc[ix]; e = s.to_numpy(); w, l_ = T.bp[T.bp > 0].sum(), -T.bp[T.bp <= 0].sum()
    return dict(days=len(days), trades=len(T), mean=float(T.bp.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))) if e.std(ddof=1) > 0 else float("nan"), win=float((T.bp > 0).mean()), r=float(T.r.mean()), net=float(T.bp.sum()))


def fmt(tag, s):
    return f"{tag:26s} days {s['days']:4d} trades {s['trades']:4d} | mean {s['mean']:+7.1f} bp/trade ({s['r']:+5.2f} R) | PF {s['pf']:5.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | net {s['net']:+9,.0f} bp"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},trend_pullback,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['mean']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser()
    for k in ("smoke", "trials", "holdout"):
        ap.add_argument(f"--{k}", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        m = bars("XAUUSD"); T = simulate(m, "XAUUSD", *PERIODS["SMOKE"]); T["in"] = pd.to_datetime(T.t_in, unit="s").dt.strftime("%m-%d %H:%M"); T["out"] = pd.to_datetime(T.t_out, unit="s").dt.strftime("%m-%d %H:%M"); pd.set_option("display.width", 200)
        print(T[["in", "out", "side", "entry", "exit", "pnl", "r", "why"]].round(2).to_string()); print(fmt("H1 gold SMOKE Dec 2021", stats(T, m, *PERIODS["SMOKE"])))
    if a.trials:
        for name in ("XAUUSD", "NSDQ", "SP", "BTCUSD", "ETHUSD"):
            m = bars(name)
            for per in ("DEV", "VAL", "POOL"):
                T = simulate(m, name, *PERIODS[per]); s = stats(T, m, *PERIODS[per]); print(fmt(f"H1 {name} {per}", s), flush=True); ledger("H1", per, s, name + "+")
    if a.holdout:
        m = bars("XAUUSD"); T = simulate(m, "XAUUSD", *PERIODS["HOLD"]); s = stats(T, m, *PERIODS["HOLD"]); print(fmt("H1 gold HOLD-OUT 2026", s)); ledger("H1", "HOLD", s, "XAUUSD+ one-time look")


if __name__ == "__main__":
    main()
