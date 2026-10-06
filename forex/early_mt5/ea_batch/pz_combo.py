"""Combined replay: the pair (Stochastic Daily Breakout 0.31 + XAUUSD 5 minute 0.10, MT5 2-Step) with PZ_StochEA on US100.cash H1 added (the trader: "run the combined replay").

PZ deals: the real-tick tester runs of pz_us100_years.py / pz_stoch_test.py (US100cash_H1_<year>.csv, 2026 = US100cash_H1.csv), default inputs, 0.01 lot; scaled to PZ_LOTS lots (a multiple of 0.01) and
put on the pair's minute clock with the same equity rebuild (MT5 M1 bars). Slippage: SLIP index points per trade taken off every closing deal ($0.01 per point at 0.01 lot).
Series: pair alone | pair + PZ at 0.25 / 0.5 / 1.0 lots, each with 0 and 1.0 point of slippage | PZ alone. Rules and ladder as pair_ladder.py (2-Step, +10% / +5%, 5% daily, static 10% floor, a test from every weekday 2022-2026, no deadline;
ladder LB multiplies the whole combined day by step / 1.5).   python -m mt5broker.ea_batch.pz_combo
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch import confirm, ea_curves as EC, floating, pair_ladder as PL, pair_stress as PS

PZDIR = r"D:\finance\scratch\pz_stoch"
SYM = "US100.cash"
_cache: dict = {}


def pz_year(y: int, slip: float):
    k = (y, slip)
    if k not in _cache:
        f = f"{PZDIR}\\US100cash_H1.csv" if y == 2026 else f"{PZDIR}\\US100cash_H1_{y}.csv"
        d = pd.read_csv(f)
        if slip:
            d.loc[d.direction == "out", "commission"] -= slip * 0.01
        end = "2026-09-30" if y == 2026 else f"{y}-12-31"
        idx, E, R = EC.minute_equity(d, SYM, f"{y}-01-01", end, basis="mid")
        _cache[k] = (pd.Series(E, index=idx), pd.Series(R, index=idx))
    return _cache[k]


def build(pair_w: float, pz_lots: float, slip: float):
    """Like pair_stress.build, plus PZ at pz_lots. pair_w = multiple of the loadable pair lots (1.0 = 0.31 / 0.10); pz_lots = 0 drops PZ."""
    Wr = {"77900": pair_w * 0.31 / PS.LOT["77900"], "mkt_xau5min": pair_w * 0.10 / PS.LOT["mkt_xau5min"]}
    top = PS.load_pair()
    Uall, Eall, Rall, offset = [], [], [], 0.0
    for y in PS.YEARS:
        Es, Rs = {}, {}
        for eid in PS.IDS:
            r = top.loc[eid]; rd = PS.HERE / f"results_{y}"; f = rd / f"{eid}.csv"
            st = pd.read_csv(rd / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
            sym = str(st.loc[eid, "symbol"]); end = "2026-09-30" if y == 2026 else f"{y}-12-31"
            fl = floating.get(eid, y, f, sym, float(st.loc[eid, "eq_dd"]), f"{y}-01-01", end)
            fac = 1.0 if (y == 2026 or confirm.is_fx(sym)) else confirm.level(PS.HERE / "results_2026" / f"{eid}.csv") / confirm.level(f)
            lam = float(r.lam_frozen) * fac * Wr[eid]
            idx, E, R = EC.minute_equity(pd.read_csv(f), sym, f"{y}-01-01", end, basis=fl.diag.get("basis", "mid"))
            Es[eid] = lam * pd.Series(E, index=idx); Rs[eid] = lam * pd.Series(R, index=idx)
        if pz_lots:
            e, rr = pz_year(y, slip); Es["pz"] = e * (pz_lots / 0.01); Rs["pz"] = rr * (pz_lots / 0.01)
        U = pd.DatetimeIndex(sorted(set().union(*[set(x.index) for x in Es.values()])))
        E = sum(x.reindex(U).ffill().fillna(0.0) for x in Es.values()).values
        R = sum(x.reindex(U).ffill().fillna(0.0) for x in Rs.values()).values
        Uall.append(U); Eall.append(E + offset); Rall.append(R + offset); offset += R[-1]
    U = pd.DatetimeIndex(np.concatenate([u.values for u in Uall])); E = np.concatenate(Eall); R = np.concatenate(Rall)
    day = U.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    return U, E, R, start, pd.DatetimeIndex(day[start])


def by_year(U, R):
    s = pd.Series(np.diff(R, prepend=0.0), index=U).groupby(U.year).sum()
    return " ".join(f"{y}:{x:+,.0f}" for y, x in s.items())


def main():
    LB = PL.LADDERS["LB 1.5 / 1.0 / 0.6 / 0.3 at -2 / -4 / -6%"]
    cases = [("pair alone", 1.0, 0.0, 0.0)]
    for lots in (0.25, 0.5, 1.0):
        for slip in (0.0, 1.0):
            cases.append((f"pair + PZ {lots} lot, slip {slip:g} pt", 1.0, lots, slip))
    cases.append(("PZ alone 1.0 lot, slip 0", 0.0, 1.0, 0.0)); cases.append(("PZ alone 1.0 lot, slip 1", 0.0, 1.0, 1.0))
    for name, w, lots, slip in cases:
        if w == 0.0:                                            # PZ alone: pair at a negligible weight is the clock; subtract by building the pair at 1e-9
            w = 1e-9
        U, E, R, start, days = build(w, lots, slip)
        v, m, _ = PS.day_frames(U, E, R, start, days, None)
        print(f"\n== {name}: yearly P&L {by_year(U, R)}; worst day {-m.min():,.0f}", flush=True)
        PL.run("  constant (as loaded)", v, m, days, lambda dd: 1.5, 1.5)
        PL.run("  ladder LB", v, m, days, LB, 1.5)


if __name__ == "__main__":
    main()
