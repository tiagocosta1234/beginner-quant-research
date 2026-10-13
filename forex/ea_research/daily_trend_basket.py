"""Rule T1: vol-scaled daily trend basket (28 FX + gold + NSDQ/SP/DOW), exactly as registered in PREREG_DAILY_TREND_BASKET.md.
   python -m forex.ea_research.daily_trend_basket --smoke | --trials | --holdout
Observation / trading price: the bid open of the 22:00 server-time M1 bar; no look-ahead; costs = half the bar's spread + slippage per unit traded."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
FX = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
      "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
OTHERS = ["XAUUSD", "NSDQ", "SP", "DOW"]
SLIP_BP = {**{n: 0.2 for n in FX}, "XAUUSD": 0.4, "NSDQ": 0.12, "SP": 0.12, "DOW": 0.12}
LOOKS, VOL_N, TARGET = (20, 60, 120), 60, 0.002
PERIODS = {"SMOKE": ("2023-01-02", "2023-01-31"), "DEV": ("2022-06-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-06-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def observe(name: str):
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet", columns=["t", "bo", "sp"]); d = d[d.t % 86400 == 79200].copy(); d["date"] = pd.to_datetime(d.t // 86400 * 86400, unit="s")
    d = d.drop_duplicates("date").set_index("date"); return d.bo, d.sp


def build():
    P, S = {}, {}
    for n in FX + OTHERS:
        P[n], S[n] = observe(n)
    P = pd.DataFrame(P).sort_index(); S = pd.DataFrame(S).reindex(P.index); idx = P.index[P[FX].notna().sum(axis=1) >= 20]; P = P.loc[idx].ffill(limit=5); S = S.loc[idx].ffill(limit=5)
    return P, S


def basket(P: pd.DataFrame, S: pd.DataFrame, cols: list[str]):
    P, S = P[cols], S[cols]; ret_past = P / P.shift(1) - 1; r_next = P.shift(-1) / P - 1
    sig = sum(np.sign(P / P.shift(L) - 1) for L in LOOKS) / len(LOOKS); sigma = ret_past.rolling(VOL_N).std().clip(lower=0.001); w = (sig * TARGET / sigma).where(sig.notna() & sigma.notna(), 0.0)
    slip = pd.Series({n: SLIP_BP[n] * 1e-4 for n in cols}); cost_unit = (S / 2 / P).fillna(0.0) + slip; turn = (w - w.shift(1).fillna(0.0)).abs(); cost = (turn * cost_unit).sum(axis=1)
    gross = (w * r_next).sum(axis=1, min_count=1); net = (gross - cost).where(gross.notna()); return pd.DataFrame({"net": net, "gross": gross, "turn": turn.sum(axis=1)}).dropna(subset=["net"])


def stats(R: pd.DataFrame, a: str, b: str) -> dict:
    X = R[(R.index >= pd.Timestamp(a)) & (R.index <= pd.Timestamp(b))]; n = len(X)
    if n < 20:
        return dict(days=n, sharpe=float("nan"), t=float("nan"), mean_bp=float("nan"), mdd=float("nan"), turn=float("nan"), gsharpe=float("nan"))
    m, s = X.net.mean(), X.net.std(ddof=1); g, gs = X.gross.mean(), X.gross.std(ddof=1); cum = X.net.cumsum(); mdd = float((cum.cummax() - cum).max())
    return dict(days=n, sharpe=float(m / s * np.sqrt(252)), t=float(m / (s / np.sqrt(n))), mean_bp=float(m * 1e4), mdd=mdd * 100, turn=float(X.turn.mean()), gsharpe=float(g / gs * np.sqrt(252)))


def fmt(tag, s):
    return f"{tag:22s} days {s['days']:4d} | net Sharpe {s['sharpe']:+5.2f} | daily t {s['t']:+5.2f} | mean {s['mean_bp']:+6.2f} bp/day | max DD {s['mdd']:5.1f}% of capital (sum of daily R) | turnover {s['turn']:5.2f}/day | gross Sharpe {s['gsharpe']:+5.2f}"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},daily_trend_basket,{trial},{period},{s['days']},,,{s['mean_bp']:.3f},,{s['t']:.2f},{s['sharpe']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); a = ap.parse_args()
    P, S = build(); R = basket(P, S, FX + OTHERS); Rx = basket(P, S, FX + [c for c in OTHERS if c != "XAUUSD"])
    if a.smoke:
        print("dates", P.index[0].date(), P.index[-1].date(), len(P), "instruments", P.shape[1]); print(R.loc["2023-01-02":"2023-01-12"].round(6).to_string()); print(fmt("SMOKE Jan 2023", stats(R, *PERIODS["SMOKE"])))
    if a.trials:
        for per in ("DEV", "VAL", "POOL"):
            s = stats(R, *PERIODS[per]); sx = stats(Rx, *PERIODS[per]); print(fmt(f"T1 {per}", s), flush=True); print(fmt(f"   ex-gold {per}", sx), flush=True); ledger("T1", per, s, f"32 instruments, Sharpe in the last column; ex-gold Sharpe {sx['sharpe']:.2f}")
    if a.holdout:
        s = stats(R, *PERIODS["HOLD"]); print(fmt("T1 HOLD-OUT 2026", s)); ledger("T1", "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
