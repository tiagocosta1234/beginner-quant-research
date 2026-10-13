"""Rule I1: the previous-close-to-10:00 NY return predicts the last 30 minutes (NSDQ, SP, DOW), exactly as registered in PREREG_INDEX_INTRADAY_MOM.md.
   python -m forex.ea_research.index_intraday_mom --smoke | --trials | --holdout
Server clock (Europe/Athens) -> New York with real time zones; fills at the open of the 15:30 and 16:00 NY bars, ask for longs / bid for shorts, 0.12 bp slippage per fill."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
SLIP = 0.12e-4
NAMES = ["NSDQ", "SP", "DOW"]
PERIODS = {"SMOKE": ("2023-03-06", "2023-03-17"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def trades_for(name: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet", columns=["t", "bo", "bc", "ao", "sp"]).sort_values("t")
    ny = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("America/New_York")
    d = d.assign(date=ny.dt.date, hm=ny.dt.hour * 100 + ny.dt.minute); d = d[d.hm.isin([959, 1530, 1559, 1600])].dropna(subset=["date"])
    P = {hm: d[d.hm == hm].drop_duplicates("date").set_index("date") for hm in (959, 1530, 1559, 1600)}
    dates = sorted(set(P[959].index) & set(P[1530].index) & set(P[1600].index)); prev_dates = sorted(P[1559].index); rows = []
    for D in dates:
        prev = [x for x in prev_dates if x < D]
        if not prev:
            continue
        pd_ = prev[-1]
        if (D - pd_).days > 4:
            continue
        r1 = P[959].loc[D, "bc"] / P[1559].loc[pd_, "bc"] - 1
        if r1 == 0:
            continue
        s = 1 if r1 > 0 else -1; a, b = P[1530].loc[D], P[1600].loc[D]
        entry = a.ao * (1 + SLIP) if s > 0 else a.bo * (1 - SLIP)
        ex = (b.bo * (1 - SLIP)) if s > 0 else ((b.bo + b.sp) * (1 + SLIP)); pnl = s * (ex - entry)           # exit at the 16:00 bar's open: bid for a long, ask (= bid + spread) for a short
        rows.append(dict(name=name, date=pd.Timestamp(D), side=s, r1_bp=r1 * 1e4, entry=entry, exit=ex, bp=pnl / entry * 1e4, gross_bp=(pnl + 0.5 * (a.sp + b.sp) + SLIP * (entry + ex)) / entry * 1e4))
    return pd.DataFrame(rows)


def stats(T: pd.DataFrame, a: str, b: str) -> dict:
    X = T[(T.date >= pd.Timestamp(a)) & (T.date <= pd.Timestamp(b))]
    if not len(X):
        return dict(days=0, trades=0, mean=float("nan"), gross=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), net=0.0, per="", npos=0)
    day = X.groupby("date").bp.mean(); w, l_ = X.bp[X.bp > 0].sum(), -X.bp[X.bp <= 0].sum(); per = X.groupby("name").bp.mean()
    return dict(days=len(day), trades=len(X), mean=float(X.bp.mean()), gross=float(X.gross_bp.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(day.mean() / (day.std(ddof=1) / np.sqrt(len(day)))), win=float((X.bp > 0).mean()), net=float(X.bp.sum()), per=" ".join(f"{k} {v:+.2f}" for k, v in per.items()), npos=int((per > 0).sum()))


def fmt(tag, s):
    return f"{tag:18s} days {s['days']:4d} trades {s['trades']:5d} | net {s['mean']:+6.2f} bp/trade (mid-to-mid gross {s['gross']:+6.2f}) | PF {s['pf']:5.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | per index: {s['per']}"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},index_intraday_mom,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['mean']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    T = pd.concat([trades_for(n) for n in NAMES], ignore_index=True)
    if a.smoke:
        pd.set_option("display.width", 200); X = T[(T.date >= pd.Timestamp(PERIODS["SMOKE"][0])) & (T.date <= pd.Timestamp(PERIODS["SMOKE"][1])) & (T.name == "NSDQ")]; print(X.round(2).to_string()); print(len(T), "trades in total; trades per index:", T.groupby("name").size().to_dict())
    if a.trials:
        for per in ("DEV", "VAL", "POOL"):
            s = stats(T, *PERIODS[per]); print(fmt(f"I1 {per}", s), flush=True); ledger("I1", per, s, "NSDQ SP DOW pooled; " + s["per"])
    if a.holdout:
        s = stats(T, *PERIODS["HOLD"]); print(fmt("I1 HOLD-OUT 2026", s)); ledger("I1", "HOLD", s, "one-time look; " + s["per"])


if __name__ == "__main__":
    main()
