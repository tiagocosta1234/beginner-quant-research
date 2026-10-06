"""Round 347e (part 2) -- the trendline breakout of trendline_eval.py traded on EVERY symbol at the same time, as one account (the trader, 2026-10-06: "you can trade every symbol at the same time").

Each symbol runs the primary spec (30-bar lookback, 1.5 ATR stop, 12-bar hold, entry at the next bar's open at the real bid / ask) independently, every trade sized to risk r% of $100K at its own stop.
The account's equity is the SUM of the symbols' minute-by-minute equity curves on one common clock (so floating losses that coincide across symbols add up, exactly as the firm would see them), then
the same daily-loss / maximum-loss replay as trendline_eval.py. Symbols: every MT5 1-minute bid / ask file in forex/early_mt5/data (BTCUSD, XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF and the cash
indices US100 / US30 / US500 / US2000 / GER40 / FRA40 / UK100). Because a trade is sized by its stop, the contract size cancels out of the risk; it only matters for commission (FX $3 / lot / side as the
tester charged, XAUUSD $1, indices and BTC none assumed) and for the currency conversion of GER40 / FRA40 / UK100 (ignored: a few percent of those trades' P&L). Margin and leverage limits are not
modelled: with 15 symbols several positions can be open at once. A random-direction run of the same portfolio (same events, coin-flip sides) is the null.

  python -m mt5broker.ea_batch.trendline_portfolio
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch import trendline_eval as T

EXTRA = {
    "AUDUSD": ("AUDUSD_M1_ticks_full.parquet", lambda p: 100_000.0, 3.0, "B"),
    "USDCAD": ("USDCAD_M1_ticks_full.parquet", lambda p: 100_000.0 / p, 3.0, "B"),
    "USDCHF": ("USDCHF_M1_ticks_full.parquet", lambda p: 100_000.0 / p, 3.0, "B"),
}
for ix in ("US100.cash", "US30.cash", "US500.cash", "US2000.cash", "GER40.cash", "FRA40.cash", "UK100.cash"):
    EXTRA[ix] = (f"{ix}_M1_ticks_full.parquet", lambda p: 1.0, 0.0, "B")
T.SYMBOLS.update(EXTRA)
RISKS = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.75, 1.0)


def minute_index(sym):
    return pd.DatetimeIndex(pd.to_datetime(pd.read_parquet(T.DATA / T.SYMBOLS[sym][0], columns=["time"]).time, unit="s"))


def curves(tr: pd.DataFrame, m1: pd.DataFrame):
    """(realized P&L per minute, equity per minute relative to the start) for one symbol's trades at 1% risk; floating at the worst bid / ask of every open minute."""
    n = len(m1)
    bl, ah = m1.low.values, m1.ask_high.values
    real, F = np.zeros(n), np.zeros(n)
    for p in tr.itertuples():
        kv = p.lots * p.k
        wl = (bl[p.i0:p.i1 + 1] - p.pe) * kv if p.side == 1 else (p.pe - ah[p.i0:p.i1 + 1]) * kv
        real[p.i0] -= p.comm
        real[p.i1] += p.gross - p.comm
        if p.i1 > p.i0:
            F[p.i0:p.i1] += wl[:-1]
    return real, np.cumsum(real) + F


def portfolio(symbols, tfs, rng_seed=None, invert=False):
    """Returns (v, m, entry days, stats) of the combined account at 1% risk per trade."""
    U = None
    for s in symbols:
        ix = minute_index(s); U = ix if U is None else U.union(ix)
    U = U.sort_values(); n = len(U)
    Racc, Eacc = np.zeros(n), np.zeros(n)
    ent, ntr, nets = set(), 0, []
    for s in symbols:
        m1 = T.load_m1(s)
        pos = U.get_indexer(m1.index)
        for tf in tfs:
            rng = None if rng_seed is None else np.random.default_rng(rng_seed + hash((s, tf)) % 1000)
            tr = T.simulate(s, tf, T.Spec(), m1, rng=rng, invert=invert)
            if tr.empty:
                continue
            real, eq = curves(tr, m1)
            ntr += len(tr); nets.append((tr.gross - 2 * tr.comm).values)
            ent |= set(pd.DatetimeIndex(m1.index.values[tr.i0.values]).normalize())
            for arr, acc in ((np.cumsum(real), Racc), (eq, Eacc)):                 # forward-fill each symbol's curve onto the common clock
                full = np.full(n, np.nan); full[pos] = arr
                acc += pd.Series(full).ffill().fillna(0.0).values
        del m1
    real = np.diff(Racc, prepend=0.0)
    day = U.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    days = pd.DatetimeIndex(day[start])
    before = np.where(start > 0, Racc[np.maximum(start - 1, 0)], 0.0)
    v = np.add.reduceat(real, start)
    m = np.minimum(np.minimum.reduceat(Eacc, start) - before, v)
    net = np.concatenate(nets)
    vv = pd.Series(v, index=days).reindex(pd.date_range(days.min(), days.max())).fillna(0.0)
    stats = dict(trades=ntr, mean_R=float(net.mean() / T.RISK_REF), t_stat=float(net.mean() / net.std() * np.sqrt(len(net))), sharpe=float(vv.mean() / vv.std() * np.sqrt(365)),
                 net_at_1pct=float(net.sum()), worst_day_pct=float(m.min() / T.INITIAL * 100))
    return pd.Series(v, index=days), pd.Series(m, index=days), ent, stats


def report(label, v, m, ent, stats, W):
    T.RISKS = RISKS
    ev = T.evaluate(v, m, ent, W)
    print(f"\n{label}: {stats['trades']} trades, mean {stats['mean_R']:+.3f}R (t {stats['t_stat']:+.1f}), daily Sharpe {stats['sharpe']:.2f}, worst intraday equity day at 1% risk/trade {stats['worst_day_pct']:.1f}%")
    for H in T.HORIZONS:
        e = ev[ev.horizon == H].set_index("rule")
        print(f"  within {H:>2} days: " + " | ".join(f"{r} {e.loc[r, 'pass_pct']:.0f}% (breach {e.loc[r, 'breach_pct']:.0f}%, r={e.loc[r, 'best_risk_pct']}%; leave-1-yr-out {e.loc[r, 'loyo_pass_pct']:.0f}%)" for r in e.index if pd.notna(e.loc[r, 'pass_pct'])))
    return ev


def main_inverted():
    W = T.windows("D"); syms = list(T.SYMBOLS)
    for label, tfs in (("INVERTED (fade the breakout), 15 symbols, hourly", ("H1",)), ("INVERTED, 15 symbols, hourly + daily", ("H1", "D1"))):
        v, m, ent, st = portfolio(syms, tfs, invert=True)
        report(label, v, m, ent, st, W)


def main():
    W = T.windows("D")
    syms = list(T.SYMBOLS)
    out = []
    for label, tfs in (("ALL 15 symbols, hourly", ("H1",)), ("ALL 15 symbols, hourly + daily", ("H1", "D1"))):
        v, m, ent, st = portfolio(syms, tfs)
        ev = report(label, v, m, ent, st, W); ev.insert(0, "config", label); out.append(ev)
        v, m, ent, st = portfolio(syms, tfs, rng_seed=0)
        ev = report("  NULL (random direction) of the same portfolio, 1 seed", v, m, ent, st, W); ev.insert(0, "config", label + " NULL"); out.append(ev)
    pd.concat(out).to_csv(T.HERE / "trendline_portfolio_results.csv", index=False)


if __name__ == "__main__":
    import sys
    main_inverted() if "--invert" in sys.argv else main()
