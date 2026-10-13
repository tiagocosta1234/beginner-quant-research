"""One-trade-a-day rules on MT5 broker's US index CFDs, exactly as registered in PREREG_INDEX_DAILY.md: rule A overnight drift (long 16:30 NY -> 09:30 NY next weekday), rule B New York opening-range breakout.
   python -m forex.ea_research.index_daily --smoke                  mechanics check on Dec 2021 (prints trades; not used for any decision)
   python -m forex.ea_research.index_daily --trials                 A1..A3, B1..B5 on NSDQ+ in DEV and VAL, appended to LEDGER.csv
   python -m forex.ea_research.index_daily --replicate A1,B1        the same rules on SP+ and DOW+ over 2022-2025 (only for a primary that passed DEV and VAL)
   python -m forex.ea_research.index_daily --holdout A1             the one-time 2026 look
MT5 broker server clock = New York + 7 h. Returns in basis points of the entry price; costs: ask/bid from the bar spread, slippage 0.12 bp of the price on every market fill, stop assumed first inside a bar."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
H = 3600
SLIP_BP = 1.2e-5
PERIODS = {"SMOKE": ("2021-12-01", "2021-12-31"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30"), "REPL": ("2022-01-01", "2025-12-31")}
BASE_A = dict(rule="A", no_fri=False, stop_pct=0.0)
BASE_B = dict(rule="B", range_min=30, target_r=1.5, mid_stop=False, long_only=False)
TRIALS = {"A1": BASE_A, "A2": {**BASE_A, "no_fri": True}, "A3": {**BASE_A, "stop_pct": 1.0}, "B1": BASE_B, "B2": {**BASE_B, "target_r": 1.0}, "B3": {**BASE_B, "range_min": 15}, "B4": {**BASE_B, "mid_stop": True}, "B5": {**BASE_B, "long_only": True}}


class Data:
    pass


def load(name: str) -> Data:
    d = pd.read_parquet(DATA / f"{name}_M1_rates.parquet").sort_values("t").reset_index(drop=True); D = Data()
    D.ny = d.t.to_numpy("int64") - 7 * H; D.o, D.h, D.l, D.c, D.sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "sp")); D.n = len(d); return D


def wday(day: int) -> int:
    return (day + 3) % 7


def slip(px: float) -> float:
    return SLIP_BP * px


def find_bar(D: Data, t: int, within: int):
    i = int(np.searchsorted(D.ny, t)); return i if i < D.n and D.ny[i] - t < within else None


def weekdays(d0: int, d1: int):
    for d in range(d0, d1 + 1):
        if wday(d) < 5:
            yield d


def trades_A(D: Data, d0: int, d1: int, cfg: dict) -> list[dict]:
    rows = []
    for day in weekdays(d0, d1):
        ie = find_bar(D, day * 86400 + int(16.5 * H), 20 * 60)
        if ie is None or (cfg["no_fri"] and wday(day) == 4):
            continue
        d2, ix = day, None
        for _ in range(6):
            d2 += 1
            while wday(d2) >= 5: d2 += 1
            ix = find_bar(D, d2 * 86400 + int(9.5 * H), 20 * 60)
            if ix is not None: break
        if ix is None or ix <= ie:
            continue
        ent = D.o[ie] + D.sp[ie] + slip(D.o[ie]); ex, xi, why = D.o[ix] - slip(D.o[ix]), ix, "time"
        if cfg["stop_pct"]:
            lvl = ent * (1 - cfg["stop_pct"] / 100); hit = np.nonzero(D.l[ie:ix] <= lvl)[0]
            if len(hit): xi = ie + int(hit[0]); ex = min(lvl, D.o[xi]) - slip(lvl); why = "stop"
        rows.append(dict(day=day, cday=int(D.ny[xi] // 86400), side=1, entry=ent, exit=ex, pts=ex - ent, bp=(ex - ent) / ent * 1e4, r=float("nan"), why=why))
    return rows


def trades_B(D: Data, d0: int, d1: int, cfg: dict) -> list[dict]:
    rows = []
    for day in weekdays(d0, d1):
        b = day * 86400; i0 = find_bar(D, b + int(9.5 * H), 5 * 60)
        if i0 is None: continue
        i1 = int(np.searchsorted(D.ny, b + int(9.5 * H) + cfg["range_min"] * 60)); iend = int(np.searchsorted(D.ny, b + 15 * H)); ixt = int(np.searchsorted(D.ny, b + int(15.75 * H)))
        if i1 - i0 < cfg["range_min"] * 2 // 3 or iend <= i1 + 1 or ixt <= iend: continue
        hi, lo = D.h[i0:i1].max(), D.l[i0:i1].min(); sig = 0
        for j in range(i1, iend):
            if D.c[j] > hi: sig = 1; break
            if D.c[j] < lo and not cfg["long_only"]: sig = -1; break
        if sig == 0 or j + 1 >= D.n: continue
        e = j + 1
        ent = (D.o[e] + D.sp[e] + slip(D.o[e])) if sig > 0 else (D.o[e] - slip(D.o[e]))
        stop = (((hi + lo) / 2) if cfg["mid_stop"] else (lo if sig > 0 else hi)); R = abs(ent - stop)
        if R <= 0 or (sig > 0 and ent <= stop) or (sig < 0 and ent >= stop): continue
        tgt = ent + sig * cfg["target_r"] * R; ex, why, xi = None, "time", ixt
        for k in range(e, ixt):
            if sig > 0:
                if D.l[k] <= stop: ex, why, xi = min(stop, D.o[k]) - slip(stop), "stop", k; break
                if D.h[k] >= tgt: ex, why, xi = max(tgt, D.o[k]), "tp", k; break
            else:
                if D.h[k] + D.sp[k] >= stop: ex, why, xi = max(stop, D.o[k] + D.sp[k]) + slip(stop), "stop", k; break
                if D.l[k] + D.sp[k] <= tgt: ex, why, xi = min(tgt, D.o[k] + D.sp[k]), "tp", k; break
        if ex is None: ex = (D.o[ixt] - slip(D.o[ixt])) if sig > 0 else (D.o[ixt] + D.sp[ixt] + slip(D.o[ixt]))
        pts = sig * (ex - ent); rows.append(dict(day=day, cday=day, side=sig, entry=ent, exit=ex, pts=pts, bp=pts / ent * 1e4, r=pts / R, why=why))
    return rows


def simulate(D: Data, cfg: dict, a: str, b: str):
    d0, d1 = (dt.date.fromisoformat(x) - dt.date(1970, 1, 1) for x in (a, b)); d0, d1 = d0.days, d1.days
    T = pd.DataFrame((trades_A if cfg["rule"] == "A" else trades_B)(D, d0, d1, cfg))
    days = [d for d in weekdays(d0, d1) if find_bar(D, d * 86400 + int(9.5 * H), 5 * 60) is not None]
    return T, days


def stats(T: pd.DataFrame, days: list[int]) -> dict:
    if not len(T): return dict(days=len(days), trades=0, net=0.0, exp=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"), pts=0.0)
    s = pd.Series(0.0, index=days); g = T.groupby("cday").bp.sum(); s.loc[s.index.intersection(g.index)] += g.loc[s.index.intersection(g.index)]
    w, l_ = T.bp[T.bp > 0].sum(), -T.bp[T.bp <= 0].sum(); e = s.to_numpy()
    return dict(days=len(days), trades=len(T), net=float(T.bp.sum()), exp=float(T.bp.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))) if e.std(ddof=1) > 0 else float("nan"), win=float((T.bp > 0).mean()), pts=float(T.pts.sum()))


def fmt(tag, s):
    return f"{tag:30s} days {s['days']:4d} trades {s['trades']:5d} net {s['net']:9,.0f} bp ({s['pts']:9,.0f} pts) | mean {s['exp']:+6.2f} bp/trade | PF {s['pf']:5.2f} | daily t {s['t']:+5.2f} | win {100*s['win']:4.1f}%"


def ledger(trial, period, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},index_daily,{trial},{period},{s['days']},{s['trades']},{s['net']:.1f},{s['exp']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--replicate", default=None); ap.add_argument("--holdout", default=None); a = ap.parse_args()
    if a.smoke:
        D = load("NSDQ"); pd.set_option("display.width", 220)
        for name in ("A1", "B1"):
            T, days = simulate(D, TRIALS[name], *PERIODS["SMOKE"]); T["d"] = pd.to_datetime(T.day, unit="D").dt.strftime("%m-%d"); T["c"] = pd.to_datetime(T.cday, unit="D").dt.strftime("%m-%d")
            print(f"--- {name}"); print(T[["d", "c", "side", "entry", "exit", "pts", "bp", "r", "why"]].round(2).to_string()); print(fmt(f"{name} SMOKE Dec 2021 (mechanics only)", stats(T, days)))
    if a.trials:
        D = load("NSDQ")
        for name, cfg in TRIALS.items():
            for per in ("DEV", "VAL"):
                T, days = simulate(D, cfg, *PERIODS[per]); s = stats(T, days); print(fmt(f"{name} NSDQ {per}", s), flush=True); ledger(name, per, s, "NSDQ+ " + str({k: v for k, v in cfg.items() if k != "rule"}).replace(",", ";"))
    if a.replicate:
        for name in a.replicate.split(","):
            for inst in ("SP", "DOW"):
                D = load(inst); T, days = simulate(D, TRIALS[name], *PERIODS["REPL"]); s = stats(T, days); print(fmt(f"{name} {inst} 2022-25", s), flush=True); ledger(name, "REPL2022-25", s, f"replication {inst}+")
    if a.holdout:
        D = load("NSDQ"); T, days = simulate(D, TRIALS[a.holdout], *PERIODS["HOLD"]); s = stats(T, days); print(fmt(f"{a.holdout} NSDQ HOLD-OUT 2026", s)); ledger(a.holdout, "HOLD", s, "NSDQ+ one-time look")


if __name__ == "__main__":
    main()
