"""
Round 174: the third lever from the trader's "how do we smooth this" list, after
#2 (reshape the payoff, Round 173: tested properly, decayed OOS) failed.
This is #4: confluence (AND) instead of union (OR). Round 166 summed every
leg that fired that day (Connors RSI(2)<10, IBS<0.2, month-end rebalancing,
pre-holiday) -- take everything, size by however many agree. This tests the
opposite: trade ONLY on days where at least 2 of the 4 legs agree on the
SAME direction, on the theory that cutting the marginal, single-signal days
removes a disproportionate share of the losers relative to the winners,
even though it means far fewer trades.

Mechanically different from Round 166's `combine()`, which needed each
leg's REALIZED trade P&L. This needs each leg's DIRECTION DECISION before
any P&L exists, so confluence direction can be at agreement, not just co-
occurrence -- three of the four legs (Connors, IBS, pre-holiday) are
long-only by construction; only month-end rebalancing can go short. A
"confluence" day is one where 2+ of the four point the same way (almost
always long, given that asymmetry -- disclosed here, not discovered after
running).

Step 0, honest before running: Round 166 already showed these four legs'
daily correlations directly (Connors-IBS 0.382 -- the rest near zero), so
confluence will mostly mean "Connors and IBS agree" (they're correlated
enough to co-fire fairly often) plus the rarer case of one of the other two
lining up too. This could raise average quality by keeping only the
strongest days, or could just be a thinned, noisier version of the same
family with fewer observations to judge it by -- both are real
possibilities, not a foregone conclusion either way.

Rule: for each of ES/NQ/YM/RTY, on each day, count how many of the four
legs (Connors RSI(2)<10, IBS<0.2, month-end rebalancing fade, pre-holiday)
point the same direction. Trade (single R-unit, `round135_batch_d.
trades_from`) only when >=2 agree, in that direction. Everything else
(instruments, cost model, IS/OOS split) unchanged from Round 166.

1 variant. Ledger k=278 -> 279; OOS bar 1 - 0.01/279.

Candidate: net AND before-cost mean R > 0; IS P(edge>0) >= 0.95 (pre-2013);
OOS P(edge>0) >= the k=279 bar (2013-26).
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import round135_batch_d as D
import idea_harness as H
from round142_batch_j import connors
from round144_batch_k import rebalance_direction, nyse_calendar
from round145_batch_l import ohlc_frame, ibs_long

MIN_AGREE = 2


def pre_holiday_flags(idx):
    nyse = D.load_daily("SPY").index
    nxt = pd.Series(nyse[1:], index=nyse[:-1])
    pre = {day for day, n in nxt.items() if np.busday_count(day.date() + pd.Timedelta(days=1), n.date()) >= 1}
    return pd.Series(np.where(idx.isin(list(pre)), 1, 0), index=idx)


def leg_directions(sym, eq, rb):
    return pd.DataFrame({
        "connors": connors(eq[sym], 10),
        "ibs": ibs_long(ohlc_frame(sym)).reindex(eq[sym].index).fillna(0),
        "month_end": rb.reindex(eq[sym].index).fillna(0),
        "pre_holiday": pre_holiday_flags(eq[sym].index),
    })


def confluence_direction(dirs, min_agree=MIN_AGREE):
    n_long = (dirs == 1).sum(axis=1)
    n_short = (dirs == -1).sum(axis=1)
    return pd.Series(np.where(n_long >= min_agree, 1, np.where(n_short >= min_agree, -1, 0)), index=dirs.index)


def build_trades(min_agree=MIN_AGREE):
    eq = {s: D.market_frame(s) for s in D.EQUITY}
    zn = D.market_frame("ZN=F")
    rb = rebalance_direction(eq["ES=F"], zn)
    out = []
    for sym in D.EQUITY:
        dirs = leg_directions(sym, eq, rb)
        conf = confluence_direction(dirs, min_agree)
        out.append(D.trades_from(eq[sym], conf, sym))
    return pd.concat(out, ignore_index=True), eq


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv

    if dry:
        eq = {s: D.market_frame(s) for s in D.EQUITY}
        zn = D.market_frame("ZN=F")
        rb = rebalance_direction(eq["ES=F"], zn)
        for sym in D.EQUITY:
            dirs = leg_directions(sym, eq, rb)
            n_active = (dirs != 0).sum(axis=1)
            print(f"{sym}: days with >=2 legs active {int((n_active >= 2).sum())} / {len(dirs)}, "
                  f">=3 active {int((n_active >= 3).sum())}, all 4 active {int((n_active >= 4).sum())}")
        tr, _ = build_trades()
        print(f"\nConfluence (>=2 agree) trades, all 4 symbols: {len(tr)}")
        print("\n--dry-run: counts only, no candidate judgment. Hand-check before the real run.")
        sys.exit(0)

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k = H.ledger_count() + 1
    tr, eq = build_trades()
    r = D.judge_variant(f"Round 174 confluence (>={MIN_AGREE} of 4 dip-buy-family legs agree), 4 indices", tr, k)

    lines = H.ledger_rows([r], "Round 174 (pre-registered, confluence/AND combination of the dip-buy family)",
                           commit, date="2026-09-27")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round174_results.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
    print(f"\nledger now k={H.ledger_count()}")
