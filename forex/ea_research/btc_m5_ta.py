"""Four classic technical-analysis rules on 5-minute BTCUSD (MT5 broker bars built from M1), exactly as registered in PREREG_BTC_M5_TA.md.
   python -m forex.ea_research.btc_m5_ta --smoke     mechanics check on Dec 2022 (prints trades; not used for any decision)
   python -m forex.ea_research.btc_m5_ta --trials    C1..C4 on DEV, VAL, POOL, appended to LEDGER.csv
   python -m forex.ea_research.btc_m5_ta --holdout C1 [C2 ..]   the one-time 2026 look for rules that passed DEV and VAL
Signals at the bid close of bar k, fills at the open of bar k+1 (ask for longs, bid for shorts) with 2 bp slippage, stops intrabar, stop first."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_research.btc_m1_ta import epoch, stats, fmt, PERIODS, START

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
SLIP = 2.0e-4
SQ48 = 48 ** 0.5
PARAMS = {"C1": dict(cool=12, tmax=288, k=1.5, trail=True), "C2": dict(cool=6, tmax=36, k=2.0, trail=False), "C3": dict(cool=6, tmax=10 ** 9, k=2.0, trail=False), "C4": dict(cool=6, tmax=36, k=1.5, trail=False)}


def load5() -> pd.DataFrame:
    d = pd.read_parquet(DATA / "BTCUSD_M1_rates.parquet").sort_values("t"); d = d[d.t >= epoch(START)]; g = d.groupby(d.t // 300)
    b = pd.DataFrame({"bo": g.bo.first(), "bh": g.bh.max(), "bl": g.bl.min(), "bc": g.bc.last(), "ao": g.ao.first(), "ah": g.ah.max(), "al": g.al.min(), "ac": g.ac.last(), "sp": g.sp.mean()}); b["t"] = b.index.to_numpy() * 300; return b.reset_index(drop=True)


def indicators(d: pd.DataFrame) -> dict:
    c, h, l = d.bc, d.bh, d.bl; pc = c.shift(1); tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1); sma, sd = c.rolling(48).mean(), c.rolling(48).std()
    e24, e96 = c.ewm(span=24, adjust=False).mean(), c.ewm(span=96, adjust=False).mean()
    dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean(); rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    return dict(atr=tr.rolling(48).mean().shift(1).to_numpy(), hh=h.rolling(48).max().shift(1).to_numpy(), ll=l.rolling(48).min().shift(1).to_numpy(), z=((c - sma) / sd).to_numpy(), e24=e24.to_numpy(), e96=e96.to_numpy(), rsi=rsi.to_numpy())


def run(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    t = d.t.to_numpy("int64"); bo, bh, bl, bc, ao, ah, al, ac, sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "sp")); n = len(d); I = indicators(d)
    atr, hh, ll, z, e24, e96, rsi = (I[k] for k in ("atr", "hh", "ll", "z", "e24", "e96", "rsi")); P = PARAMS[rule]; cool, tmax, stop_k, trail = P["cool"], P["tmax"], P["k"], P["trail"]
    sig = np.zeros(n, dtype=np.int8)
    if rule == "C1":
        sig[(bc > hh) & np.isfinite(hh)] = 1; sig[(bc < ll) & np.isfinite(ll)] = -1
    elif rule == "C2":
        sig[z <= -2.5] = 1; sig[z >= 2.5] = -1
    elif rule == "C3":
        cu = (e24 > e96) & (np.roll(e24, 1) <= np.roll(e96, 1)); cd = (e24 < e96) & (np.roll(e24, 1) >= np.roll(e96, 1)); cu[0] = cd[0] = False; sig[cu] = 1; sig[cd] = -1
    else:
        sig[rsi <= 20] = 1; sig[rsi >= 80] = -1
    gap_ok = np.r_[(t[1:] - t[:-1]) <= 600, False]; sig[~(gap_ok & np.isfinite(atr) & (atr > 0))] = 0
    idx = np.flatnonzero(sig); rows = []; free_from = 0
    T, BO, BH, BL, BC, AO, AH, AL, AC, SP, ATR, Z, E24, E96, RSI = (x.tolist() if isinstance(x, np.ndarray) else x for x in (t, bo, bh, bl, bc, ao, ah, al, ac, sp, atr, z, e24, e96, rsi))
    for k in idx.tolist():
        if k < free_from or k + 1 >= n:
            continue
        s = int(sig[k]); e = k + 1; entry = (AO[e] * (1 + SLIP)) if s > 0 else (BO[e] * (1 - SLIP)); R = stop_k * ATR[k] * SQ48; mid = 0.5 * (BO[e] + AO[e]); stop = mid - s * R; ext = BC[e - 1] if s > 0 else AC[e - 1]; ex = None; why = ""; j = e; sp_in = SP[e]
        while j < n:
            if s > 0 and BL[j] <= stop:
                ex = min(stop, BO[j]) * (1 - SLIP) if j > e else stop * (1 - SLIP); why = "stop"; break
            if s < 0 and AH[j] >= stop:
                ex = max(stop, AO[j]) * (1 + SLIP) if j > e else stop * (1 + SLIP); why = "stop"; break
            if trail:
                ext = max(ext, BC[j]) if s > 0 else min(ext, AC[j]); tr_ = ext - s * R; stop = max(stop, tr_) if s > 0 else min(stop, tr_)
            held = j - e + 1; ext_sig = False
            if rule == "C2":
                ext_sig = (s > 0 and Z[j] >= 0) or (s < 0 and Z[j] <= 0)
            elif rule == "C3":
                ext_sig = held >= 24 and ((s > 0 and E24[j] < E96[j]) or (s < 0 and E24[j] > E96[j]))
            elif rule == "C4":
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
        pnl = s * (ex - entry); jj = min(j, n - 1); sp_out = SP[jj]
        rows.append(dict(t_in=T[e], t_out=T[jj], side=s, entry=entry, exit=ex, bp=pnl / entry * 1e4, gross_bp=(pnl + 0.5 * (sp_in + sp_out) + SLIP * (entry + ex)) / entry * 1e4, why=why, day=T[jj] // 86400, hold_s=T[jj] - T[e], bars=j - e)); free_from = j + cool
    return pd.DataFrame(rows)


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},btc_m5_ta,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['mean']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", nargs="*")
    a = ap.parse_args(); d = load5()
    if a.smoke:
        pd.set_option("display.width", 200)
        for r in ("C1", "C2", "C3", "C4"):
            X = run(d, r); t0, t1 = epoch(PERIODS["SMOKE"][0]), epoch(PERIODS["SMOKE"][1]) + 86400 * 7; Y = X[(X.t_in >= t0) & (X.t_in < t1)].copy(); Y["in"] = pd.to_datetime(Y.t_in, unit="s").dt.strftime("%m-%d %H:%M")
            print(f"--- {r}: {len(X)} trades over the whole sample; first trades of December 2022"); print(Y[["in", "side", "entry", "exit", "bp", "gross_bp", "bars", "why"]].head(5).round(2).to_string())
    if a.trials:
        for r in ("C1", "C2", "C3", "C4"):
            X = run(d, r)
            for per in ("DEV", "VAL", "POOL"):
                s = stats(X, d, *PERIODS[per]); print(fmt(f"{r} {per}", s), flush=True); ledger(r, per, s, "BTCUSD+ M5, bp net of spread and 2 bp slippage")
    if a.holdout:
        for r in a.holdout:
            s = stats(run(d, r), d, *PERIODS["HOLD"]); print(fmt(f"{r} HOLD-OUT 2026", s)); ledger(r, "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
