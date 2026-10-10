"""Four classic technical-analysis rules on 1-minute BTCUSD (MT5 broker bars), exactly as registered in PREREG_BTC_M1_TA.md.
   python -m mt5broker.ea_research.btc_m1_ta --smoke     mechanics check on Dec 2022 (prints trades; not used for any decision)
   python -m mt5broker.ea_research.btc_m1_ta --trials    B1..B4 on DEV, VAL, POOL, appended to LEDGER.csv
   python -m mt5broker.ea_research.btc_m1_ta --holdout B1 [B2 ..]   the one-time 2026 look for rules that passed DEV and VAL
Signals at the bid close of bar k, fills at the open of bar k+1 (ask for longs, bid for shorts) with 2 bp slippage, stops intrabar, stop first."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
SLIP = 2.0e-4
START = "2022-04-01"
PERIODS = {"SMOKE": ("2022-12-01", "2022-12-07"), "DEV": ("2022-04-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "POOL": ("2022-04-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def epoch(day: str) -> int:
    return int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp())


def load():
    d = pd.read_parquet(DATA / "BTCUSD_M1_rates.parquet").sort_values("t"); d = d[d.t >= epoch(START)].reset_index(drop=True); return d


def indicators(d: pd.DataFrame) -> dict:
    c, h, l = d.bc, d.bh, d.bl; pc = c.shift(1); tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    sma, sd = c.rolling(60).mean(), c.rolling(60).std()
    e20, e100 = c.ewm(span=20, adjust=False).mean(), c.ewm(span=100, adjust=False).mean()
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean(); rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    return dict(atr=tr.rolling(60).mean().shift(1).to_numpy(), hh=h.rolling(120).max().shift(1).to_numpy(), ll=l.rolling(120).min().shift(1).to_numpy(), z=((c - sma) / sd).to_numpy(), e20=e20.to_numpy(), e100=e100.to_numpy(), rsi=rsi.to_numpy())


def run(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    t = d.t.to_numpy("int64"); bo, bh, bl, bc, ao, ah, al, ac, sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "sp")); n = len(d); I = indicators(d)
    atr, hh, ll, z, e20, e100, rsi = (I[k] for k in ("atr", "hh", "ll", "z", "e20", "e100", "rsi"))
    sig = np.zeros(n, dtype=np.int8)
    if rule == "B1":
        sig[(bc > hh) & np.isfinite(hh)] = 1; sig[(bc < ll) & np.isfinite(ll)] = -1; cool, tmax, stop_k, trail = 30, 120, 1.0, True
    elif rule == "B2":
        sig[z <= -3.0] = 1; sig[z >= 3.0] = -1; cool, tmax, stop_k, trail = 10, 45, 1.5, False
    elif rule == "B3":
        cu = (e20 > e100) & (np.roll(e20, 1) <= np.roll(e100, 1)); cd = (e20 < e100) & (np.roll(e20, 1) >= np.roll(e100, 1)); cu[0] = cd[0] = False; sig[cu] = 1; sig[cd] = -1; cool, tmax, stop_k, trail = 10, 10 ** 9, 2.0, False
    else:
        sig[rsi <= 15] = 1; sig[rsi >= 85] = -1; cool, tmax, stop_k, trail = 10, 30, 1.5, False
    gap_ok = np.r_[(t[1:] - t[:-1]) <= 120, False]; sig[~(gap_ok & np.isfinite(atr) & (atr > 0))] = 0
    idx = np.flatnonzero(sig); rows = []; free_from = 0; T, BO, BH, BL, BC, AO, AH, AL, AC, SP, ATR, Z, E20, E100, RSI = (x.tolist() if isinstance(x, np.ndarray) else x for x in (t, bo, bh, bl, bc, ao, ah, al, ac, sp, atr, z, e20, e100, rsi))
    for k in idx.tolist():
        if k < free_from or k + 1 >= n:
            continue
        s = int(sig[k]); e = k + 1; entry = (AO[e] * (1 + SLIP)) if s > 0 else (BO[e] * (1 - SLIP)); R = stop_k * ATR[k] * 7.745966692; mid = 0.5 * (BO[e] + AO[e]); stop = mid - s * R; ext = BC[e - 1] if s > 0 else AC[e - 1]; ex = None; why = ""; j = e       # AMENDMENT 1: stops sized to the hold horizon (S = ATR60 x sqrt(60)), measured from the mid
        sp_in = SP[e]
        while j < n:
            if s > 0 and BL[j] <= stop:
                ex = min(stop, BO[j]) * (1 - SLIP) if j > e else stop * (1 - SLIP); why = "stop"; break
            if s < 0 and AH[j] >= stop:
                ex = max(stop, AO[j]) * (1 + SLIP) if j > e else stop * (1 + SLIP); why = "stop"; break
            if trail:
                ext = max(ext, BC[j]) if s > 0 else min(ext, AC[j]); tr_ = ext - s * R; stop = max(stop, tr_) if s > 0 else min(stop, tr_)
            held = j - e + 1; ext_sig = False
            if rule == "B2":
                ext_sig = (s > 0 and Z[j] >= 0) or (s < 0 and Z[j] <= 0)
            elif rule == "B3":
                ext_sig = held >= 30 and ((s > 0 and E20[j] < E100[j]) or (s < 0 and E20[j] > E100[j]))
            elif rule == "B4":
                ext_sig = (s > 0 and RSI[j] >= 50) or (s < 0 and RSI[j] <= 50)
            if ext_sig or held >= tmax:
                if j + 1 < n:
                    ex = (BO[j + 1] * (1 - SLIP)) if s > 0 else (AO[j + 1] * (1 + SLIP)); why = "signal" if ext_sig else "time"; j = j + 1
                else:
                    ex = BC[j]; why = "end"
                break
            j += 1
        if ex is None:
            break
        pnl = s * (ex - entry); sp_out = SP[min(j, n - 1)]
        rows.append(dict(t_in=T[e], t_out=T[min(j, n - 1)], side=s, entry=entry, exit=ex, bp=pnl / entry * 1e4, gross_bp=(pnl + 0.5 * (sp_in + sp_out) + SLIP * (entry + ex)) / entry * 1e4, why=why, day=T[min(j, n - 1)] // 86400, hold_s=T[min(j, n - 1)] - T[e], bars=j - e)); free_from = j + cool
    return pd.DataFrame(rows)


def stats(X: pd.DataFrame, d: pd.DataFrame, a: str, b: str) -> dict:
    t0, t1 = epoch(a), epoch(b) + 86400; X = X[(X.t_in >= t0) & (X.t_in < t1)]; dd = d.t.to_numpy("int64") // 86400; days = np.unique(dd[(dd >= t0 // 86400) & (dd < t1 // 86400)])
    if not len(X):
        return dict(days=len(days), trades=0, mean=float("nan"), gross=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), net=0.0, sub1m=float("nan"))
    s = pd.Series(0.0, index=days); g = X.groupby("day").bp.sum(); ix = g.index.intersection(s.index); s.loc[ix] += g.loc[ix]; e = s.to_numpy(); w, l_ = X.bp[X.bp > 0].sum(), -X.bp[X.bp <= 0].sum()
    return dict(days=len(days), trades=len(X), mean=float(X.bp.mean()), gross=float(X.gross_bp.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))) if e.std(ddof=1) > 0 else float("nan"), win=float((X.bp > 0).mean()), net=float(X.bp.sum()), sub1m=float((X.hold_s < 60).mean()))


def fmt(tag, s):
    return f"{tag:16s} days {s['days']:4d} trades {s['trades']:6d} | net {s['mean']:+7.2f} bp/trade (mid-to-mid gross {s['gross']:+7.2f}) | PF {s['pf']:5.2f} | daily t {s['t']:+6.2f} | win {100*s['win']:4.1f}% | <1min {100*s['sub1m']:4.1f}%"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},btc_m1_ta,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['mean']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", nargs="*")
    a = ap.parse_args(); d = load()
    if a.smoke:
        pd.set_option("display.width", 200)
        for r in ("B1", "B2", "B3", "B4"):
            X = run(d, r); t0, t1 = epoch(PERIODS["SMOKE"][0]), epoch(PERIODS["SMOKE"][1]) + 86400; Y = X[(X.t_in >= t0) & (X.t_in < t1)].copy(); Y["in"] = pd.to_datetime(Y.t_in, unit="s").dt.strftime("%m-%d %H:%M")
            print(f"--- {r}: {len(X)} trades over the whole sample; first trades of {PERIODS['SMOKE'][0]}..{PERIODS['SMOKE'][1]}"); print(Y[["in", "side", "entry", "exit", "bp", "gross_bp", "bars", "why"]].head(6).round(2).to_string())
    if a.trials:
        for r in ("B1", "B2", "B3", "B4"):
            X = run(d, r)
            for per in ("DEV", "VAL", "POOL"):
                s = stats(X, d, *PERIODS[per]); print(fmt(f"{r} {per}", s), flush=True); ledger(r, per, s, "BTCUSD+ M1, bp net of spread and 2 bp slippage")
    if a.holdout:
        for r in a.holdout:
            s = stats(run(d, r), d, *PERIODS["HOLD"]); print(fmt(f"{r} HOLD-OUT 2026", s)); ledger(r, "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
