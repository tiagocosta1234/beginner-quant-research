"""
Round 330 (2026-10-03, PRE-REGISTERED; the 6 cells are logged as ONE ledger row, k + 1): intraday gold / silver ratio reversion, inside the regular session only.

Mechanism: gold and silver are cointegrated; one-hour deviations of ln(GC / SI) from its recent path are mostly relative-liquidity noise and revert (the daily ratio fade was tested in Round 176, ledger 284-285; index pairs intraday in Rounds 283 / J4 had zero gross).
Intraday GC / SI at 5-60 minute horizons is not in the ledger (k = 2031). Futures roll artifacts (a jump in one leg only) would fake spread moves, so every window lives INSIDE one 09:30-15:59 ET session (rolls happen overnight / on weekends).

DATA: Databento 1-minute GC and SI (2020-01-02..2026-09-25) resampled to 5-minute bars (open of the first minute, close of the fifth), RTH 09:30-15:59 ET, inner join on bar time, days with all 78 bars on both legs only.
SIGNAL (strictly causal): s = ln(GC close) - ln(SI close). At decision bar t (grid 10:30..14:30, the bar that just CLOSED), z_L = (s_t - s_{t-L bars}) / (sigma5 x sqrt(L)), sigma5 = standard deviation of the 5-minute changes of s over the PREVIOUS 20 sessions. Rule REVERT: z_L >= +2 -> short the spread
(short gold, long silver, equal dollars); z_L <= -2 -> long the spread; the first signal of the day only; ENTRY = the open of the NEXT 5-minute bar; EXIT = the close of the bar H bars later, capped at 15:59. L in {6, 12, 24} bars (30 / 60 / 120 minutes), H in {6, 12} bars (30 / 60 minutes): 6 cells.
P&L: direction x (dln GC - dln SI) x 1e4 in bp of ONE leg's notional, minus the round-trip cost of both legs, 1.5 (GC) + 3.0 (SI) = 4.5 bp (fixed now). Placebo = FOLLOW (the opposite direction) at the same cost.
SPLIT: IS 2020-2023 / OOS 2024-2026-09. Statistic: mean net bp per trade, date-clustered bootstrap (5,000 draws, seed 330).
CANDIDATE (fixed now): IS mean > 0 with P >= 0.95 AND OOS mean > 0 with P >= 1 - 0.05/6 = 0.9917 AND the FOLLOW placebo's OOS mean <= 0. Not widened after the run: no new thresholds, windows, hours, hedge ratios or products to rescue a failure.
DRY-RUN COUNTS (counts only): sessions kept (every 5-minute bar has all five 1-minute bars on both legs): GC 1,547 of 1,824, SI 766 of 1,823 (silver's thin minutes), intersection about 750; trades IS / OOS: L6 119 / 156, L12 101 / 121,
L24 65 / 85 (H = 6 and 12 share entries). Only complete-bar days are used because a stale silver minute would fake spread moves that revert; the cost of that is a smaller sample. A dead loop left in the first draft was removed.
POWER: spread-trade sd about 20-30 bp, so the s.e. of an IS mean is about 2-3 bp (65-119 trades) and of an OOS mean about 2-3 bp: only an edge above about +7 bp net (gross about +12 bp) is detectable; the result will be a weak test of small edges.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round321_long_bias_bold_play as R

IS_END = pd.Timestamp("2023-12-31")
COST = 4.5
LS, HS = (6, 12, 24), (6, 12)
NB = 78


def bars5(sym):
    b = R.load(sym)                                   # RTH 09:30-15:59 1-minute
    g = b.groupby([b.index.normalize(), (b.index.hour * 60 + b.index.minute - 570) // 5])
    o = g.o.first().unstack(); c = g.c.last().unstack(); n = g.c.count().unstack()
    ok = (n.reindex(columns=range(NB)).fillna(0) >= 5).all(axis=1)       # every 5-minute bar complete
    return o.loc[ok, range(NB)], c.loc[ok, range(NB)]


def build():
    og, cg = bars5("GC"); os_, cs = bars5("SI")
    days = og.index.intersection(os_.index)
    og, cg, os_, cs = og.loc[days], cg.loc[days], os_.loc[days], cs.loc[days]
    s = np.log(cg.values) - np.log(cs.values)               # days x 78
    ds = np.diff(s, axis=1)                                  # within-session 5-minute changes
    sig5 = pd.Series(np.nanstd(ds, axis=1), index=days).rolling(20).mean().shift(1)   # previous 20 sessions
    rows = []
    for i, d in enumerate(days):
        if d < pd.Timestamp("2020-01-02") or not np.isfinite(sig5.iloc[i]):
            continue
        for L in LS:
            for H in HS:
                hit = None
                for t in range(11, 60, 6):                                     # decision bars closing at 10:30, 11:00, ..., 14:30
                    if t - L < 0:
                        continue
                    z = (s[i, t] - s[i, t - L]) / (sig5.iloc[i] * np.sqrt(L))
                    if abs(z) >= 2:
                        hit = (t, np.sign(z)); break
                if hit is None:
                    continue
                t, sg = hit
                e = t + 1                                                      # entry bar
                x = min(e + H - 1, NB - 1)
                dg = np.log(cg.values[i, x] / og.values[i, e]); dsl = np.log(cs.values[i, x] / os_.values[i, e])
                spread_ret = (dg - dsl) * 1e4
                d_ = -sg                                                       # REVERT: short the spread when z high
                rows.append(dict(date=d, L=L, H=H, net=d_ * spread_ret - COST, plc=-d_ * spread_ret - COST))
    return pd.DataFrame(rows)


def boot(x, rng, col="net"):
    g = x.groupby("date")[col].agg(["sum", "count"])
    idx = rng.integers(0, len(g), (5000, len(g)))
    m = g["sum"].values[idx].sum(1) / g["count"].values[idx].sum(1)
    return float(x[col].mean()), float((m > 0).mean())


def main(dry):
    df = build(); rng = np.random.default_rng(330); out = {}
    for L in LS:
        for H in HS:
            x = df[(df.L == L) & (df.H == H)]
            a, b = x[x.date <= IS_END], x[x.date > IS_END]
            key = f"L{L}|H{H}"
            if dry:
                print(key, "trades IS", len(a), "OOS", len(b)); continue
            mi, pi = boot(a, rng); mo, po = boot(b, rng); pl = b.plc.mean()
            out[key] = dict(n_is=len(a), n_oos=len(b), is_bp=mi, is_P=pi, oos_bp=mo, oos_P=po, placebo_oos=float(pl),
                            gross_oos=float(mo + COST), candidate=bool(mi > 0 and pi >= .95 and mo > 0 and po >= 1 - .05 / 6 and pl <= 0))
            print(key, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[key].items()}, flush=True)
    if not dry:
        print("candidates:", [k for k, v in out.items() if v["candidate"]])
        json.dump(out, open(os.path.join(HERE, "round330_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
