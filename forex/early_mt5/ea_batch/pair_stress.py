"""Stress tests of the pair (Stochastic Daily Breakout + XAUUSD 5 minute) at 1.5 x scale, with and without an equity guard (the trader, 2026-10-06: "do everything ... test it on every single aspect").

BASE      the 2022-2026 real-tick tester runs, each EA scaled to its frozen lot x its weight, intraday equity rebuilt on MT5 1-minute bid / ask bars and summed on one minute clock (as ea_combo_all.py).
TESTS     S0 base (both EAs at 1.5)   S1 the lots actually loadable (0.31 / 0.10 = 1.508 x / 1.431 x)   S2 extra cost per lot per side ($15 / $30 / $60 on top of the tester's spread, i.e. a worse broker)
          S3 MT5 broker's daily reset at Prague midnight (server time - 1 h) instead of the server midnight   S4 equity guard   S5 guard + loadable lots + $30 cost + Prague day   S6 block bootstrap of the daily results
GUARD     the model of the AccountGuard EA: when the day's equity falls to -2.5% of $100K from the day's opening equity, everything is closed at that minute and nothing trades until the next day; when the account
          equity falls to 8% below its highest end-of-day balance (1-Step) / 8% below the start balance (2-Step) everything is closed and the test stops ("halt": not a pass, not a breach, the account is intact).
          The model assumes the EAs cannot re-enter after a halt (the guard deletes pending orders and closes positions every second).
RULES     1-Step: +10% target (best day <= 50% of the profit), 3% daily loss, 10% floor trailing the highest end-of-day balance; 2-Step: +10% then +5%, 5% daily, static 10% floor, 4 trading days each.
          A test is started on every weekday from 2022 and runs until it passes, breaches, halts or the data ends (no deadline).

  python -m mt5broker.ea_batch.pair_stress
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch import confirm, ea_curves as EC, floating

HERE = Path(__file__).resolve().parent
INITIAL = 100_000.0
YEARS = (2022, 2023, 2024, 2025, 2026)
END = pd.Timestamp("2026-09-30")
IDS = ("77900", "mkt_xau5min")
LOT = {"77900": 0.01 * 20.557519940794243, "mkt_xau5min": 0.01 * 6.988901624220759}      # frozen lots (lots)


def load_pair():
    s = pd.read_csv(EC.SUMMARY, dtype={"id": str})
    return s[s.id.isin(IDS)].set_index("id")


def build(weights: dict, extra_cost: float = 0.0, shift_h: int = 0):
    """(U, E, R, day starts, days) of the pair at c = weights per EA (multiples of the frozen lot). extra_cost = $ per lot per side added to the tester's commission."""
    top = load_pair()
    Uall, Eall, Rall, offset = [], [], [], 0.0
    for y in YEARS:
        Es, Rs = {}, {}
        for eid in IDS:
            r = top.loc[eid]
            rd = HERE / f"results_{y}"; f = rd / f"{eid}.csv"
            st = pd.read_csv(rd / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
            sym = str(st.loc[eid, "symbol"]); end = "2026-09-30" if y == 2026 else f"{y}-12-31"
            fl = floating.get(eid, y, f, sym, float(st.loc[eid, "eq_dd"]), f"{y}-01-01", end)
            fac = 1.0 if (y == 2026 or confirm.is_fx(sym)) else confirm.level(HERE / "results_2026" / f"{eid}.csv") / confirm.level(f)
            lam = float(r.lam_frozen) * fac * weights[eid]
            deals = pd.read_csv(f)
            if extra_cost:
                deals["commission"] = deals["commission"] - extra_cost * deals["volume"]          # the deal's own volume (tested lot); scaled with lam below like every other P&L
            idx, E, R = EC.minute_equity(deals, sym, f"{y}-01-01", end, basis=fl.diag.get("basis", "mid"))
            Es[eid] = lam * pd.Series(E, index=idx); Rs[eid] = lam * pd.Series(R, index=idx)
        U = pd.DatetimeIndex(sorted(set().union(*[set(x.index) for x in Es.values()])))
        E = sum(x.reindex(U).ffill().fillna(0.0) for x in Es.values()).values
        R = sum(x.reindex(U).ffill().fillna(0.0) for x in Rs.values()).values
        Uall.append(U); Eall.append(E + offset); Rall.append(R + offset); offset += R[-1]
    U = pd.DatetimeIndex(np.concatenate([u.values for u in Uall])); E = np.concatenate(Eall); R = np.concatenate(Rall)
    day = (U - pd.Timedelta(hours=shift_h)).values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    return U, E, R, start, pd.DatetimeIndex(day[start])


def day_frames(U, E, R, start, days, guard_day: float | None):
    """Daily closed P&L v and worst equity m (relative to the day's opening equity). With guard_day (e.g. 0.025): the day stops at the first minute whose equity is guard_day x $100K below the day's open."""
    n = len(E)
    end = np.r_[start[1:], n]
    before = np.where(start > 0, R[np.maximum(start - 1, 0)], 0.0)
    v = np.add.reduceat(np.diff(R, prepend=0.0), start)
    m = np.minimum(np.minimum.reduceat(E, start) - before, v)
    halted = np.zeros(len(start), bool)
    if guard_day:
        lim = -guard_day * INITIAL
        for k in np.flatnonzero(m <= lim):
            path = E[start[k]:end[k]] - before[k]
            j = int(np.argmax(path <= lim))
            v[k] = path[j]; m[k] = path[j]; halted[k] = True                               # flattened at that minute
    return v, m, halted


def attempt1(pnl, mm, days, halt=None):
    bal = hwm = INITIAL; pos = best = 0.0
    for d in days:
        v = pnl.get(d, 0.0); m = min(mm.get(d, 0.0), v)
        hwm = max(hwm, bal)
        if m < -3_000 or bal + m <= hwm - 10_000:
            return "breach"
        if halt is not None and bal + m <= hwm - halt:
            return "halt"
        bal += v
        if v > 0:
            pos += v; best = max(best, v)
        if bal > 110_000 and best <= 0.5 * pos:
            return "pass"
    return "open"


def attempt2(pnl, mm, ent, days, halt=None):
    def phase(i, target):
        bal, tds = INITIAL, set()
        while i < len(days):
            d = days[i]; v = pnl.get(d, 0.0); m = min(mm.get(d, 0.0), v)
            if d in ent:
                tds.add(d)
            if m < -5_000 or bal + m < 90_000:
                return "breach", i + 1
            if halt is not None and bal + m <= INITIAL - halt:
                return "halt", i + 1
            bal += v
            if bal > target and len(tds) >= 4:
                return "pass", i + 1
            i += 1
        return "open", i
    o1, i = phase(0, 110_000.0)
    if o1 != "pass":
        return o1, None
    o2, j = phase(i + 2, 105_000.0)
    return o2, (j - (i + 2)) + i + 2 if o2 == "pass" else None


@dataclass
class Out:
    p1: float; b1: float; h1: float; p2: float; b2: float; h2: float; n: int; worst_day: float; days_med: float


def evaluate(v, m, days, guard_halt: float | None = None, cap: int | None = None, step: int = 2, rules1: bool = False) -> Out:
    bd = pd.bdate_range(days.min(), END)
    V = pd.Series(v, index=days).reindex(bd).fillna(0.0); M = pd.Series(m, index=days).reindex(bd).fillna(0.0)
    pnl, mm = V.to_dict(), M.to_dict(); ent = set(days[np.abs(v) > 0])
    r1, r2 = [], []
    for i in range(0, len(bd) - 60, step):
        dl = list(bd[i:i + cap]) if cap else list(bd[i:])
        r1.append(attempt1(pnl, mm, dl, guard_halt) if rules1 else "open"); r2.append(attempt2(pnl, mm, ent, dl, guard_halt))
    f = lambda rr, k: float(np.mean([x == k for x in rr]))
    f2 = lambda k: float(np.mean([x[0] == k for x in r2]))
    dd = [x[1] for x in r2 if x[0] == "pass"]
    return Out(f(r1, "pass"), f(r1, "breach"), f(r1, "halt"), f2("pass"), f2("breach"), f2("halt"), len(r1), float(-m.min() / INITIAL * 100), float(np.median(dd)) if dd else float("nan"))


def row(tag, o: Out):
    print(f"{tag:<50} 2-Step pass {o.p2:4.0%} breach {o.b2:4.0%} open {1 - o.p2 - o.b2 - o.h2:4.0%} | median {o.days_med:4.0f} trading days to finish both phases | worst day {o.worst_day:4.1f}%", flush=True)


def main():
    Wr = {"77900": 0.31 / LOT["77900"], "mkt_xau5min": 0.10 / LOT["mkt_xau5min"]}
    print("loadable-lot weights (0.31 / 0.10):", {k: round(v, 3) for k, v in Wr.items()}, "  RULES: MT5 2-Step, no deadline, a test from every weekday 2022-2026", flush=True)
    # 1) scale grid, no guard
    for c in (1.0, 1.25, 1.5, 2.0):
        b = build({i: c for i in IDS}); v, m, _ = day_frames(*b, None); row(f"scale {c:.2f}, no guard", evaluate(v, m, b[4]))
    # 2) guard thresholds at 1.5
    b = build({i: 1.5 for i in IDS})
    for g in (0.025, 0.03, 0.04):
        v, m, h = day_frames(*b, g); o = evaluate(v, m, b[4]); row(f"1.5, day guard {g:.1%} ({int(h.sum())} day-stops)", o)
    # 3) the loadable lots, then every stress on top (guard = 4% a day)
    rb = build(Wr)
    v, m, _ = day_frames(*rb, None); row("loadable 0.31 / 0.10, no guard", evaluate(v, m, rb[4]))
    v, m, _ = day_frames(*rb, 0.04); row("loadable 0.31 / 0.10, guard 4%", evaluate(v, m, rb[4]))
    for ec in (15, 30, 60):
        b = build(Wr, extra_cost=ec)
        v, m, _ = day_frames(*b, None); row(f"  +${ec}/lot/side, no guard", evaluate(v, m, b[4]))
        v, m, _ = day_frames(*b, 0.04); row(f"  +${ec}/lot/side, guard 4%", evaluate(v, m, b[4]))
    b = build(Wr, shift_h=1)
    v, m, _ = day_frames(*b, None); row("  Prague-midnight days, no guard", evaluate(v, m, b[4]))
    v, m, _ = day_frames(*b, 0.04); row("  Prague-midnight days, guard 4%", evaluate(v, m, b[4]))
    b = build(Wr, extra_cost=30, shift_h=1)
    v, m, _ = day_frames(*b, None); row("EVERYTHING (lots, +$30, Prague), no guard", evaluate(v, m, b[4]))
    v, m, _ = day_frames(*b, 0.04); row("EVERYTHING (lots, +$30, Prague), guard 4%", evaluate(v, m, b[4]))
    # 4) block bootstrap of the daily results (20-day blocks), 2-Step, tests up to 500 trading days
    rng = np.random.default_rng(347)
    for tag, g in (("no guard", None), ("guard 4%", 0.04)):
        vv, mm_, _ = day_frames(*rb, g); N = len(vv); B = 20; res = []
        for _ in range(150):
            idx = np.concatenate([np.arange(s0, s0 + B) % N for s0 in rng.integers(0, N, N // B + 1)])[:N]
            fd = pd.bdate_range("2030-01-01", periods=N); pnl, mmd = dict(zip(fd, vv[idx])), dict(zip(fd, mm_[idx])); ent = set(fd)
            for i0 in range(0, N - 60, 60):
                res.append(attempt2(pnl, mmd, ent, list(fd[i0:i0 + 500]))[0])
        f = lambda k: np.mean([x == k for x in res])
        print(f"BOOTSTRAP {tag} (150 paths, 20-day blocks, up to 500 days): 2-Step pass {f('pass'):.0%} breach {f('breach'):.0%} open {f('open'):.0%}", flush=True)


if __name__ == "__main__":
    main()
