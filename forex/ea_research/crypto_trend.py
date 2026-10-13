"""Daily trend following on MT5 broker's crypto CFDs, exactly as registered in PREREG_CRYPTO_TREND.md.
   python -m forex.ea_research.crypto_trend --check                 data completeness (days, bars per day) for the four symbols
   python -m forex.ea_research.crypto_trend --trials                C1..C6 on BTCUSD+ in DEV and VAL, appended to LEDGER.csv
   python -m forex.ea_research.crypto_trend --replicate             C1 on ETH / LTC / XRP over 2022-02..2025-12 (only if C1 passed DEV and VAL)
   python -m forex.ea_research.crypto_trend --holdout               the one-time 2026 look for C1
Server day = calendar day of the MT5 broker server clock. Returns per unit of notional; a flip costs the day's opening spread + 4 bp."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
SLIP = 4e-4
PERIODS = {"DEV": ("2022-02-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30"), "REPL": ("2022-02-01", "2025-12-31")}
BASE = dict(ma=50, long_only=False, atr_stop=0.0, volt=False)
TRIALS = {"C1": BASE, "C2": {**BASE, "ma": 20}, "C3": {**BASE, "ma": 100}, "C4": {**BASE, "long_only": True}, "C5": {**BASE, "atr_stop": 3.0}, "C6": {**BASE, "volt": True}}


def daily(name: str) -> pd.DataFrame:
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet").sort_values("t"); d["day"] = d.t // 86400
    g = d.groupby("day"); o = g.bo.first(); c = g.bc.last(); h = g.bh.max(); l = g.bl.min(); n = g.t.size(); sp0 = g.apply(lambda x: x.sp.iloc[:5].mean(), include_groups=False)
    D = pd.DataFrame({"o": o, "h": h, "l": l, "c": c, "n": n, "sp0": sp0}); D.index = pd.to_datetime(D.index, unit="D"); return D[D.n >= 60]


def positions_returns(D: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    c, o, h, l = D.c.to_numpy(), D.o.to_numpy(), D.h.to_numpy(), D.l.to_numpy(); n = len(D); ma = pd.Series(c).rolling(cfg["ma"]).mean().to_numpy()
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.r_[c[0], c[:-1]]), np.abs(l - np.r_[c[0], c[:-1]]))); atr = pd.Series(tr).rolling(14).mean().to_numpy()
    sig = np.zeros(n)                                                                  # signal decided at the close of t-1 for day t
    for t in range(1, n):
        if np.isnan(ma[t - 1]): continue
        s = 1 if c[t - 1] > ma[t - 1] else -1
        sig[t] = 0 if (cfg["long_only"] and s < 0) else s
    ret = np.zeros(n); side = np.zeros(n); flips = np.zeros(n); prev = 0.0; entry_hh = None; stopped_sign = 0
    for t in range(1, n):
        want = sig[t]; cost = 0.0
        if cfg["atr_stop"] and prev != 0 and not np.isnan(atr[t - 1]):                  # trailing stop on the held side, checked on the day's range
            hh = entry_hh if entry_hh is not None else c[t - 1]
            stop = hh - prev * cfg["atr_stop"] * atr[t - 1] if prev > 0 else hh + cfg["atr_stop"] * atr[t - 1]
            hit = (l[t] <= stop) if prev > 0 else (h[t] >= stop)
            if hit:
                px = (min(stop, o[t]) if prev > 0 else max(stop, o[t])); r_stop = prev * (px / c[t - 1] - 1) - (D.sp0.iloc[t] / px + SLIP / 2)
                ret[t] = r_stop; side[t] = 0; prev = 0.0; stopped_sign = int(want); entry_hh = None; flips[t] = 1; continue
        if cfg["atr_stop"] and prev == 0 and stopped_sign != 0:
            if want != stopped_sign and want != 0: stopped_sign = 0
            else: want = 0
        if want == prev:
            ret[t] = prev * (c[t] / c[t - 1] - 1); side[t] = prev
            if prev != 0 and cfg["atr_stop"]: entry_hh = max(entry_hh, c[t]) if prev > 0 else min(entry_hh, c[t])
        else:
            r_old = prev * (o[t] / c[t - 1] - 1) if prev != 0 else 0.0; r_new = want * (c[t] / o[t] - 1) if want != 0 else 0.0
            cost = (D.sp0.iloc[t] / o[t] + SLIP) if (prev != 0 and want != 0) else ((D.sp0.iloc[t] / (2 * o[t]) + SLIP / 2))
            ret[t] = r_old + r_new - cost; side[t] = want; flips[t] = 1; prev = want; entry_hh = c[t] if want != 0 else None
    out = pd.DataFrame({"ret": ret, "side": side, "flip": flips}, index=D.index)
    if cfg["volt"]:
        sd = pd.Series(np.r_[0, np.diff(np.log(c))]).rolling(20).std().shift(1).to_numpy(); out["volw"] = np.where(np.isnan(sd) | (sd <= 0), np.nan, 1.0 / sd)
    return out


def period_stats(R: pd.DataFrame, a: str, b: str, volnorm: float | None = None) -> dict:
    r = R.loc[a:b]; x = r.ret.to_numpy()
    if volnorm is not None: x = x * (r.volw.to_numpy() / volnorm); x = np.nan_to_num(x)
    n = len(x); m, s = x.mean(), x.std(ddof=1); cum = np.cumsum(x); dd = float((np.maximum.accumulate(np.r_[0, cum])[1:] - cum).max())
    return dict(days=n, flips=int(r.flip.sum()), mean_bp=float(m * 1e4), t=float(m / (s / np.sqrt(n))) if s > 0 else float("nan"), sharpe=float(m / s * np.sqrt(365)) if s > 0 else float("nan"), cum=float(cum[-1]), maxdd=dd, win=float((x > 0).mean()))


def fmt(tag, s):
    return f"{tag:34s} days {s['days']:4d} flips {s['flips']:3d} | mean {s['mean_bp']:+6.2f} bp/day | daily t {s['t']:+5.2f} | Sharpe {s['sharpe']:+5.2f} | cum {100*s['cum']:+7.1f}% | max DD {100*s['maxdd']:5.1f}%"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},crypto_trend,{trial},{period},{s['days']},{s['flips']},{s['cum']*100:.2f},{s['mean_bp']:.3f},,{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); [ap.add_argument(f"--{k}", action="store_true") for k in ("check", "trials", "replicate", "holdout")]; a = ap.parse_args()
    if a.check:
        for nm in ("BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"):
            D = daily(nm); print(f"{nm}: {len(D)} days {D.index[0].date()}..{D.index[-1].date()} | bars/day median {int(D.n.median())} min {int(D.n.min())} | weekend days {int((D.index.weekday >= 5).sum())} | open spread median {100*float((D.sp0/D.o).median()):.3f}% | close {D.c.iloc[0]:,.0f} -> {D.c.iloc[-1]:,.0f}")
    if a.trials:
        D = daily("BTCUSD"); volnorm = None
        Rb = positions_returns(D, TRIALS["C6"]); dev = Rb.loc[PERIODS["DEV"][0]:PERIODS["DEV"][1]]; volnorm = float(np.nanmean(dev.volw))
        for name, cfg in TRIALS.items():
            R = positions_returns(D, cfg)
            for per in ("DEV", "VAL"):
                s = period_stats(R, *PERIODS[per], volnorm if cfg["volt"] else None); print(fmt(f"{name} BTC {per} {({k: v for k, v in cfg.items() if cfg[k] != BASE[k]} or 'primary')}", s), flush=True); ledger(name, per, s, "BTCUSD+ " + str({k: v for k, v in cfg.items() if cfg[k] != BASE[k]}).replace(",", ";"))
    if a.replicate:
        for nm in ("ETHUSD", "LTCUSD", "XRPUSD"):
            R = positions_returns(daily(nm), TRIALS["C1"]); s = period_stats(R, *PERIODS["REPL"]); print(fmt(f"C1 {nm} 2022-02..2025-12", s), flush=True); ledger("C1", "REPL2022-25", s, f"replication {nm}+")
    if a.holdout:
        R = positions_returns(daily("BTCUSD"), TRIALS["C1"]); s = period_stats(R, *PERIODS["HOLD"]); print(fmt("C1 BTC HOLD-OUT 2026", s)); ledger("C1", "HOLD", s, "BTCUSD+ one-time look")


if __name__ == "__main__":
    main()
