"""H1 Donchian breakout with a tight ATR stop and a chandelier trail on MT5 broker gold, exactly as registered in PREREG_GOLD_DONCHIAN.md.
   python -m forex.ea_research.gold_donchian --smoke        mechanics check on Dec 2021 (prints trades; not used for any decision)
   python -m forex.ea_research.gold_donchian --trials       G1..G6 in DEV and VAL, appended to LEDGER.csv
   python -m forex.ea_research.gold_donchian --holdout      the one-time 2026 look for G1
Server clock; P&L in USD per ounce (R = the initial stop distance); costs: ask/bid from the bar spread + 0.15 USD slippage on market entries and stop exits; stop first inside a bar."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5" / "XAUUSD_M1_rates.parquet"
LEDGER = HERE / "LEDGER.csv"
SLIP = 0.15
PERIODS = {"SMOKE": ("2021-12-01", "2021-12-31"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
BASE = dict(look=24, sl_atr=1.5, trail_atr=2.5, long_only=False, hours=None, max_bars=72)
TRIALS = {"G1": BASE, "G2": {**BASE, "look": 48}, "G3": {**BASE, "look": 12}, "G4": {**BASE, "sl_atr": 1.0, "trail_atr": 2.0}, "G5": {**BASE, "long_only": True}, "G6": {**BASE, "hours": (3, 19)}}


class Data:
    pass


def epoch(day: str) -> int:
    return int(dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc).timestamp())


def load() -> Data:
    d = pd.read_parquet(DATA).sort_values("t").reset_index(drop=True); D = Data()
    D.t = d.t.to_numpy("int64"); D.o, D.h, D.l, D.c, D.sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "sp")); D.n = len(d)
    hb = D.t // 3600; chg = np.r_[True, hb[1:] != hb[:-1]]; D.hs = np.nonzero(chg)[0]; D.he = np.r_[D.hs[1:], D.n]; D.hts = hb[D.hs] * 3600; D.K = len(D.hs)
    D.H1c = D.c[D.he - 1]; D.H1h = np.maximum.reduceat(D.h, D.hs); D.H1l = np.minimum.reduceat(D.l, D.hs)
    pc = np.r_[D.H1c[0], D.H1c[:-1]]; tr = np.maximum(D.H1h - D.H1l, np.maximum(np.abs(D.H1h - pc), np.abs(D.H1l - pc))); D.atr = pd.Series(tr).rolling(14).mean().to_numpy()
    return D


def simulate(D: Data, cfg: dict, a: str, b: str) -> pd.DataFrame:
    t0, t1 = epoch(a), epoch(b) + 86400; L = cfg["look"]; rows = []; pos = None; pending = 0
    for k in range(L + 15, D.K - 1):
        ts = D.hts[k]
        if ts >= t1:
            break
        lo, hi = D.hs[k], D.he[k]
        if pos is None and pending != 0:
            hrs = cfg["hours"]; sh = (ts // 3600) % 24
            if hrs is None or hrs[0] <= sh < hrs[1]:
                side = pending; atr = D.atr[k - 1]
                ent = (D.o[lo] + D.sp[lo] + SLIP) if side > 0 else (D.o[lo] - SLIP)
                pos = dict(side=side, entry=ent, stop=ent - side * cfg["sl_atr"] * atr, r=cfg["sl_atr"] * atr, atr=atr, ext=ent, k0=k, t_in=int(D.t[lo]))
        pending = 0
        if pos is not None:
            s = pos["side"]; ex = None
            if s > 0:
                m = D.l[lo:hi] <= pos["stop"]
                if m.any():
                    j = lo + int(np.argmax(m)); ex = min(pos["stop"], D.o[j]) - SLIP; xj = j; why = "stop"
            else:
                m = (D.h[lo:hi] + D.sp[lo:hi]) >= pos["stop"]
                if m.any():
                    j = lo + int(np.argmax(m)); ex = max(pos["stop"], D.o[j] + D.sp[j]) + SLIP; xj = j; why = "stop"
            if ex is None:
                c = D.H1c[k]; pos["ext"] = max(pos["ext"], c) if s > 0 else min(pos["ext"], c)
                tr = pos["ext"] - s * cfg["trail_atr"] * pos["atr"]; pos["stop"] = max(pos["stop"], tr) if s > 0 else min(pos["stop"], tr)
                if k - pos["k0"] + 1 >= cfg["max_bars"]:
                    j = D.hs[k + 1]; ex = (D.o[j] - SLIP) if s > 0 else (D.o[j] + D.sp[j] + SLIP); xj = j; why = "time"
            if ex is not None:
                pnl = s * (ex - pos["entry"])
                rows.append(dict(t_in=pos["t_in"], t_out=int(D.t[xj]), side=s, entry=pos["entry"], exit=ex, pnl=pnl, r=pnl / pos["r"], why=why, day=int(D.t[xj] // 86400))); pos = None
        if pos is None:
            c = D.H1c[k]; hh = D.H1h[k - L:k].max(); ll = D.H1l[k - L:k].min()
            if c > hh:
                pending = 1
            elif c < ll and not cfg["long_only"]:
                pending = -1
    T = pd.DataFrame(rows)
    if len(T):
        T = T[(T.t_in >= t0) & (T.t_in < t1)].reset_index(drop=True)
    return T


def stats(T: pd.DataFrame, D: Data, a: str, b: str) -> dict:
    d0, d1 = epoch(a) // 86400, epoch(b) // 86400; dd = D.t // 86400; days = np.unique(dd[(dd >= d0) & (dd <= d1)])
    if not len(T):
        return dict(days=len(days), trades=0, net=0.0, exp_r=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), avg_win=float("nan"), avg_loss=float("nan"))
    s = pd.Series(0.0, index=days); g = T.groupby("day").pnl.sum(); ix = g.index.intersection(s.index); s.loc[ix] += g.loc[ix]; e = s.to_numpy()
    w, l = T.pnl[T.pnl > 0].sum(), -T.pnl[T.pnl <= 0].sum()
    return dict(days=len(days), trades=len(T), net=float(T.pnl.sum()), exp_r=float(T.r.mean()), pf=float(w / l) if l > 0 else float("inf"), t=float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))) if e.std(ddof=1) > 0 else float("nan"),
                win=float((T.pnl > 0).mean()), avg_win=float(T.r[T.pnl > 0].mean()) if (T.pnl > 0).any() else float("nan"), avg_loss=float(T.r[T.pnl <= 0].mean()) if (T.pnl <= 0).any() else float("nan"))


def fmt(tag, s):
    return f"{tag:34s} days {s['days']:4d} trades {s['trades']:4d} net {s['net']:+9,.1f} USD/oz | exp {s['exp_r']:+5.2f} R | PF {s['pf']:5.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}% | avg win {s['avg_win']:+5.2f} R, avg loss {s['avg_loss']:+5.2f} R"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},gold_donchian,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['exp_r']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser()
    for k in ("smoke", "trials", "holdout"):
        ap.add_argument(f"--{k}", action="store_true")
    a = ap.parse_args(); D = load()
    if a.smoke:
        T = simulate(D, BASE, *PERIODS["SMOKE"]); pd.set_option("display.width", 220); T["in"] = pd.to_datetime(T.t_in, unit="s").dt.strftime("%m-%d %H:%M"); T["out"] = pd.to_datetime(T.t_out, unit="s").dt.strftime("%m-%d %H:%M")
        print(T[["in", "out", "side", "entry", "exit", "pnl", "r", "why"]].round(2).to_string()); print(fmt("G1 SMOKE Dec 2021 (mechanics only)", stats(T, D, *PERIODS["SMOKE"])))
    if a.trials:
        for name, cfg in TRIALS.items():
            for per in ("DEV", "VAL"):
                T = simulate(D, cfg, *PERIODS[per]); s = stats(T, D, *PERIODS[per]); diff = {k: v for k, v in cfg.items() if cfg[k] != BASE[k]}
                print(fmt(f"{name} {per} {diff or 'primary'}", s), flush=True); ledger(name, per, s, str(diff).replace(",", ";"))
    if a.holdout:
        T = simulate(D, BASE, *PERIODS["HOLD"]); s = stats(T, D, *PERIODS["HOLD"]); print(fmt("G1 HOLD-OUT 2026", s)); ledger("G1", "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
