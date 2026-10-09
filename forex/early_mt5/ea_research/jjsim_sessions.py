"""Simulator of JJ Simon's 6 PM / 8 PM New York session setup on MT5 broker's Nasdaq CFD (NSDQ+), exactly as formalised in PREREG_JJSIM_NQ_SESSIONS.md.
   python -m mt5broker.ea_research.jjsim_sessions --smoke            mechanics check on Dec 2021 (prints trades, no result is used)
   python -m mt5broker.ea_research.jjsim_sessions --trials           T1..T12 on DEV and VAL, appended to LEDGER.csv
   python -m mt5broker.ea_research.jjsim_sessions --holdout T1       the one-time 2026 look (only after T1 passed DEV and VAL)
Input: forex/early_mt5/data_mt5/NSDQ_M1_rates.parquet (MT5 broker server clock = New York + 7 h; bid OHLC and the bar spread). P&L in index points (1 lot = 5 USD a point)."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5" / "NSDQ_M1_rates.parquet"
LEDGER = HERE / "LEDGER.csv"
H = 3600
SLIP = 0.3                      # points, adverse, on every market entry, stop and market exit
PERIODS = {"SMOKE": ("2021-12-01", "2021-12-31"), "DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
BASE = dict(tp=38.0, sl=25.0, thr=30.0, structure=False, be=True, cont=True, rev=True, s18=True, s20=True, gap=10.0, max_rev=3, invert=False)
TRIALS = {"T1": {}, "T2": dict(tp=25.0), "T3": dict(tp=50.0), "T4": dict(sl=38.0), "T5": dict(structure=True), "T6": dict(rev=False), "T7": dict(cont=False),
          "T8": dict(s20=False), "T9": dict(s18=False), "T10": dict(thr=20.0), "T11": dict(thr=40.0), "T12": dict(be=False), "I1": dict(invert=True), "I2": dict(invert=True, tp=25.0, sl=38.0)}


class Data:
    pass


def load() -> Data:
    d = pd.read_parquet(DATA).sort_values("t").reset_index(drop=True); D = Data()
    D.ny = d.t.to_numpy("int64") - 7 * H
    D.o, D.h, D.l, D.c, D.sp = (d[k].to_numpy("float64") for k in ("bo", "bh", "bl", "bc", "sp"))
    D.n = len(d); return D


def wday(day: int) -> int:                                    # Monday = 0 (epoch day 0 was a Thursday)
    return (day + 3) % 7


def open_0930(D: Data, day: int) -> float:
    for k in range(5):
        dd = day - k
        if wday(dd) < 5:
            tgt = dd * 86400 + 34200; j = int(np.searchsorted(D.ny, tgt))
            if j < D.n and D.ny[j] - tgt < 300:
                return float(D.o[j])
    return float("nan")


def sim_evening(D: Data, day: int, cfg: dict) -> list[dict]:
    ny, o, h, l, c, sp = D.ny, D.o, D.h, D.l, D.c, D.sp; base = day * 86400
    lo = int(np.searchsorted(ny, base + 18 * H)); hi = int(np.searchsorted(ny, base + 22 * H))
    if lo == 0 or hi - lo < 60 or ny[lo] - base > 18.5 * H:
        return []
    F1 = o[lo]; gap = F1 - c[lo - 1]; o930 = open_0930(D, day); bias = 0 if np.isnan(o930) else int(np.sign(F1 - o930))
    j20 = int(np.searchsorted(ny, base + 20 * H)); j20 = j20 if (j20 < hi and ny[j20] - (base + 20 * H) < 900) else None
    fair, fair2 = F1, None; pos = None; pending = None; trades = []; att = {"18": 0, "20": 0}; be_done = False

    def close(i, px, why):
        nonlocal pos
        pts = pos["side"] * (px - pos["entry"]); trades.append(dict(day=day, side=pos["side"], typ=pos["typ"], sess=pos["sess"], t_in=int(ny[pos["i"]]), t_out=int(ny[i]), entry=pos["entry"], exit=px, pts=pts, worst=pos["worst"], why=why)); pos = None

    for i in range(lo, hi):
        s = ny[i] - base
        if cfg["be"] and pos is not None and not be_done and s >= 20 * H:
            pos["sl"] = pos["entry"]; pos["be"] = True
        if s >= 20 * H:
            be_done = True
        if pending is not None and pos is None:
            side, typ, sess = pending; fill = (o[i] + sp[i] + SLIP) if side > 0 else (o[i] - SLIP)
            pos = dict(side=side, typ=typ, sess=sess, i=i, entry=fill, tp=fill + side * cfg["tp"], sl=fill - side * cfg["sl"], worst=0.0, be=False)
            if typ == "rev": att[sess] += 1
        pending = None
        if pos is not None:
            side = pos["side"]; ah, al, ao = h[i] + sp[i], l[i] + sp[i], o[i] + sp[i]
            if side > 0:
                pos["worst"] = min(pos["worst"], l[i] - pos["entry"])
                if l[i] <= pos["sl"]: close(i, min(pos["sl"], o[i]) - SLIP, "be" if pos["be"] else "sl")
                elif h[i] >= pos["tp"]: close(i, max(pos["tp"], o[i]), "tp")
            else:
                pos["worst"] = min(pos["worst"], pos["entry"] - ah)
                if ah >= pos["sl"]: close(i, max(pos["sl"], ao) + SLIP, "be" if pos["be"] else "sl")
                elif al <= pos["tp"]: close(i, min(pos["tp"], ao), "tp")
        if i + 1 >= hi:
            break
        k = i - lo; s_next = ny[i + 1] - base
        if j20 is not None and i == j20 + 4:                                              # Asian fair price, decided at the close of the 20:04 bar
            toward = np.sign(c[i] - o[j20]) == np.sign(F1 - o[j20]) and np.sign(F1 - o[j20]) != 0
            fair2 = F1 if toward else o[j20]
        if pos is not None:
            continue
        side = 0; typ = sess = None
        if cfg["cont"] and cfg["s18"] and k == 0 and s_next < 20 * H:
            d = int(np.sign(c[i] - o[i]))
            if d != 0 and bias == d and not (d > 0 and gap > cfg["gap"]) and not (d < 0 and gap < -cfg["gap"]): side, typ, sess = d, "cont", "18"
        elif cfg["cont"] and cfg["s20"] and j20 is not None and i == j20 and s_next < 21.5 * H:
            d = int(np.sign(c[i] - o[i]))
            if d != 0: side, typ, sess = d, "cont", "20"
        if side == 0 and cfg["rev"]:
            sess_now, f, ok = None, None, False
            if cfg["s18"] and k >= 5 and s_next < 20 * H and att["18"] < cfg["max_rev"]: sess_now, f, ok = "18", fair, True
            elif cfg["s20"] and j20 is not None and fair2 is not None and i >= j20 + 5 and 20 * H <= s_next < 21.5 * H and att["20"] < cfg["max_rev"]: sess_now, f, ok = "20", fair2, True
            if ok and i >= 1:
                body, pbody = abs(c[i] - o[i]), abs(c[i - 1] - o[i - 1]); a = max(lo, i - 10)
                if c[i] > o[i] and body > pbody and c[i] > h[i - 1] and f - c[i] >= cfg["thr"] and (not cfg["structure"] or c[i] > h[a:i].max()): side, typ, sess = 1, "rev", sess_now
                elif c[i] < o[i] and body > pbody and c[i] < l[i - 1] and c[i] - f >= cfg["thr"] and (not cfg["structure"] or c[i] < l[a:i].min()): side, typ, sess = -1, "rev", sess_now
        if side != 0:
            pending = (-side if cfg["invert"] else side, typ, sess)
    if pos is not None:                                                                   # 22:00 time stop
        j = hi if hi < D.n else hi - 1
        close(j, (o[j] - SLIP) if pos["side"] > 0 else (o[j] + sp[j] + SLIP), "time")
    return trades


def simulate(D: Data, cfg: dict, a: str, b: str):
    d0, d1 = (dt.date.fromisoformat(x) - dt.date(1970, 1, 1) for x in (a, b)); rows, ev = [], []
    for day in range(d0.days, d1.days + 1):
        if wday(day) not in (6, 0, 1, 2, 3):
            continue
        tr = sim_evening(D, day, cfg)
        lo = int(np.searchsorted(D.ny, day * 86400 + 18 * H))
        if lo == 0 or lo >= D.n or D.ny[lo] - day * 86400 > 18.5 * H:
            continue
        cum = low = 0.0
        for t in tr:
            low = min(low, cum + t["worst"]); cum += t["pts"]; low = min(low, cum)
        ev.append(dict(day=day, n=len(tr), pts=cum, low=low)); rows += tr
    T = pd.DataFrame(rows); E = pd.DataFrame(ev)
    if len(T):
        T["date"] = pd.to_datetime(T.day, unit="D")
    E["date"] = pd.to_datetime(E.day, unit="D"); return T, E


def stats(T: pd.DataFrame, E: pd.DataFrame) -> dict:
    if not len(T):
        return dict(evenings=len(E), trades=0, net=0.0, exp=float("nan"), pf=float("nan"), t=float("nan"), win=float("nan"))
    w, l_ = T.pts[T.pts > 0].sum(), -T.pts[T.pts <= 0].sum(); e = E.pts.to_numpy()
    return dict(evenings=len(E), trades=len(T), net=float(T.pts.sum()), exp=float(T.pts.mean()), pf=float(w / l_) if l_ > 0 else float("inf"), t=float(e.mean() / (e.std(ddof=1) / np.sqrt(len(e)))) if e.std(ddof=1) > 0 else float("nan"), win=float((T.pts > 0).mean()))


def fmt(tag, s):
    return f"{tag:34s} evenings {s['evenings']:4d} trades {s['trades']:5d} net {s['net']:9,.1f} pts | expectancy {s['exp']:+6.2f} pts/trade | PF {s['pf']:5.2f} | evening t {s['t']:+5.2f} | win {100*s['win']:4.1f}%"


def ledger(trial, period, s, note=""):
    row = f"{dt.datetime.now():%Y-%m-%d %H:%M},jjsim_nq,{trial},{period},{s['evenings']},{s['trades']},{s['net']:.1f},{s['exp']:.3f},{s['pf']:.3f},{s['t']:.2f},{s['win']:.3f},{note}\n"
    with open(LEDGER, "a", encoding="utf-8") as f: f.write(row)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--only", default=None); ap.add_argument("--holdout", default=None)
    a = ap.parse_args(); D = load()
    if a.smoke:
        T, E = simulate(D, BASE, *PERIODS["SMOKE"]); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
        T["in_ny"] = pd.to_datetime(T.t_in, unit="s").dt.strftime("%m-%d %H:%M"); T["out_ny"] = pd.to_datetime(T.t_out, unit="s").dt.strftime("%m-%d %H:%M")
        print(T[["in_ny", "out_ny", "sess", "typ", "side", "entry", "exit", "pts", "worst", "why"]].round(2).to_string())
        print(fmt("SMOKE Dec 2021 (mechanics only)", stats(T, E)))
        print("invariants: max trades per evening", int(E.n.max()), "| worst pts", round(T.pts.min(), 1), "| best pts", round(T.pts.max(), 1), "| exits by reason", T.why.value_counts().to_dict(), "| entry hours NY", sorted(set(pd.to_datetime(T.t_in, unit="s").dt.hour)))
    if a.trials:
        for name, over in TRIALS.items():
            if a.only and name not in a.only.split(","): continue
            cfg = {**BASE, **over}
            for per in ("DEV", "VAL"):
                T, E = simulate(D, cfg, *PERIODS[per]); s = stats(T, E); print(fmt(f"{name} {per} {over or 'primary'}", s), flush=True); ledger(name, per, s, str(over).replace(",", ";"))
    if a.holdout:
        cfg = {**BASE, **TRIALS[a.holdout]}; T, E = simulate(D, cfg, *PERIODS["HOLD"]); s = stats(T, E); print(fmt(f"{a.holdout} HOLD-OUT 2026", s)); ledger(a.holdout, "HOLD", s, "one-time look")


if __name__ == "__main__":
    main()
