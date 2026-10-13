"""The Stochastic Daily Breakout EA ALONE on an MT5 2-Step account (the trader: "run the Stochastic EA alone"), 2022-2026, real-tick tester runs (results_<year>/77900.csv), equity rebuilt on MT5 1-minute bid / ask bars.

Reuses pair_stress.build (one EA: IDS is set to ("77900",)) and pair_ladder.run (2-Step, +10% then +5%, 5% daily loss, static 10% floor, >= 4 trading days per phase, no deadline, a test from every weekday;
a ladder multiplies the NEXT day's P&L by the step's scale / the base scale, the step chosen from the previous day's balance relative to the phase start).
Frozen lot = 0.01 x 20.5575 = 0.2056 lots (the 2026-ranking size); scale c = multiple of it, lots = 0.2056 x c.
Ladders (fixed before the run, same ratios as the pair's ladder LB: 1 : 2/3 : 0.4 : 0.2 at -2% / -4% / -6%).   python -m forex.ea_batch.stoch_alone
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from forex.ea_batch import floating, pair_ladder as PL, pair_stress as PS

PS.IDS = ("77900",)
PS.LOT = {"77900": PS.LOT["77900"]}
LOT1 = 0.01 * 20.557519940794243


def trade_stats():
    print("TRADE STATISTICS (tester runs, 0.01-lot deals scaled to the frozen lot 0.2056; net = profit + commission + swap)", flush=True)
    tot = []
    for y in PS.YEARS:
        f = PS.HERE / f"results_{y}" / "77900.csv"
        d = pd.read_csv(f)
        pos, _ = floating.pair_positions(d, floating.prior_k("XAUUSD", pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")))
        fac = 1.0 if y == 2026 else PS.confirm.level(PS.HERE / "results_2026" / "77900.csv") / PS.confirm.level(f)
        k = 20.557519940794243 * fac
        te, tx = pd.to_datetime(pos.te), pd.to_datetime(pos.tx)
        net = pos.profit.values * k + (0.0)
        hold = (tx - te).dt.total_seconds() / 60
        wk = te.dt.isocalendar().week.values != tx.dt.isocalendar().week.values
        w = net[net > 0].sum(); l = -net[net <= 0].sum()
        tot.append(net)
        print(f"  {y}: {len(pos):>3} trades, win {np.mean(net > 0):4.0%}, profit factor {w / l if l else float('nan'):4.2f}, net at frozen lot {net.sum():>+9,.0f}, avg win {net[net > 0].mean():>+7,.0f} / avg loss {net[net <= 0].mean():>+7,.0f}, median hold {np.median(hold) / 60:5.1f} h, crossing a weekend {wk.mean():4.0%}", flush=True)
    net = np.concatenate(tot)
    print(f"  all: {len(net)} trades ({len(net) / 4.75:.0f} a year), win {np.mean(net > 0):.0%}, net {net.sum():+,.0f} at the frozen lot, t-stat of the trade P&L {net.mean() / (net.std() / np.sqrt(len(net))):+.1f}", flush=True)


def main():
    trade_stats()
    b = PS.build({"77900": 1.0})
    v, m, _ = PS.day_frames(*b, None); days = b[4]; U, E, R = b[0], b[1], b[2]
    by = pd.Series(np.diff(R, prepend=0.0), index=U).groupby(U.year).sum()
    dd = {}
    for y in PS.YEARS:
        sel = U.year == y; e = np.concatenate([[0.0], E[sel] - E[sel][0]]); dd[y] = float((np.maximum.accumulate(e) - e).max())
    print("\nAT THE FROZEN LOT (c = 1): worst intraday day %.1f%% of $100K; per-year max equity drawdown: %s" % (-m.min() / PS.INITIAL * 100, {y: f"{x:,.0f}" for y, x in dd.items()}), flush=True)
    print("\n2-STEP, NO DEADLINE, all starts 2022-2026 | starts in 2022-23 | starts 2024+   (pass / breach, median trading days to finish both phases)", flush=True)
    for c in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        PL.run(f"constant {c:.1f} x ({LOT1 * c:.2f} lots)", v, m, days, lambda dd_, c=c: c, 1.0)
    print("\nDE-RISK LADDERS (start scale / then 2/3 / 0.4 / 0.2 of it at -2 / -4 / -6% from the phase start)", flush=True)
    for top in (1.5, 2.0, 3.0):
        rule = lambda dd_, top=top: top if dd_ >= -0.02 else (top * 2 / 3 if dd_ >= -0.04 else (top * 0.4 if dd_ >= -0.06 else top * 0.2))
        PL.run(f"ladder from {top:.1f} x ({LOT1 * top:.2f} -> {LOT1 * top * 2 / 3:.2f} -> {LOT1 * top * 0.4:.2f} -> {LOT1 * top * 0.2:.2f})", v, m, days, rule, 1.0)
    print("\nSTRESS: +$30 per lot per side (worse broker) and MT5 broker's Prague-midnight day", flush=True)
    bs = PS.build({"77900": 1.0}, extra_cost=30, shift_h=1)
    vs, ms, _ = PS.day_frames(*bs, None)
    for c in (1.0, 2.0, 3.0):
        PL.run(f"constant {c:.1f} x, stressed", vs, ms, bs[4], lambda dd_, c=c: c, 1.0)
    top = 2.0
    PL.run("ladder from 2.0 x, stressed", vs, ms, bs[4], lambda dd_: top if dd_ >= -0.02 else (top * 2 / 3 if dd_ >= -0.04 else (top * 0.4 if dd_ >= -0.06 else top * 0.2)), 1.0)
    # bootstrap of the daily results
    rng = np.random.default_rng(347)
    for c in (1.0, 2.0):
        vv, mm_ = v * c, m * c; N = len(vv); res = []
        for _ in range(150):
            idx = np.concatenate([np.arange(s0, s0 + 20) % N for s0 in rng.integers(0, N, N // 20 + 1)])[:N]
            fd = pd.bdate_range("2030-01-01", periods=N); pnl, mmd = dict(zip(fd, vv[idx])), dict(zip(fd, mm_[idx])); ent = set(fd)
            for i0 in range(0, N - 60, 60):
                res.append(PS.attempt2(pnl, mmd, ent, list(fd[i0:i0 + 750]))[0])
        f = lambda k: np.mean([x == k for x in res])
        print(f"BOOTSTRAP constant {c:.1f} x (150 paths, 20-day blocks, up to 750 days): pass {f('pass'):.0%} breach {f('breach'):.0%} open {f('open'):.0%}", flush=True)


if __name__ == "__main__":
    main()
