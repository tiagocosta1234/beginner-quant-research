"""
Round 327 (2026-10-03, PRE-REGISTERED; the 2 cells are logged as ONE ledger row, k + 1): a causal regime switch between multi-hour reversal and continuation, using only the strategy's own trailing results.

Rounds 325 and 326 found the same time pattern on four instruments across two asset classes: 2-3 hour >= 2 sigma moves REVERSED in 2020-2023 and CONTINUED in 2024-2026. A pattern that flips with the regime
can still be tradable if the regime can be read causally from the recent past. Mechanism: serial correlation of intraday moves is persistent in trending / mean-reverting phases (volatility and trend regimes last months),
so the sign of the last ~100 trades' reversal-minus-continuation P&L predicts the next trade's better side. Ledger checked first (k = 2029): no strategy-of-strategies regime switch on intraday moves is in the ledger.

DATA / SIGNALS: exactly Round 325's trades (build() per instrument, first >= 2 sigma move of the day, L in {120, 180}, M in {60, 120}), instruments ES, NQ, GC, SI, costs ES / NQ 1.0, GC 1.5, SI 3.0 bp.
RULE: for each instrument separately, in date order: for trade i (i > 100) the trailing 100 trades of THAT instrument and (L, M) strictly before it give mean reversal P&L and mean continuation P&L; trade whichever side had the higher trailing
mean (reversal = Round 325's rule, continuation = its opposite). The first 100 trades per instrument are warm-up (no trade). Trailing window 100 is fixed now, not tuned.
CELLS: 2 = (L120, M60) and (L180, M120), each pooled over the four instruments, scored on all trades after warm-up (about 2021 to 2026-09). Statistic: mean net bp per trade, date-clustered bootstrap (5,000 draws, seed 327).
CANDIDATE (fixed now): pooled mean > 0 with P >= 1 - 0.05/2 = 0.975 AND positive in both halves (before / from 2024-01-01) with a half-sample P >= 0.80, AND a coin-side placebo (random side each trade, 20 draws averaged) below the strategy by >= 2 bp.
Not widened after the run: no window length, threshold or horizon change to rescue a failure.
DRY-RUN COUNTS (trade counts only): L120 M60 scored 1,547 trades after the same-day fix (NQ 411, ES 389, SI 383, GC 364; 1,549 before it) from 2021-05-06 to 2026-09-25, 759 before 2024-01-01 and 788 after; L180 M120 scored 956 trades from 2021-11-16,
425 before and 531 after. A same-day leak was caught by reading before any P&L: the first draft's trailing window could include an earlier trade of the SAME day (DIP_LONG and SPIKE_SHORT on one date), whose exit may come after the
next entry; the window now ends strictly before the day's first trade.
POWER: per-trade sd about 30-45 bp; s.e. of the pooled mean about 0.9 bp (L120) / 1.3 bp (L180) and of a half about 1.3-1.9 bp: an edge above about +3-4 bp is detectable.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round325_intraday_dip_reversal as Q

COSTS = {"ES": 1.0, "NQ": 1.0, "GC": 1.5, "SI": 3.0}
W = 100
SPLIT = pd.Timestamp("2024-01-01")


def switch_trades(L, M, rng):
    rows = []
    for sym, c in COSTS.items():
        Q.COST = c
        d = Q.build(sym)
        d = d[(d.L == L) & (d.M == M)].sort_values("date").reset_index(drop=True)
        # one reversal pnl and one continuation pnl per trade (DIP_LONG and SPIKE_SHORT both included, date order)
        rev, cont = d.net.values, d.plc.values
        first = d.groupby("date").cumcount().eq(0)
        start = np.where(first, np.arange(len(d)), np.nan); start = pd.Series(start).ffill().astype(int).values   # first row of each date
        for i in range(W, len(d)):
            j = start[i]                     # trailing window ends strictly before today's first trade
            if j < W:
                continue
            mr, mc = rev[j - W:j].mean(), cont[j - W:j].mean()
            pick_cont = mc > mr
            coin = rev[i] if rng.random() < .5 else cont[i]
            rows.append(dict(date=d.date[i], sym=sym, net=cont[i] if pick_cont else rev[i], coin=coin, cont=bool(pick_cont)))
    return pd.DataFrame(rows)


def main(dry):
    rng = np.random.default_rng(327); out = {}
    for L, M in ((120, 60), (180, 120)):
        t = switch_trades(L, M, rng)
        if dry:
            print(f"L{L} M{M}: scored trades {len(t)} ({dict(t.sym.value_counts())}), from {t.date.min().date()} to {t.date.max().date()}, trades before split {(t.date < SPLIT).sum()}, after {(t.date >= SPLIT).sum()}"); continue
        a, b = t[t.date < SPLIT], t[t.date >= SPLIT]
        m, p = Q.boot(t, rng); ma, pa = Q.boot(a, rng); mb, pb = Q.boot(b, rng)
        coin = float(np.mean([switch_trades(L, M, np.random.default_rng(1000 + k)).coin.mean() for k in range(20)]))
        out[f"L{L}|M{M}"] = dict(n=len(t), mean_bp=m, P=p, first_half_bp=ma, first_P=pa, second_half_bp=mb, second_P=pb, coin_bp=coin,
                                 share_cont_first=float(a.cont.mean()), share_cont_second=float(b.cont.mean()),
                                 candidate=bool(m > 0 and p >= .975 and ma > 0 and pa >= .8 and mb > 0 and pb >= .8 and m - coin >= 2))
        print(f"L{L} M{M}", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[f"L{L}|M{M}"].items()})
    if not dry:
        print("candidates:", [k for k, v in out.items() if v["candidate"]])
        json.dump(out, open(os.path.join(HERE, "round327_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
